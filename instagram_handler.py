import os
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired

class InstagramHandler:
    def __init__(self, account_manager, verification):
        self.client = Client()
        self.account_manager = account_manager
        self.verification = verification
        self.temp_dir = "temp_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.telegram_bot = None

    def set_telegram_bot(self, bot):
        self.telegram_bot = bot

    def login(self, username):
        account = self.account_manager.get_account(username)
        if not account:
            raise Exception("Account not found. Use /login first")
        
        try:
            self.client.login(username, account['password'])
            return True
            
        except ChallengeRequired:
            self.verification.start_verification(username, account['chat_id'])
            return False
            
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")

    def get_content(self, input_text):
        try:
            if input_text.startswith('@'):
                return self._
