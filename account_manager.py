"""
Account manager for handling multiple Instagram accounts.
This module provides functionality to register, store, and rotate between multiple
Instagram accounts to stay under rate limits and avoid bans.
"""

import os
import json
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
ACCOUNTS_FILE = "instagram_accounts.json"
MAX_DAILY_REQUESTS = 20  # Default max requests per account per day
COOLDOWN_HOURS = 24  # Default hours between account rotation cycles


class AccountStatus:
    """Status of an Instagram account."""
    AVAILABLE = "available"  # Account can be used
    COOLING = "cooling"      # Account is in cooldown after hitting limits
    BANNED = "banned"        # Account has been banned or restricted by Instagram
    UNKNOWN = "unknown"      # Account status is unknown


class AccountManager:
    """Manages multiple Instagram accounts for rotation."""
    
    def __init__(self, accounts_file: str = ACCOUNTS_FILE):
        """Initialize the account manager."""
        self.accounts_file = accounts_file
        self.accounts = {}  # username -> account info
        self.current_account = None  # Currently active account username
        self.load_accounts()
        
    def load_accounts(self) -> bool:
        """Load accounts from the accounts file."""
        try:
            if os.path.exists(self.accounts_file):
                with open(self.accounts_file, 'r') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', {})
                    self.current_account = data.get('current_account')
                    logger.info(f"Loaded {len(self.accounts)} accounts from file")
                    return True
            else:
                logger.info(f"Accounts file {self.accounts_file} not found, starting with empty accounts")
                return False
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
            return False
    
    def save_accounts(self) -> bool:
        """Save accounts to the accounts file."""
        try:
            data = {
                'accounts': self.accounts,
                'current_account': self.current_account,
                'updated_at': datetime.now().isoformat()
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.accounts_file), exist_ok=True)
            
            with open(self.accounts_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.accounts)} accounts to file")
            return True
        except Exception as e:
            logger.error(f"Error saving accounts: {e}")
            return False
    
    def add_account(self, username: str, password: str) -> bool:
        """Add a new Instagram account."""
        # Check if account already exists
        if username in self.accounts:
            logger.info(f"Account {username} already exists, updating password")
            
            # Update only the password, preserve other account data
            self.accounts[username]['password'] = password
            self.save_accounts()
            return True
        
        # Create new account entry
        account = {
            'username': username,
            'password': password,
            'added_at': datetime.now().isoformat(),
            'status': AccountStatus.AVAILABLE,
            'last_used': None,
            'request_count': 0,
            'daily_limit': MAX_DAILY_REQUESTS,
            'cooldown_hours': COOLDOWN_HOURS,
            'total_requests': 0,
            'error_count': 0,
            'notes': ''
        }
        
        self.accounts[username] = account
        
        # If this is the first account, set it as current
        if not self.current_account:
            self.current_account = username
            logger.info(f"Setting {username} as the current account")
        
        self.save_accounts()
        logger.info(f"Added account: {username}")
        return True
    
    def remove_account(self, username: str) -> bool:
        """Remove an Instagram account."""
        if username not in self.accounts:
            logger.warning(f"Account {username} not found")
            return False
        
        # Remove the account
        del self.accounts[username]
        
        # If this was the current account, select a new one
        if self.current_account == username:
            self.current_account = self._select_best_account()
            
        self.save_accounts()
        logger.info(f"Removed account: {username}")
        return True
    
    def get_account(self, username: Optional[str] = None) -> Optional[Dict]:
        """Get a specific account or the current one if username is None."""
        if username is None:
            if not self.current_account:
                return None
            username = self.current_account
            
        if username is None:
            return None
            
        return self.accounts.get(username)
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all registered accounts with their statuses."""
        return [
            {
                'username': username,
                'status': account.get('status', AccountStatus.UNKNOWN),
                'last_used': account.get('last_used'),
                'request_count': account.get('request_count', 0),
                'daily_limit': account.get('daily_limit', MAX_DAILY_REQUESTS),
                'total_requests': account.get('total_requests', 0),
            }
            for username, account in self.accounts.items()
        ]
    
    def get_current_account(self) -> Optional[Dict]:
        """Get the currently active account."""
        return self.get_account(self.current_account)
    
    def _select_best_account(self) -> Optional[str]:
        """Select the best account to use based on usage stats."""
        if not self.accounts:
            logger.warning("No accounts available for selection")
            return None
            
        # Update account statuses
        self._update_account_statuses()
        
        # Get available accounts
        available_accounts = [
            username for username, account in self.accounts.items()
            if account.get('status') == AccountStatus.AVAILABLE
        ]
        
        if not available_accounts:
            logger.warning("No available accounts found, all may be in cooldown or banned")
            
            # If all accounts are cooling, pick the one closest to being available
            cooling_accounts = [
                (username, account) for username, account in self.accounts.items()
                if account.get('status') == AccountStatus.COOLING
            ]
            
            if cooling_accounts:
                # Sort by last_used (oldest first)
                cooling_accounts.sort(key=lambda x: x[1].get('last_used', '0'))
                return cooling_accounts[0][0]
                
            # Otherwise, just pick any account as a fallback
            return list(self.accounts.keys())[0]
        
        # Prioritize accounts with fewer requests today
        available_accounts.sort(
            key=lambda username: self.accounts[username].get('request_count', 0)
        )
        
        # Return the account with the fewest requests
        return available_accounts[0]
    
    def _update_account_statuses(self) -> None:
        """Update the status of all accounts based on usage."""
        now = datetime.now()
        
        for username, account in self.accounts.items():
            # Skip already banned accounts
            if account.get('status') == AccountStatus.BANNED:
                continue
                
            # Check if account is in cooldown
            last_used_str = account.get('last_used')
            if last_used_str:
                try:
                    last_used = datetime.fromisoformat(last_used_str)
                    cooldown_hours = account.get('cooldown_hours', COOLDOWN_HOURS)
                    cooldown_until = last_used + timedelta(hours=cooldown_hours)
                    
                    if account.get('request_count', 0) >= account.get('daily_limit', MAX_DAILY_REQUESTS):
                        # Account hit limit and is cooling down
                        if now < cooldown_until:
                            # Still in cooldown
                            account['status'] = AccountStatus.COOLING
                        else:
                            # Cooldown period over, reset request count
                            account['status'] = AccountStatus.AVAILABLE
                            account['request_count'] = 0
                    else:
                        # Account is under limit, mark as available
                        account['status'] = AccountStatus.AVAILABLE
                except Exception as e:
                    logger.warning(f"Error updating status for account {username}: {e}")
            else:
                # Account has never been used, mark as available
                account['status'] = AccountStatus.AVAILABLE
    
    def rotate_account(self, force: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Rotate to the next available Instagram account.
        
        Args:
            force: If True, force rotation even if current account is under limits
            
        Returns:
            Tuple of (success, old_username, new_username)
        """
        old_username = self.current_account
        
        # If no accounts, we can't rotate
        if not self.accounts:
            logger.warning("No accounts registered, cannot rotate")
            return False, old_username, None
        
        # Check if current account needs rotation
        current = self.get_current_account()
        if not force and current and current.get('request_count', 0) < current.get('daily_limit', MAX_DAILY_REQUESTS):
            # Current account is still under limit, no need to rotate
            logger.info(f"Current account {old_username} is still under limit, not rotating")
            return True, old_username, old_username
        
        # Find the best account to use
        new_username = self._select_best_account()
        if not new_username:
            logger.error("Failed to select an account for rotation")
            return False, old_username, None
            
        # Set as current account
        self.current_account = new_username
        self.save_accounts()
        
        if new_username != old_username:
            logger.info(f"Rotated account from {old_username} to {new_username}")
        
        return True, old_username, new_username
    
    def record_request(self, username: Optional[str] = None, success: bool = True) -> bool:
        """Record a request for an account to track usage."""
        if username is None:
            username = self.current_account
            
        if not username or username not in self.accounts:
            logger.warning(f"Cannot record request for unknown account: {username}")
            return False
            
        account = self.accounts[username]
        
        # Update request counters
        account['request_count'] = account.get('request_count', 0) + 1
        account['total_requests'] = account.get('total_requests', 0) + 1
        
        # Record last used time
        account['last_used'] = datetime.now().isoformat()
        
        # Update error count if request failed
        if not success:
            account['error_count'] = account.get('error_count', 0) + 1
        
        # Check if account hit daily limit
        if account['request_count'] >= account.get('daily_limit', MAX_DAILY_REQUESTS):
            account['status'] = AccountStatus.COOLING
            logger.info(f"Account {username} hit daily limit, marking as cooling")
            
            # Try to rotate to a new account
            self.rotate_account()
        
        self.save_accounts()
        return True
    
    def mark_account_banned(self, username: Optional[str] = None) -> bool:
        """Mark an account as banned by Instagram."""
        if username is None:
            username = self.current_account
            
        if not username or username not in self.accounts:
            logger.warning(f"Cannot mark unknown account as banned: {username}")
            return False
            
        # Mark the account as banned
        self.accounts[username]['status'] = AccountStatus.BANNED
        self.accounts[username]['notes'] = f"Marked as banned on {datetime.now().isoformat()}"
        
        # If this was the current account, rotate to a new one
        if self.current_account == username:
            self.rotate_account(force=True)
            
        self.save_accounts()
        logger.warning(f"Marked account {username} as banned")
        return True
    
    def set_daily_limit(self, username: str, limit: int) -> bool:
        """Set the daily request limit for an account."""
        if username not in self.accounts:
            logger.warning(f"Cannot set limit for unknown account: {username}")
            return False
            
        self.accounts[username]['daily_limit'] = limit
        self.save_accounts()
        logger.info(f"Set daily limit of {limit} for account {username}")
        return True
    
    def set_cooldown_hours(self, username: str, hours: int) -> bool:
        """Set the cooldown period for an account after hitting limits."""
        if username not in self.accounts:
            logger.warning(f"Cannot set cooldown for unknown account: {username}")
            return False
            
        self.accounts[username]['cooldown_hours'] = hours
        self.save_accounts()
        logger.info(f"Set cooldown period of {hours} hours for account {username}")
        return True