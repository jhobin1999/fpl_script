class AnalysisService():
    def __init__(self, transactions: dict, user_dict: dict, player_dict: dict, current_gw: int):
        self._user_dict = user_dict
        self._transactions = transactions
        self._player_dict = player_dict
        self._current_gw = current_gw

    
    def most_weeks_bottom(self):
        pass

    def most_weeks_top(self):
        pass

    def most_transactions(self):
        pass
        
    
    def transaction_message(self):
        result = {}
        tick = "\u2705"   # ✅ Accepted Waiver
        cross = "\u274C"  # ❌ Failed/Declined Waiver
        free = "\U0001F193" # 🆓 Free Agent Transfer

        # Filter transactions for current gameweek only
        gw_transactions = [t for t in self._transactions if t.get("event") == self._current_gw]

        if not gw_transactions:
            return f"No transactions recorded for Gameweek {self._current_gw}."

        for transaction in gw_transactions:
            user_key = str(transaction["entry"])
            user = self._user_dict.get(user_key, "Unknown Manager")
            
            # Determine status symbol
            if transaction['kind'] == "f":
                transaction_result = free
            else:
                transaction_result = tick if transaction["result"] == "a" else cross

            player_in = self._player_dict.get(transaction["element_in"], {}).get('name', f"ID:{transaction['element_in']}")
            player_out = self._player_dict.get(transaction["element_out"], {}).get('name', f"ID:{transaction['element_out']}")

            message = f"  • {player_in} IN - {player_out} OUT {transaction_result}"
            
            if user in result:
                result[user].append(message)
            else:
                result[user] = [message]

        for user_key, user_name in self._user_dict.items():
            if user_name not in result:
                result[user_name] = ["  N/A"]

        # Combine all managers into a single formatted string
        formatted_blocks = [f"🏆 GW{self._current_gw} Transactions\n"]
        for name, messages in result.items():
            formatted_blocks.append(f"{name}:\n" + "\n".join(messages))

        return "\n\n".join(formatted_blocks)