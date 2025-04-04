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
            try:
                if story.media_type == 1:  # Photo
                    path = os.path.join(self.temp_dir, f"{story.id}.jpg")
                    self.client.photo_download(story.id, path)
                    media.append({'type': 'photo', 'path': path})
                elif story.media_type == 2:  # Video
                    path = os.path.join(self.temp_dir, f"{story.id}.mp4")
                    self.client.video_download(story.id, path)
                    media.append({'type': 'video', 'path': path})
            except Exception as e:
                print(f"Error downloading story: {str(e)}")
        return True, "Stories downloaded successfully", media

    def _download_story_by_url(self, url):
        # Extract the story ID from the URL and download it
        # Implementation goes here
        pass

    def cleanup_files(self, media):
        for item in media:
            os.remove(item['path'])
