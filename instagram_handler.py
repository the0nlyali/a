import os
import requests
from instagrapi import Client
from urllib.parse import urlparse

class InstagramHandler:
    def __init__(self):
        self.client = Client()
        self.telegram_bot = None
        self.temp_dir = "temp_media"
        os.makedirs(self.temp_dir, exist_ok=True)

    def set_telegram_bot(self, bot):
        self.telegram_bot = bot

    def get_content(self, input_text):
        try:
            if not input_text:
                return False, "No input provided", None
            
            input_text = input_text.strip()
            
            # Handle usernames
            if input_text.startswith('@'):
                return self._handle_username(input_text[1:])
            
            # Handle URLs
            parsed = urlparse(input_text)
            if 'instagram.com' in parsed.netloc:
                if '/stories/' in parsed.path:
                    return self._handle_story(input_text)
                elif '/p/' in parsed.path or '/reel/' in parsed.path:
                    return self._handle_post(input_text)
            
            return False, "Unsupported input format", None
            
        except Exception as e:
            return False, f"Error: {str(e)}", None

    def _handle_username(self, username):
        try:
            user_id = self.client.user_id_from_username(username)
            stories = self.client.user_stories(user_id)
            
            if not stories:
                return False, "No stories available", None
                
            media_items = []
            for story in stories:
                if story.media_type == 1:  # Photo
                    url = story.thumbnail_url or story.url
                    ext = ".jpg"
                else:  # Video
                    url = story.video_url
                    ext = ".mp4"
                
                path = self._download_file(url, f"story_{story.pk}{ext}")
                media_items.append({
                    'type': 'photo' if story.media_type == 1 else 'video',
                    'path': path
                })
            
            return True, f"Downloaded {len(media_items)} stories", media_items
            
        except Exception as e:
            return False, f"Failed to download stories: {str(e)}", None

    def _handle_story(self, url):
        # Similar to _handle_username but extracts username from URL
        pass

    def _handle_post(self, url):
        try:
            media_pk = self.client.media_pk_from_url(url)
            media = self.client.media_info(media_pk)
            
            media_items = []
            if media.media_type == 8:  # Carousel
                for item in media.resources:
                    item_path = self._process_media_item(item)
                    media_items.append(item_path)
            else:
                item_path = self._process_media_item(media)
                media_items.append(item_path)
            
            return True, "Downloaded post", media_items
            
        except Exception as e:
            return False, f"Failed to download post: {str(e)}", None

    def _process_media_item(self, media):
        if media.media_type == 1:  # Photo
            url = media.thumbnail_url or media.url
            ext = ".jpg"
        else:  # Video
            url = media.video_url
            ext = ".mp4"
        
        return self._download_file(url, f"media_{media.pk}{ext}")

    def _download_file(self, url, filename):
        path = os.path.join(self.temp_dir, filename)
        response = requests.get(url, stream=True)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return path

    def cleanup_files(self, media_items):
        for item in media_items:
            try:
                os.remove(item['path'])
            except:
                pass
