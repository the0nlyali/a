import os
import logging

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Telegram
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Instagram
TEMP_DIR = "temp_downloads"
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Messages (truncated for brevity - use your existing WELCOME_MESSAGE/HELP_MESSAGE)
WELCOME_MESSAGE = "Welcome to Instagram Downloader Bot..."
HELP_MESSAGE = "How to use the bot..."
ERROR_MESSAGES = {
    "invalid_url": "⚠️ Invalid URL...",
    # ... keep your existing error messages
}
