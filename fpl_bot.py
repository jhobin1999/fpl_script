import os
import re
import subprocess
import requests
from datetime import datetime, timezone

league_id = 127417
group_id = "BZdi6I3QqmX8DJAKfIH3g1"
# Automatically resolve paths based on script location
PYTHON_BIN = "/usr/bin/python3"  # Standard system Python on macOS

def get_current_gameweek():
    """Fetches the current active Gameweek ID from Draft bootstrap-static."""
    url = "https://draft.premierleague.com/api/bootstrap-static"
    res = requests.get(url).json()
    
    # 1. Primary check: 'current' key inside 'events' dict
    events_data = res.get('events', {})
    if isinstance(events_data, dict) and 'current' in events_data and events_data['current']:
        return events_data['current']
    
    # 2. Secondary check: list of event objects
    if isinstance(events_data, dict) and 'data' in events_data:
        for event in events_data['data']:
            if event.get('is_current'):
                return event['id']
                
    # 3. Fallback: check match fixtures
    matches = res.get('matches', [])
    if matches:
        return matches[0].get('event', 1)

    return 1

def get_player_dict():
    """Fetches Draft player data to ensure player IDs match Draft transactions."""
    url = "https://draft.premierleague.com/api/bootstrap-static"
    res = requests.get(url).json()

    players = res['elements']

    player_dict = {
        p['id']: {
            'name': p['web_name'],
            'team_code': p['team'],
            'element_type': p['element_type'],  # 1=GKP, 2=DEF, 3=MID, 4=FWD
            'total_points': p['total_points']
        }
        for p in players
    }
    return player_dict

def create_user_dict(response):
    user_dict = {}
    if "league_entries" in response:
        for user in response["league_entries"]:
            # Fixed quote nesting syntax
            entry_id = str(user["entry_id"])
            first_name = user["player_first_name"]
            user_dict[entry_id] = first_name
    return user_dict

def transaction_message(transactions, user_dict, player_dict, current_gw):
    result = {}
    tick = "\u2705"   # ✅ Accepted Waiver
    cross = "\u274C"  # ❌ Failed/Declined Waiver
    free = "\U0001F193" # 🆓 Free Agent Transfer

    # Filter transactions for current gameweek only
    gw_transactions = [t for t in transactions if t.get("event") == current_gw]

    if not gw_transactions:
        return f"No transactions recorded for Gameweek {current_gw}."

    for transaction in gw_transactions:
        user_key = str(transaction["entry"])
        user = user_dict.get(user_key, "Unknown Manager")
        
        # Determine status symbol
        if transaction['kind'] == "f":
            transaction_result = free
        else:
            transaction_result = tick if transaction["result"] == "a" else cross

        player_in = player_dict.get(transaction["element_in"], {}).get('name', f"ID:{transaction['element_in']}")
        player_out = player_dict.get(transaction["element_out"], {}).get('name', f"ID:{transaction['element_out']}")

        message = f"  • {player_in} IN - {player_out} OUT {transaction_result}"
        
        if user in result:
            result[user].append(message)
        else:
            result[user] = [message]

    # Combine all managers into a single formatted string
    formatted_blocks = [f"🏆 GW{current_gw} Transactions\n"]
    for name, messages in result.items():
        formatted_blocks.append(f"{name}:\n" + "\n".join(messages))

    return "\n\n".join(formatted_blocks)

def produce_message():
    endpoints = {
        "Standings": f"https://draft.premierleague.com/api/league/{league_id}/details",
        "Draft Picks": f"https://draft.premierleague.com/api/draft/{league_id}/choices",
        "Transactions": f"https://draft.premierleague.com/api/draft/league/{league_id}/transactions",
        "Waiver Pool": f"https://draft.premierleague.com/api/league/{league_id}/element-status"
    }
    
    current_gw = get_current_gameweek()
    player_dict = get_player_dict()
    message = ""
    user_dict = {}

    for name, url in endpoints.items():
        response = requests.get(url)
        if response.status_code == 200:
            response_json = response.json()
            response_keys = list(response_json.keys())
            
            if name == "Standings":
                user_dict = create_user_dict(response_json)
                print(f"✅ {name} : {response_keys}")
            elif name == "Transactions":
                transactions = response_json.get("transactions", [])
                message = transaction_message(transactions, user_dict, player_dict, current_gw)
        else:
            print(f"❌ {name} failed with status code {response.status_code}")

    return message

# --- AUTO-CHAINING LOGIC ---

def get_next_lineup_time():
    """Queries FPL API for upcoming Gameweek deadline and returns time 60m before."""
    url = "https://draft.premierleague.com/api/bootstrap-static"
    res = requests.get(url).json()
    
    # Grab event data array
    events = res.get('events', {}).get('data', [])
    now = datetime.now(timezone.utc)

    for event in events:
        deadline_str = event.get('deadline_time')
        if deadline_str:
            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            if deadline > now:
                return event['id'], deadline

    return None, None


def schedule_next_run():
  """Schedules next run by updating yml and pushing to GitHub."""
  gw_id, run_time = get_next_lineup_time()

  if not run_time:
    print("⚠️ No future Gameweek deadlines found to schedule.")
    return

  utc_time = run_time.astimezone(timezone.utc)
  minute = utc_time.minute
  hour = utc_time.hour
  day = utc_time.day
  month = utc_time.month

  cron_expr = f"{minute} {hour} {day} {month} *"
  print(
      f"\n📅 Next Lineup Release (GW{gw_id}):"
      f" {utc_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
  )
  print(f"⏱️ New Cron Schedule: {cron_expr}")

  try:
    yml_path = ".github/workflows/run_fpl.yml"

    # 1. Read the current workflow file
    with open(yml_path, "r") as f:
      content = f.read()

    # 2. Replace the old cron line with the new one
    new_content = re.sub(
        r"cron:\s*['\"].*?['\"]", f"cron: '{cron_expr}'", content
    )

    # 3. Save the updated file
    with open(yml_path, "w") as f:
      f.write(new_content)

    # 4. Grab GitHub Actions environment variables
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repository = os.environ.get("GITHUB_REPOSITORY")

    if not github_token or not github_repository:
      print("❌ Error: Missing GITHUB_TOKEN or GITHUB_REPOSITORY environment variables.")
      return

    # 5. Configure git and authenticate the remote URL using the token
    subprocess.run(
        ["git", "config", "--global", "user.name", "github-actions[bot]"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "config",
            "--global",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        check=True,
    )
    
    # Authenticate remote URL for pushing
    remote_url = f"https://x-access-token:{github_token}@github.com/{github_repository}.git"
    subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)

    # 6. Stage, commit, and push
    subprocess.run(["git", "add", yml_path], check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            f"Update workflow schedule for GW{gw_id} [{cron_expr}]",
        ],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)

    print("✅ Successfully updated and pushed the next run schedule to GitHub!")

  except Exception as e:
    print(f"❌ Failed to schedule next run: {e}")
