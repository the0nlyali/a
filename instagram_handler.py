import os
import logging
import tempfile
import shutil
import requests
import re
import time
import random
import threading
from pathlib import Path
from instagrapi import Client

from config import TEMP_DIR, ERROR_MESSAGES, MAX_TELEGRAM_FILE_SIZE
from account_manager import AccountManager, AccountStatus
from rate_limiter import RateLimiter, RateLimitedClient
from auto_rotate import AutoRotator

class InstagramHandler:
    def __init__(self):
        self.client = Client()
        self.authenticated = False
        
        # Store credentials in memory (not in environment variables)
        self.username = None
        self.password = None
        
        # Initialize account manager and rate limiter
        self.account_manager = AccountManager()
        self.rate_limiter = RateLimiter()
        
        # Use rate limited client wrapper
        self.limited_client = RateLimitedClient(self.client, self.rate_limiter)
        
        # Connect without authentication by default
        logging.info("Using Instagram API without authentication")
        
        # Keep track of rate limits
        self.request_count = 0
        self.max_requests = 100  # Basic rate limiting protection
        
        # Reference to Telegram bot (set from outside)
        self.telegram_bot = None
        self.bot_chat_id = None  # Store chat_id of user who initiated login
        
        # Initialize auto rotator (will start in separate method)
        self.auto_rotator = AutoRotator(self, 
                                        check_interval=30*60,  # Check every 30 minutes
                                        request_threshold=0.7) # Rotate at 70% of daily limit
        
    def set_credentials(self, username, password, chat_id=None):
        """Set Instagram credentials in memory (not saved to environment)"""
        self.username = username
        self.password = password
        if chat_id:
            self.bot_chat_id = chat_id
            
        # Add account to the account manager
        self.account_manager.add_account(username, password)
            
        logging.debug(f"Credentials set for user: {username}")
        return True
        
    def set_telegram_bot(self, bot):
        """Set the Telegram bot reference to enable sending notifications"""
        self.telegram_bot = bot
        logging.debug("Telegram bot reference set")
        
    def notify_verification_needed(self, message=None):
        """Send a notification to the user that a verification code is needed"""
        if self.telegram_bot and self.bot_chat_id:
            try:
                # Send a more prominent message with explicit instructions
                msg = message or (
                    "🔐 *VERIFICATION REQUIRED!* 🔐\n\n"
                    "Instagram needs to verify your identity. Please check your email or SMS "
                    "associated with your Instagram account and send me the 6-digit verification "
                    "code.\n\n"
                    "Simply type the 6 digits here - no need to use any commands."
                )
                # Try to send with markdown formatting for better visibility
                try:
                    sent_message = self.telegram_bot.send_message(self.bot_chat_id, msg, parse_mode='Markdown')
                except Exception:
                    # If markdown fails, try without formatting
                    sent_message = self.telegram_bot.send_message(self.bot_chat_id, msg)
                
                # Send a second message to ensure the user understands
                self.telegram_bot.send_message(
                    self.bot_chat_id, 
                    "⏳ I'll wait for you to send the code. Just type the 6 digits when you receive it!"
                )
                
                # Log message ID for debugging
                logging.info(f"Sent verification notification message ID: {sent_message.message_id}")
                return True
            except Exception as e:
                logging.error(f"Failed to send verification notification: {e}")
                # Try a simpler message as fallback
                try:
                    self.telegram_bot.send_message(
                        self.bot_chat_id, 
                        "Instagram verification required! Please send the 6-digit code you received."
                    )
                    return True
                except Exception as e2:
                    logging.error(f"Failed to send fallback verification message: {e2}")
        else:
            logging.error(f"Cannot send notification - bot_chat_id: {self.bot_chat_id}, telegram_bot set: {self.telegram_bot is not None}")
        return False
    
    def try_login(self):
        """Try to login non-blockingly (called in a separate thread)"""
        if self.authenticated:
            return True
            
        # Import verification module (here to avoid circular imports)
        from verification import (save_verification_request, get_verification_code, 
                                 has_verification_code, clear_verification_data,
                                 set_user_waiting_for_verification)
            
        # Check if we have credentials (either in memory or environment)
        username = self.username or os.environ.get("INSTAGRAM_USERNAME")
        password = self.password or os.environ.get("INSTAGRAM_PASSWORD")
        
        # Try to login if credentials are available
        if username and password:
            # First, check if we have a session file from previous successful login
            session_file = os.path.join(TEMP_DIR, f"instagram_session_{username}.json")
            session_exists = os.path.exists(session_file)
            
            # Define max retries for login attempts
            max_retries = 3
            retry_count = 0
            retry_delay = 3  # seconds between retries
            
            # Track if we've already notified about login issues
            notification_sent = False
            
            while retry_count < max_retries:
                try:
                    # Create a new client to avoid blocking the main one
                    client = Client()
                    
                    # Try to load saved session if it exists
                    if session_exists:
                        try:
                            logging.info(f"Attempting to load saved session for {username}")
                            client.load_settings(session_file)
                            client.login(username, password)
                            # If we reach here, login with session succeeded
                            self.client = client
                            self.authenticated = True
                            logging.info(f"Successfully logged in using saved session for {username}")
                            
                            # Save updated session
                            try:
                                client.dump_settings(session_file)
                                logging.info(f"Updated session file saved")
                            except Exception as save_err:
                                logging.warning(f"Could not save updated session: {save_err}")
                            
                            # Notify the user
                            if self.telegram_bot and self.bot_chat_id:
                                self.telegram_bot.send_message(
                                    self.bot_chat_id, 
                                    f"✅ Successfully logged in to Instagram as @{username}!"
                                )
                            return True
                        except Exception as session_error:
                            logging.warning(f"Could not use saved session: {session_error}")
                            session_exists = False  # Don't try again with this session
                    
                    # If no session or session load failed, try normal login
                    logging.info(f"Attempting Instagram login for {username} (attempt {retry_count+1}/{max_retries})...")
                    
                    try:
                        # First try without verification code to see if it's needed
                        client.login(username, password)
                        
                        # If we reach here, login succeeded without verification
                        self.client = client
                        self.authenticated = True
                        
                        # Save session for future use
                        try:
                            client.dump_settings(session_file)
                            logging.info(f"Session saved to {session_file}")
                        except Exception as save_err:
                            logging.warning(f"Could not save session: {save_err}")
                        
                        # Notify the user about successful login
                        if self.telegram_bot and self.bot_chat_id:
                            success_msg = f"✅ Successfully logged in to Instagram as @{username}!"
                            self.telegram_bot.send_message(self.bot_chat_id, success_msg)
                        
                        logging.info("Logged in to Instagram successfully")
                        return True
                    
                    except Exception as first_login_error:
                        error_message = str(first_login_error).lower()
                        
                        # Check if verification is needed
                        if any(keyword in error_message for keyword in ["challenge", "verification", "code", "two-factor", "2fa"]):
                            # Handle verification flow
                            # Extract challenge info if possible - use a safe approach
                            user_id = "unknown"
                            challenge_context = "unknown"
                            try:
                                # Extract data from the error message
                                error_str = str(first_login_error)
                                logging.debug(f"Full login error message: {error_str}")
                                
                                # Try to parse the error for useful information
                                if hasattr(first_login_error, 'challenge_context'):
                                    challenge_context = str(first_login_error.challenge_context)
                                elif 'challenge_context' in error_str:
                                    # Try to extract from string if not available as attribute
                                    try:
                                        import re
                                        context_match = re.search(r'challenge_context[\'"]?\s*[:=]\s*[\'"]?([^\'"]+)', error_str)
                                        if context_match:
                                            challenge_context = context_match.group(1)
                                    except Exception:
                                        pass
                                        
                                if hasattr(first_login_error, 'user_id'):
                                    user_id = str(first_login_error.user_id)
                                elif 'user_id' in error_str:
                                    # Try to extract from string if not available as attribute
                                    try:
                                        import re
                                        user_id_match = re.search(r'user_id[\'"]?\s*[:=]\s*[\'"]?([^\'"]+)', error_str)
                                        if user_id_match:
                                            user_id = user_id_match.group(1)
                                    except Exception:
                                        pass
                            except Exception as ex:
                                logging.warning(f"Could not extract challenge info: {ex}")
                                
                            logging.info(f"Challenge context: {challenge_context}, User ID: {user_id}")
                                
                            # Save verification request
                            save_verification_request(challenge_context, user_id)
                            
                            # Set the state for this user to waiting for verification
                            if self.bot_chat_id:
                                set_user_waiting_for_verification(str(self.bot_chat_id), challenge_context)
                            
                            # Notify about verification
                            logging.warning("Instagram requires verification code")
                            if self.bot_chat_id and self.telegram_bot:
                                try:
                                    notification_sent = self.notify_verification_needed()
                                    if notification_sent:
                                        logging.info(f"Sent verification request notification to user {self.bot_chat_id}")
                                    else:
                                        logging.error(f"Failed to send verification notification to user {self.bot_chat_id}")
                                except Exception as notify_error:
                                    logging.error(f"Error during verification notification: {notify_error}")
                            else:
                                logging.error("Cannot send verification notification - bot_chat_id or telegram_bot not set")
                            
                            # Wait for verification code (up to 300 seconds / 5 minutes)
                            wait_time = 0
                            max_wait = 300
                            while wait_time < max_wait:
                                if has_verification_code():
                                    verification_code = get_verification_code()
                                    if verification_code:
                                        masked_code = verification_code[:2] + "****" if len(verification_code) > 4 else "****"
                                        logging.info(f"Verification code provided: {masked_code}")
                                    
                                    # Try login with the provided code
                                    try:
                                        client = Client()  # Fresh client
                                        client.login(
                                            username,
                                            password,
                                            verification_code=verification_code
                                        )
                                        # If we reach here, login succeeded
                                        self.client = client
                                        self.authenticated = True
                                        clear_verification_data()  # Clean up
                                        
                                        # Save the successful session
                                        try:
                                            client.dump_settings(session_file)
                                            logging.info(f"Session saved after verification to {session_file}")
                                        except Exception as save_err:
                                            logging.warning(f"Could not save session after verification: {save_err}")
                                        
                                        # Notify the user about successful login
                                        if self.telegram_bot and self.bot_chat_id:
                                            success_msg = f"✅ Successfully logged in to Instagram as @{username}!"
                                            self.telegram_bot.send_message(self.bot_chat_id, success_msg)
                                        
                                        logging.info("Successfully logged in to Instagram with verification code")
                                        return True
                                    except Exception as verify_error:
                                        logging.error(f"Verification code didn't work: {verify_error}")
                                        clear_verification_data()  # Clean up
                                        
                                        # Notify the user about failed verification
                                        if self.telegram_bot and self.bot_chat_id:
                                            error_msg = (
                                                "❌ Verification failed. The code may have expired or been incorrect.\n\n"
                                                "Please try logging in again with /login username password."
                                            )
                                            self.telegram_bot.send_message(self.bot_chat_id, error_msg)
                                        
                                        return False
                                
                                # Wait before checking again
                                time.sleep(5)
                                wait_time += 5
                            
                            # Timeout waiting for verification
                            logging.warning("Timed out waiting for verification code")
                            
                            # Notify the user about timeout
                            if self.telegram_bot and self.bot_chat_id:
                                timeout_msg = (
                                    "⏰ Verification code request timed out.\n\n"
                                    "Please check your email or phone for the code and try logging in again with "
                                    "/login username password."
                                )
                                self.telegram_bot.send_message(self.bot_chat_id, timeout_msg)
                            
                            return False
                        
                        elif "ip" in error_message and any(term in error_message for term in ["block", "blacklist", "suspicious"]):
                            # IP address might be blocked or flagged
                            logging.warning(f"IP address may be blocked by Instagram: {error_message}")
                            
                            # Only send one notification about this issue
                            if not notification_sent and self.telegram_bot and self.bot_chat_id:
                                ip_block_msg = (
                                    "⚠️ Instagram may have temporarily blocked this IP address.\n\n"
                                    "This is common with server environments. Please try again later or "
                                    "login to your Instagram account via the app to confirm it's still active."
                                )
                                self.telegram_bot.send_message(self.bot_chat_id, ip_block_msg)
                                notification_sent = True
                            
                            # Don't retry immediately, this won't help with IP blocks
                            return False
                            
                        elif "invalid" in error_message and any(term in error_message for term in ["credential", "password", "username"]):
                            # Invalid credentials
                            logging.warning(f"Invalid Instagram credentials: {error_message}")
                            
                            if self.telegram_bot and self.bot_chat_id:
                                invalid_creds_msg = (
                                    "❌ Login failed: The username or password appears to be incorrect.\n\n"
                                    "Please check your credentials and try again with /login username password."
                                )
                                self.telegram_bot.send_message(self.bot_chat_id, invalid_creds_msg)
                            
                            # Don't retry with same invalid credentials
                            return False
                        
                        else:
                            # Other login error, may be temporary
                            logging.warning(f"Instagram login error (attempt {retry_count+1}/{max_retries}): {error_message}")
                            retry_count += 1
                            
                            # Only notify on the last retry
                            if retry_count >= max_retries and not notification_sent and self.telegram_bot and self.bot_chat_id:
                                general_error_msg = (
                                    "❌ Login attempt failed after multiple tries.\n\n"
                                    "Instagram might be experiencing issues or applying security measures. "
                                    "Please try again later."
                                )
                                self.telegram_bot.send_message(self.bot_chat_id, general_error_msg)
                                notification_sent = True
                            
                            # Wait before retrying
                            time.sleep(retry_delay)
                
                except Exception as e:
                    # Unexpected error in the login process itself
                    logging.error(f"Unexpected error during login process: {e}")
                    retry_count += 1
                    
                    # Only notify on the last retry
                    if retry_count >= max_retries and not notification_sent and self.telegram_bot and self.bot_chat_id:
                        error_msg = (
                            "❌ An unexpected error occurred during login.\n\n"
                            "Please try again later or contact the bot administrator if the problem persists."
                        )
                        self.telegram_bot.send_message(self.bot_chat_id, error_msg)
                        notification_sent = True
                    
                    # Wait before retrying
                    time.sleep(retry_delay)
            
            # If we reached this point, all retries failed
            logging.error(f"All login attempts failed for {username}")
            return False
        
        else:
            logging.info("No Instagram credentials found, using public access only")
            return False
    
    def _extract_username(self, input_text):
        """Extract username from URL or plain username input"""
        if not input_text:
            return None
            
        # Clean the input text
        input_text = input_text.strip()
        
        logging.debug(f"Extracting username from: {input_text}")
        
        # First, try to extract username using regex for URLs
        if "instagram.com" in input_text:
            # Match username pattern in Instagram URLs
            username_match = re.search(r'instagram\.com/([^/?#]+)', input_text)
            if username_match:
                username = username_match.group(1)
                # Handle special cases
                if username in ['p', 'reel', 'reels', 'stories', 'explore']:
                    logging.debug(f"Found special Instagram path: {username}, not a username")
                    return None  # These are not usernames but Instagram URL paths
                logging.debug(f"Successfully extracted username from URL: {username}")
                return username

            # If regex failed, try the traditional split method
            parts = input_text.strip("/").split("/")
            for i, part in enumerate(parts):
                if part == "instagram.com" and i+1 < len(parts):
                    # Handle URL formats like instagram.com/username and instagram.com/username?igshid=...
                    username = parts[i+1].split("?")[0]
                    if username in ['p', 'reel', 'reels', 'stories', 'explore']:
                        logging.debug(f"Found special Instagram path: {username}, not a username")
                        return None
                    logging.debug(f"Successfully extracted username via split method: {username}")
                    return username
            logging.debug("Could not extract username from URL")
            return None
        else:
            # It's probably just a username - remove @ and any trailing/leading spaces
            username = input_text.strip().strip("@")
            # Remove any query parameters that might have been copied
            if '?' in username:
                username = username.split('?')[0]
            logging.debug(f"Treating input as raw username: {username}")
            return username if username else None
    
    def _extract_media_id(self, url):
        """Extract media ID from post URL or shortcode"""
        if not url:
            return None
            
        # Clean the input URL
        url = url.strip()
        
        logging.debug(f"Extracting media ID from: {url}")
        
        # Use more flexible regex patterns to capture shortcodes
        # Try to find a post shortcode in the URL with different URL patterns
        shortcode_match = re.search(r'instagram\.com/(?:p|post|posts)/([^/?#]+)', url)
        if shortcode_match:
            shortcode = shortcode_match.group(1)
            logging.debug(f"Found post shortcode: {shortcode}")
            try:
                media_id = self.client.media_id(self.client.media_pk_from_code(shortcode))
                logging.debug(f"Successfully extracted media ID for post: {media_id}")
                return media_id
            except Exception as e:
                logging.error(f"Error extracting media ID from shortcode {shortcode}: {e}")
                return None
        
        # Try to find a reel code in the URL with different URL patterns
        reel_match = re.search(r'instagram\.com/(?:reel|reels|r)/([^/?#]+)', url)
        if reel_match:
            reel_code = reel_match.group(1)
            logging.debug(f"Found reel code: {reel_code}")
            try:
                media_id = self.client.media_id(self.client.media_pk_from_code(reel_code))
                logging.debug(f"Successfully extracted media ID for reel: {media_id}")
                return media_id
            except Exception as e:
                logging.error(f"Error extracting media ID from reel code {reel_code}: {e}")
                return None
        
        # Try to extract any shortcodes directly provided
        if re.match(r'^[A-Za-z0-9_-]{11}$', url):  # Typical Instagram shortcode length
            logging.debug(f"Treating input as direct shortcode: {url}")
            try:
                media_id = self.client.media_id(self.client.media_pk_from_code(url))
                logging.debug(f"Successfully extracted media ID from direct shortcode: {media_id}")
                return media_id
            except Exception as e:
                logging.error(f"Error extracting media ID from direct shortcode {url}: {e}")
                return None
        
        logging.debug("Could not extract any media ID")       
        return None
    
    def _determine_content_type(self, input_text):
        """Determine what type of content the user is requesting"""
        if not input_text:
            logging.debug("Empty input text")
            return "username", None
            
        # Clean the input
        input_text = input_text.strip()
        logging.debug(f"Determining content type for: {input_text}")
        
        # Modern Instagram URL patterns for posts
        post_patterns = ['/p/', '/post/', '/posts/']
        reel_patterns = ['/reel/', '/reels/', '/r/']
        
        # Check if it's a post or reel URL using any of the patterns
        is_post = any(pattern in input_text for pattern in post_patterns)
        is_reel = any(pattern in input_text for pattern in reel_patterns)
        
        if is_post:
            logging.debug(f"URL matches post pattern")
        if is_reel:
            logging.debug(f"URL matches reel pattern")
        
        if is_post or is_reel:
            media_id = self._extract_media_id(input_text)
            if media_id:
                content_type = "reel" if is_reel else "post"
                logging.debug(f"Determined content type: {content_type}")
                return content_type, media_id
        
        # Try to parse it as a direct shortcode (sometimes users just copy the shortcode part)
        if re.match(r'^[A-Za-z0-9_-]{11}$', input_text):
            logging.debug(f"Input looks like a direct shortcode")
            media_id = self._extract_media_id(input_text)
            if media_id:
                logging.debug(f"Successfully parsed direct shortcode")
                # We assume it's a post by default if we can't determine
                return "post", media_id
        
        # Default to username/stories
        logging.debug(f"Defaulting to username/stories")
        username = self._extract_username(input_text)
        if username:
            logging.debug(f"Found username: {username}")
        else:
            logging.debug(f"Could not determine username")
        return "username", username

    def get_content(self, input_text):
        """Get Instagram content based on input (stories, posts, or reels)"""
        # Check if we need to rotate accounts
        current_account = self.account_manager.get_current_account()
        
        # If no accounts are registered, use default behavior
        if not current_account:
            # Basic rate limiting
            self.request_count += 1
            if self.request_count > self.max_requests:
                return False, ERROR_MESSAGES["rate_limit"], None
        else:
            # Check if current account is available
            if current_account.get('status') != AccountStatus.AVAILABLE:
                # Try to rotate to a better account
                success, old_username, new_username = self.account_manager.rotate_account()
                if success and new_username:
                    logging.info(f"Rotated from {old_username} to {new_username}")
                    
                    # Update current account username
                    account = self.account_manager.get_account(new_username)
                    if account:
                        self.username = account.get('username')
                        self.password = account.get('password')
                        
                        # Need to re-login with the new account
                        logging.info(f"Logging in with rotated account: {self.username}")
                        
                        # Reset client to ensure fresh connection
                        self.client = Client()
                        self.authenticated = False
                        
                        # Try to log in with the new account
                        if not self.try_login():
                            logging.error(f"Failed to log in with rotated account: {self.username}")
                            return False, ERROR_MESSAGES["login_failed"], None
                else:
                    logging.warning("All accounts are unavailable or in cooldown")
                    return False, ERROR_MESSAGES["rate_limit"], None
            
            # Record this request with the account manager
            self.account_manager.record_request()
            
        # Determine content type
        content_type, identifier = self._determine_content_type(input_text)
        
        if not identifier:
            return False, ERROR_MESSAGES["invalid_url"], None
        
        # Apply rate limiting before making the request
        self.rate_limiter.wait()
        
        # Handle different content types
        if content_type == "post":
            return self.get_post(identifier)
        elif content_type == "reel":
            return self.get_reel(identifier)
        else:  # username, get stories
            return self.get_stories(identifier)
    
    def get_post(self, media_id):
        """Download Instagram post by media ID"""
        # Create a temporary directory
        temp_dir = os.path.join(TEMP_DIR, f"post_{media_id}_{os.urandom(4).hex()}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Get post details
            try:
                media_info = self.limited_client.media_info(media_id)
            except Exception as e:
                logging.error(f"Error getting post info for {media_id}: {e}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, ERROR_MESSAGES["not_found"], None
            
            # Download media
            media_items = []
            
            # If it's a carousel post, download all items
            if media_info.media_type == 8:  # Carousel
                for resource in media_info.resources:
                    # Download each carousel item
                    item = self._download_media_item(resource, temp_dir)
                    if item:
                        media_items.append(item)
            else:
                # Single photo or video
                item = self._download_media_item(media_info, temp_dir)
                if item:
                    media_items.append(item)
            
            if not media_items:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, ERROR_MESSAGES["download_error"], None
                
            username = media_info.user.username
            return True, f"Downloaded post from @{username} ({len(media_items)} items)", media_items
            
        except Exception as e:
            logging.error(f"Error processing post {media_id}: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"{ERROR_MESSAGES['general_error']} Error: {str(e)}", None
    
    def get_reel(self, media_id):
        """Download Instagram reel by media ID"""
        # Create a temporary directory
        temp_dir = os.path.join(TEMP_DIR, f"reel_{media_id}_{os.urandom(4).hex()}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Get reel details
            try:
                media_info = self.limited_client.media_info(media_id)
            except Exception as e:
                logging.error(f"Error getting reel info for {media_id}: {e}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, ERROR_MESSAGES["not_found"], None
            
            # Download media - reel is just a video
            media_items = []
            
            # Make sure it's a video type
            if media_info.media_type == 2:  # Video
                item = self._download_media_item(media_info, temp_dir)
                if item:
                    media_items.append(item)
            
            if not media_items:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, ERROR_MESSAGES["download_error"], None
                
            username = media_info.user.username
            return True, f"Downloaded reel from @{username}", media_items
            
        except Exception as e:
            logging.error(f"Error processing reel {media_id}: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"{ERROR_MESSAGES['general_error']} Error: {str(e)}", None

    def get_stories(self, username):
        """Get all available stories from a username"""
        # Create a temporary directory for this specific download
        temp_dir = os.path.join(TEMP_DIR, f"stories_{username}_{os.urandom(4).hex()}")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Get user info
            try:
                user_id = self.limited_client.user_id_from_username(username)
            except Exception as e:
                logging.error(f"Error finding user {username}: {e}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, ERROR_MESSAGES["not_found"], None
            
            # Fetch stories
            try:
                stories = self.limited_client.user_stories(user_id)
            except Exception as e:
                logging.error(f"Error fetching stories for {username}: {e}")
                if "not authorized to view" in str(e).lower():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False, ERROR_MESSAGES["private_account"], None
                else:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False, ERROR_MESSAGES["download_error"], None
            
            if not stories:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, ERROR_MESSAGES["no_stories"], None
            
            # Download stories
            story_items = []
            for story in stories:
                # Create temp file for this story
                is_video = story.media_type == 2  # 2 is video in instagrapi
                file_ext = ".mp4" if is_video else ".jpg"
                
                with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix=file_ext) as tf:
                    temp_filename = tf.name
                
                # Get the URL
                if is_video:
                    url = story.video_url
                else:
                    url = story.thumbnail_url if hasattr(story, 'thumbnail_url') else story.url
                
                # Download the file
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    with open(temp_filename, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    
                    # Check file size for Telegram limits
                    if os.path.getsize(temp_filename) <= MAX_TELEGRAM_FILE_SIZE:
                        story_items.append({
                            'type': 'video' if is_video else 'photo',
                            'path': temp_filename
                        })
                        
            if not story_items:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, ERROR_MESSAGES["media_too_large"], None
                
            return True, f"Found {len(story_items)} stories from @{username}", story_items
            
        except Exception as e:
            logging.error(f"Error processing stories for {username}: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"{ERROR_MESSAGES['general_error']} Error: {str(e)}", None
    
    def _download_media_item(self, media_item, temp_dir):
        """Helper to download a single media item"""
        try:
            # Create temp file
            is_video = media_item.media_type == 2  # 2 is video in instagrapi
            file_ext = ".mp4" if is_video else ".jpg"
            
            with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix=file_ext) as tf:
                temp_filename = tf.name
            
            # Get the URL for download
            if is_video:
                url = media_item.video_url
            else:
                url = media_item.thumbnail_url if hasattr(media_item, 'thumbnail_url') else media_item.url
            
            # Download the file
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(temp_filename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                
                # Check file size
                if os.path.getsize(temp_filename) <= MAX_TELEGRAM_FILE_SIZE:
                    return {
                        'type': 'video' if is_video else 'photo',
                        'path': temp_filename
                    }
                else:
                    os.unlink(temp_filename)
            
            return None
            
        except Exception as e:
            logging.error(f"Error downloading media item: {e}")
            return None

    def cleanup_files(self, file_paths):
        """Remove temporary files after sending to Telegram"""
        if not file_paths:
            return
            
        # Get unique directories
        dirs_to_remove = set()
        for item in file_paths:
            path = item['path']
            dirs_to_remove.add(os.path.dirname(path))
        
        # Remove all directories
        for dir_path in dirs_to_remove:
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception as e:
                logging.error(f"Error cleaning up directory {dir_path}: {e}")
                
    def start_auto_rotation(self):
        """Start the automatic account rotation system"""
        if hasattr(self, 'auto_rotator'):
            logging.info("Starting automatic account rotation system")
            success = self.auto_rotator.start()
            return success
        else:
            logging.error("Auto rotator not initialized")
            return False
            
    def stop_auto_rotation(self):
        """Stop the automatic account rotation system"""
        if hasattr(self, 'auto_rotator'):
            logging.info("Stopping automatic account rotation system")
            success = self.auto_rotator.stop()
            return success
        else:
            logging.error("Auto rotator not initialized")
            return False
            
    def force_account_rotation(self):
        """Force an immediate account rotation"""
        if hasattr(self, 'auto_rotator'):
            logging.info("Forcing immediate account rotation")
            return self.auto_rotator.force_rotation()
        else:
            # Fall back to manual rotation
            success, old_username, new_username = self.account_manager.rotate_account(force=True)
            if success and old_username != new_username:
                logging.info(f"Manually rotated from {old_username} to {new_username}")
            return success
            
    def get_auto_rotation_status(self):
        """Get information about the auto-rotation system"""
        if hasattr(self, 'auto_rotator'):
            return self.auto_rotator.get_status()
        else:
            return {
                'active': False,
                'error': 'Auto rotator not initialized'
            }
