import requests

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
            first_name = user["player_first_name"].capitalize()
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

    for user_key, user_name in user_dict.items():
        if user_name not in result:
            result[user_name] = ["N/A"]

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