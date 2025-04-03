import os
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# Bot configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logging.error("No TELEGRAM_TOKEN found in environment variables!")

# Temporary directory to store downloaded files
TEMP_DIR = "temp_downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

# Maximum file size for Telegram uploads (in bytes) - 50MB
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024

# Message templates
WELCOME_MESSAGE = """
Welcome to Instagram Downloader Bot! 🎬

I can help you download Instagram content. Here's how to use me:

1. For stories: Send a profile URL like https://www.instagram.com/username or just the username
2. For posts: Send a post URL like https://www.instagram.com/p/CODE
3. For reels: Send a reel URL like https://www.instagram.com/reel/CODE

Basic Commands:
/start - Show this welcome message
/help - Get usage instructions
/login - Set your Instagram credentials (format: /login username password)
/status - Check if you're logged in to Instagram
/verify - Enter verification code when Instagram requires it (or just send the code directly)

Account Management (Admin only):
/accounts - List all registered Instagram accounts
/addaccount - Add a new Instagram account (format: /addaccount username password)
/removeaccount - Remove an Instagram account (format: /removeaccount username)
/rotate - Manually rotate to the next available Instagram account
/setlimit - Set daily request limit for an account (format: /setlimit username limit)
/setcooldown - Set cooldown hours for an account (format: /setcooldown username hours)

Automatic Rotation (Admin only):
/autorotate - Start automatic account rotation system
/stoprotation - Stop automatic account rotation system
/rotationstatus - Get status of the automatic rotation system

Note: I can only download content from public profiles or profiles you have access to.
"""

HELP_MESSAGE = """
📱 *Instagram Downloader Help* 📱

To download Instagram content, you can:

1. For Stories: 
   • Send a profile URL: `https://www.instagram.com/username`
   • Or simply send the username: `username`

2. For Posts:
   • Send a post URL: `https://www.instagram.com/p/CODE`

3. For Reels:
   • Send a reel URL: `https://www.instagram.com/reel/CODE`

4. For logging in to Instagram:
   • Use: `/login username password` - Replace with your real Instagram credentials

5. For checking your login status:
   • Use: `/status` - Will tell you if you're currently logged in to Instagram

6. For Verification (when Instagram requires it):
   • When prompted, simply send the 6-digit code you received from Instagram
   • Alternatively use: `/verify CODE` - Replace CODE with the 6-digit code

7. For Account Management (Admin only):
   • `/accounts` - List all registered Instagram accounts
   • `/addaccount username password` - Add a new Instagram account
   • `/removeaccount username` - Remove an Instagram account
   • `/rotate` - Manually rotate to the next available Instagram account
   • `/setlimit username limit` - Set daily request limit for an account
   • `/setcooldown username hours` - Set cooldown hours for an account

8. For Automatic Rotation (Admin only):
   • `/autorotate` or `/startrotation` - Start the automatic account rotation system
   • `/stoprotation` - Stop the automatic account rotation system
   • `/rotationstatus` - Get current status of the automatic rotation system

I'll download all available content and send it to you via Telegram.

⚠️ *Limitations*:
- I can only download from public profiles or profiles you have access to
- Very large videos might not be downloadable due to Telegram limits (50MB)
- Instagram may limit requests, so please use responsibly
- Sometimes Instagram will require verification - check your email for codes

If you encounter any issues, try again later or with a different profile/post/reel.
"""

ERROR_MESSAGES = {
    "invalid_url": "⚠️ That doesn't look like a valid Instagram URL or username. Please try again.",
    "no_stories": "😕 No active stories found for this profile.",
    "private_account": "🔒 This account is private and I don't have access to it.",
    "not_found": "❌ This Instagram content could not be found. Please check the username or URL.",
    "download_error": "❌ Error downloading content. Please try again later.",
    "general_error": "❌ Something went wrong. Please try again later.",
    "media_too_large": "⚠️ This content is too large to send via Telegram (limit: 50MB).",
    "rate_limit": "⚠️ Rate limit reached. Please try again later to avoid Instagram restrictions."
}
