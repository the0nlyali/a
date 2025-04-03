#!/usr/bin/env python
"""
Automatic account rotation module for the Instagram Downloader Bot.
This module provides functionality to automatically rotate Instagram accounts
to avoid rate limits and bans.
"""
import logging
import threading
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional

# Default settings
DEFAULT_AUTO_ROTATE_INTERVAL = 900  # 15 minutes check interval
DEFAULT_REQUEST_THRESHOLD = 0.75  # 75% of max requests
DEFAULT_RANDOM_VARIATION = 0.2  # 20% random variation in rotation times

class AutoRotator:
    """Handles automatic rotation of Instagram accounts."""
    
    def __init__(self, 
                 instagram_handler,
                 check_interval: int = DEFAULT_AUTO_ROTATE_INTERVAL,
                 request_threshold: float = DEFAULT_REQUEST_THRESHOLD,
                 random_variation: float = DEFAULT_RANDOM_VARIATION):
        """
        Initialize the auto rotator.
        
        Args:
            instagram_handler: The InstagramHandler instance
            check_interval: Time in seconds between rotation checks
            request_threshold: Percentage of max requests that triggers rotation
            random_variation: Random variation factor for rotation times
        """
        self.instagram_handler = instagram_handler
        self.account_manager = getattr(instagram_handler, 'account_manager', None)
        
        self.check_interval = check_interval
        self.request_threshold = request_threshold
        self.random_variation = random_variation
        
        self._thread = None
        self._stop_event = threading.Event()
        self._rotation_count = 0
        self._last_rotation = None
        self._active = False
    
    def start(self):
        """Start the automatic rotation thread."""
        if not self.account_manager:
            logging.error("Cannot start auto rotation without account manager")
            return False
        
        if self._thread and self._thread.is_alive():
            logging.info("Auto rotation thread is already running")
            return True
        
        # Create and start the thread
        self._stop_event.clear()
        self._active = True
        self._thread = threading.Thread(target=self._rotation_loop)
        self._thread.daemon = True  # Thread will exit when main program ends
        self._thread.start()
        logging.info("Auto rotation thread started")
        return True
    
    def stop(self):
        """Stop the automatic rotation thread."""
        if not self._thread or not self._thread.is_alive():
            logging.info("Auto rotation thread is not running")
            self._active = False
            return True
        
        # Signal the thread to stop
        self._stop_event.set()
        self._active = False
        
        # Wait for thread to stop (with timeout)
        self._thread.join(timeout=5.0)
        
        if self._thread.is_alive():
            logging.warning("Auto rotation thread didn't stop in time")
            return False
        else:
            logging.info("Auto rotation thread stopped")
            return True
    
    def _rotation_loop(self):
        """Main loop for account rotation checks."""
        logging.info("Auto rotation loop started")
        
        while not self._stop_event.is_set():
            try:
                self._check_and_rotate()
            except Exception as e:
                logging.error(f"Error in auto rotation loop: {e}")
            
            # Calculate next check time with random variation
            variation = random.uniform(1.0 - self.random_variation, 1.0 + self.random_variation)
            wait_time = int(self.check_interval * variation)
            
            # Wait until next check or until stop is requested
            for _ in range(min(wait_time, 300)):  # Check stop event every 5 minutes max
                if self._stop_event.wait(timeout=1.0):
                    break
        
        logging.info("Auto rotation loop ended")
    
    def _check_and_rotate(self):
        """Check if rotation is needed and rotate if necessary."""
        if not self.account_manager:
            return
        
        current = self.account_manager.get_current_account()
        if not current:
            logging.warning("No current account for rotation check")
            return
        
        # Check if we've reached the threshold for rotation
        req_count = current.get('request_count', 0)
        daily_limit = current.get('daily_limit', 0)
        
        if daily_limit <= 0:
            # No meaningful limit to compare against
            return
        
        usage_ratio = req_count / daily_limit
        
        if usage_ratio >= self.request_threshold:
            logging.info(f"Auto rotating account: {usage_ratio:.2f} >= {self.request_threshold:.2f}")
            self.force_rotation()
    
    def _update_instagram_client(self, username):
        """Update the Instagram client with credentials from the newly rotated account."""
        # This is a placeholder for when we have actual Instagram client rotation
        # We'd need to update the Instagram client with new credentials
        pass
    
    def force_rotation(self):
        """Force an immediate account rotation."""
        if not self.account_manager:
            logging.error("Cannot rotate without account manager")
            return False
        
        try:
            # Attempt rotation
            success, old_username, new_username = self.account_manager.rotate_account(force=True)
            
            if success and old_username != new_username:
                # Update rotation stats
                self._rotation_count += 1
                self._last_rotation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Update Instagram client if needed
                if new_username:
                    self._update_instagram_client(new_username)
                
                logging.info(f"Auto rotated from {old_username} to {new_username}")
                return True
            elif success:
                logging.info("Auto rotation not needed or no other accounts available")
                return True
            else:
                logging.error("Failed to auto rotate accounts")
                return False
                
        except Exception as e:
            logging.error(f"Error during auto rotation: {e}")
            return False
    
    def get_status(self):
        """Get the current status of the auto rotator."""
        return {
            'active': self._active,
            'rotation_count': self._rotation_count,
            'last_rotation': self._last_rotation,
            'check_interval': self.check_interval,
            'request_threshold': self.request_threshold
        }