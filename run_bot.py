#!/usr/bin/env python
import os
import threading
import time
import logging
from datetime import datetime

from instagram_handler import InstagramHandler
from bot import run_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize Instagram handler
instagram_handler = InstagramHandler()  # Initialize without blocking login

def start_instagram_login_thread():
    """Start Instagram login in a separate thread."""
    
    def login_task():
        """Attempt to log in to Instagram in a background thread."""
        time.sleep(5)  # Wait a bit to let other services start
        logging.info("Attempting Instagram login in background thread...")
        success = instagram_handler.try_login()
        if success:
            logging.info("Instagram login successful in background thread")
        else:
            logging.warning("Instagram login failed in background thread, will use public access")
    
    instagram_login_thread = threading.Thread(target=login_task)
    instagram_login_thread.daemon = True
    instagram_login_thread.start()

if __name__ == "__main__":
    # Start Instagram login thread
    start_instagram_login_thread()
    
    # Run the bot with our Instagram handler
    run_bot(instagram_handler)