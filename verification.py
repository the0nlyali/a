"""
Module for handling Instagram verification codes and user verification states
"""
import os
import json
import logging
import time
from typing import Optional, Dict, Any, Set
from threading import Lock

# File to store verification data
# This can be updated by functions later if needed
verification_file_path = 'verification_data.json'
# Lock to ensure thread safety
verification_lock = Lock()

# Track which users are currently in verification mode
# This is stored in memory for faster access
waiting_for_verification_users: Dict[str, str] = {}  # chat_id -> challenge_context

def get_verification_file_path() -> str:
    """Get the current verification file path"""
    global verification_file_path
    return verification_file_path

def update_verification_file_path(new_path: str) -> None:
    """Update the verification file path"""
    global verification_file_path
    verification_file_path = new_path
    logging.info(f"Updated verification file path to: {verification_file_path}")

def save_verification_request(challenge_context: str, user_id: str) -> None:
    """Save information about a verification request"""
    with verification_lock:
        data = {
            'challenge_context': challenge_context,
            'user_id': user_id,
            'timestamp': time.time(),
            'status': 'pending',
            'code': None
        }
        
        try:
            file_path = get_verification_file_path()
            # Make sure the verification file directory exists
            verification_dir = os.path.dirname(file_path)
            if verification_dir and not os.path.exists(verification_dir):
                os.makedirs(verification_dir, exist_ok=True)
                
            with open(file_path, 'w') as f:
                json.dump(data, f)
            
            logging.info(f"Saved verification request for user {user_id}")
        except Exception as e:
            logging.error(f"Error saving verification request: {e}")
            # Try using a more accessible location as fallback
            try:
                fallback_file = 'verification_data.json'  # Use current directory
                with open(fallback_file, 'w') as f:
                    json.dump(data, f)
                update_verification_file_path(fallback_file)  # Update the file path
                logging.info(f"Saved verification request to fallback location for user {user_id}")
            except Exception as e2:
                logging.error(f"Error saving verification request to fallback location: {e2}")

def save_verification_code(code: str) -> None:
    """Save a verification code provided by the user"""
    with verification_lock:
        try:
            file_path = get_verification_file_path()
            # Check if file exists
            if not os.path.exists(file_path):
                logging.warning(f"No pending verification request file found at {file_path}")
                
                # Try to create a new verification request if one doesn't exist
                data = {
                    'challenge_context': 'unknown',
                    'user_id': 'unknown',
                    'timestamp': time.time(),
                    'status': 'pending',
                    'code': None
                }
            else:
                # Load existing data
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                except Exception as read_error:
                    logging.error(f"Error reading verification file: {read_error}")
                    data = {
                        'challenge_context': 'unknown',
                        'user_id': 'unknown',
                        'timestamp': time.time(),
                        'status': 'pending',
                        'code': None
                    }
            
            # Update the data with the code
            data['code'] = code
            data['status'] = 'provided'
            
            # Save the updated data
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f)
                # Mask the code for logging
                masked_code = code[:2] + "*" * (len(code) - 2) if len(code) > 2 else "****"
                logging.info(f"Verification code '{masked_code}' saved successfully")
            except Exception as write_error:
                logging.error(f"Error writing verification file: {write_error}")
                # Try fallback location
                try:
                    fallback_file = 'verification_data.json'  # Use current directory
                    with open(fallback_file, 'w') as f:
                        json.dump(data, f)
                    update_verification_file_path(fallback_file)  # Update the file path
                    logging.info(f"Saved verification code to fallback location")
                except Exception as fallback_error:
                    logging.error(f"Error saving to fallback location: {fallback_error}")
                    
        except Exception as e:
            logging.error(f"Error in save_verification_code: {e}")

def get_verification_data() -> Optional[Dict[str, Any]]:
    """Get the current verification data"""
    with verification_lock:
        try:
            file_path = get_verification_file_path()
            if not os.path.exists(file_path):
                return None
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            return data
        except Exception as e:
            logging.error(f"Error reading verification data: {e}")
            return None

def clear_verification_data() -> None:
    """Clear the verification data"""
    with verification_lock:
        file_path = get_verification_file_path()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logging.info("Verification data cleared")
            except Exception as e:
                logging.error(f"Error clearing verification data: {e}")

def is_verification_pending() -> bool:
    """Check if there is a pending verification request"""
    data = get_verification_data()
    return data is not None and data.get('status') == 'pending'

def has_verification_code() -> bool:
    """Check if a verification code has been provided"""
    data = get_verification_data()
    return data is not None and data.get('status') == 'provided' and data.get('code') is not None

def get_verification_code() -> Optional[str]:
    """Get the provided verification code"""
    data = get_verification_data()
    if data and data.get('status') == 'provided':
        return data.get('code')
    return None

# Functions for the interactive verification flow
def set_user_waiting_for_verification(chat_id: str, challenge_context: str) -> None:
    """Mark a user as waiting for verification code"""
    waiting_for_verification_users[chat_id] = challenge_context
    logging.info(f"User {chat_id} is now waiting for verification code")

def is_user_waiting_for_verification(chat_id: str) -> bool:
    """Check if a user is waiting for verification code"""
    return chat_id in waiting_for_verification_users

def get_challenge_context_for_user(chat_id: str) -> Optional[str]:
    """Get the challenge context for a user waiting for verification"""
    return waiting_for_verification_users.get(chat_id)

def clear_user_verification_state(chat_id: str) -> None:
    """Clear the verification state for a user"""
    if chat_id in waiting_for_verification_users:
        del waiting_for_verification_users[chat_id]
        logging.info(f"User {chat_id} verification state cleared")