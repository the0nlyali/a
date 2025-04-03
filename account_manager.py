import json
import os
from pathlib import Path
from datetime import datetime

class AccountManager:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.accounts_file = self.data_dir / "accounts.json"
        self.accounts = self._load_accounts()

    def _load_accounts(self):
        if self.accounts_file.exists():
            with open(self.accounts_file) as f:
                return json.load(f)
        return {}

    def add_account(self, username, password):
        self.accounts[username] = {
            'username': username,
            'password': password,  # Note: In production, encrypt this
            'added_at': datetime.now().isoformat()
        }
        self._save_accounts()

    def _save_accounts(self):
        with open(self.accounts_file, 'w') as f:
            json.dump(self.accounts, f, indent=2)

    # ... (include your other account management methods)
