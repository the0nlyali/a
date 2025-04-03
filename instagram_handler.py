import os
import tempfile
import requests
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired

class InstagramHandler:
    def __init__(self):
        self.client = Client()
        self.telegram_bot = None
        self.temp_dir = "temp_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)

    def set_telegram_bot(self, bot):
        self.telegram_bot = bot

    def get_content(self, input_text):
        try:
            if not input_text:
                return False, "No input provided", None

            # Determine content type
            if "/stories/" in input_text or input_text.startswith("@"):
                return self._download_story(input_text)
            elif "/p/" in input_text or "/reel/" in input_text:
                return self._download_post(input_text)
            else:
                return False, "Unsupported URL format", None

        except Exception as e:
            return False, f"Error: {str(e)}", None

    def _download_story(self, username):
        try:
            # Extract username
            username = username.split("/stories/")[-1].split("/")[0].replace("@", "")
            
            # Get user ID and stories
            user_id = self.client.user_id_from_username(username)
            stories = self.client.user_stories(user_id)
            
            if not stories:
                return False, "No active stories found", None

            media_items = []
            for story in stories:
                if story.media_type == 1:  # Photo
                    url = story.thumbnail_url if hasattr(story, 'thumbnail_url') else story.url
                    ext = ".jpg"
                else:  # Video
                    url = story.video_url
                    ext = ".mp4"

                # Download file
                file_path = os.path.join(self.temp_dir, f"story_{story.pk}{ext}")
                self._download_file(url, file_path)
                
                media_items.append({
                    'type': 'photo' if story.media_type == 1 else 'video',
                    'path': file_path
                })

            return True, f"Downloaded {len(media_items)} stories", media_items

        except Exception as e:
            return False, f"Story download failed: {str(e)}", None

    def _download_post(self, url):
        try:
            media_pk = self.client.media_pk_from_url(url)
            media = self.client.media_info(media_pk)
            
            media_items = []
            if media.media_type == 8:  # Carousel
                for item in media.resources:
                    item_path = self._download_media_item(item)
                    media_items.append(item_path)
            else:
                item_path = self._download_media_item(media)
                media_items.append(item_path)

            return True, "Downloaded post", media_items

        except Exception as e:
            return False, f"Post download failed: {str(e)}", None

    def _download_media_item(self, media):
        if media.media_type == 1:  # Photo
            url = media.thumbnail_url if hasattr(media, 'thumbnail_url') else media.url
            ext = ".jpg"
        else:  # Video
            url = media.video_url
            ext = ".mp4"

        file_path = os.path.join(self.temp_dir, f"media_{media.pk}{ext}")
        self._download_file(url, file_path)
        
        return {
            'type': 'photo' if media.media_type == 1 else 'video',
            'path': file_path
        }

    def _download_file(self, url, save_path):
        response = requests.get(url, stream=True)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

    def cleanup_files(self, media_items):
        for item in media_items:
            try:
                os.remove(item['path'])
            except:
                pass
