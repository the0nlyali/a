import json
import os
from threading import Lock

class AccountManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.accounts_file = os.path.join(data_dir, "accounts.json")
        self.lock = Lock()
        os.makedirs(data_dir, exist_ok=True)
        
    def add_account(self, username, password, chat_id):
        with self.lock:
            accounts = self._load_accounts()
            accounts[username] = {
                'password': password,
                'chat_id': chat_id,
                'needs_2fa': False
            }
            self._save_accounts(accounts)
    
    def get_account(self, username):
        with self.lock:
            accounts = self._load_accounts()
            return accounts.get(username)
    
    def _load_accounts(self):
        try:
            if os.path.exists(self.accounts_file):
                with open(self.accounts_file) as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_accounts(self, accounts):
        with open(self.accounts_file, 'w') as f:
            json.dump(accounts, f)
