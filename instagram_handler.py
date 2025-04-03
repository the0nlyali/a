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
                return self._download_stories(input_text[1:])
            elif "instagram.com" in input_text:
                if "/stories/" in input_text:
                    return self._download_story_by_url(input_text)
                elif "/p/" in input_text or "/reel/" in input_text:
                    return self._download_post(input_text)
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
                    path = f"{self.temp_dir}/{story.pk}.jpg"
                    self.client.photo_download(story.pk, path)
                else:  # Video
                    path = f"{self.temp_dir}/{story.pk}.mp4"
                    self.client.video_download(story.pk, path)
                
                media.append({
                    'type': 'photo' if story.media_type == 1 else 'video',
                    'path': path
                })
            except Exception as e:
                continue
                
        if not media:
            return False, "No stories found for this user", []
        return True, f"Downloaded {len(media)} items", media

    def _download_story_by_url(self, url):
        story_pk = self.client.media_pk_from_url(url)
        story = self.client.story_info(story_pk)
        
        if story.media_type == 1:  # Photo
            path = f"{self.temp_dir}/{story.pk}.jpg"
            self.client.photo_download(story.pk, path)
        else:  # Video
            path = f"{self.temp_dir}/{story.pk}.mp4"
            self.client.video_download(story.pk, path)
            
        return True, "Story downloaded", [{
            'type': 'photo' if story.media_type == 1 else 'video',
            'path': path
        }]

    def _download_post(self, url):
        media_pk = self.client.media_pk_from_url(url)
        media = self.client.media_info(media_pk)
        
        downloaded_items = []
        
        if media.media_type == 1:  # Single photo
            path = f"{self.temp_dir}/{media.pk}.jpg"
            self.client.photo_download(media.pk, path)
            downloaded_items.append({
                'type': 'photo',
                'path': path
            })
            
        elif media.media_type == 2:  # Single video
            path = f"{self.temp_dir}/{media.pk}.mp4"
            self.client.video_download(media.pk, path)
            downloaded_items.append({
                'type': 'video',
                'path': path
            })
            
        elif media.media_type == 8:  # Album
            for item in media.resources:
                if item.media_type == 1:
                    path = f"{self.temp_dir}/{item.pk}.jpg"
                    self.client.photo_download(item.pk, path)
                else:
                    path = f"{self.temp_dir}/{item.pk}.mp4"
                    self.client.video_download(item.pk, path)
                downloaded_items.append({
                    'type': 'photo' if item.media_type == 1 else 'video',
                    'path': path
                })
        
        return True, f"Downloaded {len(downloaded_items)} items", downloaded_items

    def cleanup_files(self, media_items):
        for item in media_items:
            try:
                os.remove(item['path'])
            except:
                pass
