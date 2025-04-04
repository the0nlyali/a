import os
import requests
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
            return False
        
        try:
            self.client.login(username, account['password'])
            return True
            
        except ChallengeRequired:
            self.verification.start_verification(username, account['chat_id'])
            return False
            
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def get_content(self, input_text):
        try:
            if input_text.startswith('@'):
                return self._download_stories(input_text[1:])
            elif "instagram.com/stories/" in input_text:
                return self._download_story_by_url(input_text)
            else:
                return False, "Unsupported content type", []
                
        except LoginRequired:
            return False, "Session expired. Please /login again", []
        except Exception as e:
            return False, f"Error: {str(e)}", []

    def _download_stories(self, username):
        user_id = self.client.user_id_from_username(username)
        stories = self.client.user_stories(user_id)
        
        media = []
        for story in stories:
            media_type = 'photo' if story.media_type == 1 else 'video'
            file_path = os.path.join(self.temp_dir, f"{username}_story_{story.id}.{media_type}")
            self.client.download_story(story, file_path)
            media.append({'path': file_path, 'type': media_type})
        return True, "Stories downloaded successfully.", media

    def _download_story_by_url(self, url):
        # Extract username from the URL and download stories
        username = url.split('/')[-2]
        return self._download_stories(username)

    def cleanup_files(self, media):
        for item in media:
            os.remove(item['path'])

    def fetch_user_data(self, username):
        url = f"https://www.instagram.com/{username}/?__a=1"
        response = requests.get(url)
        try:
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except ValueError:
            print("Failed to decode JSON. Response content:")
            print(response.text)
            return None
