from instagrapi import Client
import logging
import os
from config import TEMP_DIR, MAX_TELEGRAM_FILE_SIZE

class InstagramHandler:
    def __init__(self):
        self.client = Client()
        self.authenticated = False
        self.username = None
        self.password = None
        self.telegram_bot = None

    def set_credentials(self, username, password, chat_id=None):
        self.username = username
        self.password = password
        self.chat_id = chat_id

    def try_login(self):
        try:
            if not (self.username and self.password):
                return False
                
            self.client.login(self.username, self.password)
            self.authenticated = True
            if self.telegram_bot and self.chat_id:
                self.telegram_bot.send_message(
                    self.chat_id, 
                    f"✅ Successfully logged in as @{self.username}"
                )
            return True
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False

    # ... (include your content download methods)
