"""
Handler for account management commands in the Telegram bot.
"""

import logging
import telebot
from telebot import types
from typing import Dict, List, Tuple, Optional
from account_manager import AccountManager, AccountStatus

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def is_admin(user_id: int, admin_ids: List[int]) -> bool:
    """Check if a user is an admin."""
    return user_id in admin_ids


def register_account_commands(bot: telebot.TeleBot, account_manager: AccountManager, admin_ids: Optional[List[int]] = None):
    """
    Register account management commands with the Telegram bot.
    
    Args:
        bot: The Telegram bot instance
        account_manager: The AccountManager instance
        admin_ids: List of Telegram user IDs that have admin privileges
    """
    if admin_ids is None:
        admin_ids = []
    
    @bot.message_handler(commands=['addaccount'])
    def add_account_command(message: types.Message):
        """
        Add a new Instagram account to the rotation.
        Format: /addaccount username password
        """
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "❌ Sorry, only admins can manage accounts.")
            return
        
        # Check command format
        parts = message.text.strip().split()
        if len(parts) != 3:
            bot.reply_to(message, 
                "⚠️ Please use the format: /addaccount username password\n\n"
                "For example: /addaccount myinstauser mypassword123"
            )
            return
        
        # Extract username and password
        _, username, password = parts
        
        # Add the account
        success = account_manager.add_account(username, password)
        
        if success:
            # Delete the message containing credentials for security
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                logger.warning(f"Could not delete message with credentials: {e}")
                
            # Send confirmation
            bot.send_message(
                message.chat.id,
                f"✅ Added Instagram account @{username} to the rotation.\n\n"
                f"Current accounts: {len(account_manager.accounts)}"
            )
        else:
            bot.reply_to(message, f"❌ Failed to add account @{username}. Please try again.")
    
    @bot.message_handler(commands=['removeaccount'])
    def remove_account_command(message: types.Message):
        """
        Remove an Instagram account from the rotation.
        Format: /removeaccount username
        """
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "❌ Sorry, only admins can manage accounts.")
            return
        
        # Check command format
        parts = message.text.strip().split()
        if len(parts) != 2:
            bot.reply_to(message, 
                "⚠️ Please use the format: /removeaccount username\n\n"
                "For example: /removeaccount myinstauser"
            )
            return
        
        # Extract username
        _, username = parts
        
        # Remove the account
        success = account_manager.remove_account(username)
        
        if success:
            bot.reply_to(
                message,
                f"✅ Removed Instagram account @{username} from the rotation.\n\n"
                f"Remaining accounts: {len(account_manager.accounts)}"
            )
        else:
            bot.reply_to(message, f"❌ Account @{username} not found.")
    
    @bot.message_handler(commands=['accounts'])
    def list_accounts_command(message: types.Message):
        """List all registered Instagram accounts and their status."""
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "❌ Sorry, only admins can view account information.")
            return
        
        # Get all accounts
        accounts = account_manager.get_all_accounts()
        
        if not accounts:
            bot.reply_to(message, "No Instagram accounts registered yet. Use /addaccount to add one.")
            return
        
        # Current account
        current = account_manager.get_current_account()
        current_username = current.get('username') if current else "None"
        
        # Format the account information
        account_lines = []
        
        for account in accounts:
            username = account.get('username')
            status = account.get('status', 'unknown')
            requests = account.get('request_count', 0)
            limit = account.get('daily_limit', 20)
            total = account.get('total_requests', 0)
            
            # Format the status with emoji
            status_emoji = {
                AccountStatus.AVAILABLE: "✅",
                AccountStatus.COOLING: "⏳",
                AccountStatus.BANNED: "🚫",
                AccountStatus.UNKNOWN: "❓"
            }.get(status, "❓")
            
            # Mark current account
            current_marker = "➡️ " if username == current_username else "   "
            
            # Add the line
            account_lines.append(
                f"{current_marker}{status_emoji} @{username}: {requests}/{limit} requests today, {total} total"
            )
        
        # Create the message
        accounts_message = "📱 *Instagram Accounts*\n\n" + "\n".join(account_lines)
        
        # Add instructions
        accounts_message += "\n\n" + (
            "✅ = Available  |  ⏳ = Cooling down  |  🚫 = Banned  |  ❓ = Unknown\n"
            "➡️ = Currently active account\n\n"
            "Use /addaccount to add a new account\n"
            "Use /removeaccount to remove an account\n"
            "Use /rotate to manually rotate accounts"
        )
        
        # Send the message
        bot.reply_to(message, accounts_message, parse_mode='Markdown')
    
    @bot.message_handler(commands=['rotate'])
    def rotate_account_command(message: types.Message):
        """Manually rotate to the next Instagram account."""
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "❌ Sorry, only admins can rotate accounts.")
            return
        
        # Get current account
        old_account = account_manager.get_current_account()
        old_username = old_account.get('username') if old_account else "None"
        
        # Rotate accounts
        success, _, new_username = account_manager.rotate_account(force=True)
        
        if success and new_username:
            if old_username == new_username:
                bot.reply_to(
                    message,
                    f"ℹ️ Account rotation completed, but no better alternative found.\n\n"
                    f"Still using account @{new_username}."
                )
            else:
                bot.reply_to(
                    message,
                    f"✅ Successfully rotated accounts!\n\n"
                    f"From: @{old_username}\n"
                    f"To: @{new_username}"
                )
        else:
            bot.reply_to(
                message,
                "❌ Failed to rotate accounts. No suitable account found.\n\n"
                "Use /addaccount to add more accounts."
            )
    
    @bot.message_handler(commands=['setlimit'])
    def set_limit_command(message: types.Message):
        """
        Set the daily request limit for an account.
        Format: /setlimit username limit
        """
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "❌ Sorry, only admins can change account limits.")
            return
        
        # Check command format
        parts = message.text.strip().split()
        if len(parts) != 3:
            bot.reply_to(message, 
                "⚠️ Please use the format: /setlimit username limit\n\n"
                "For example: /setlimit myinstauser 30"
            )
            return
        
        # Extract username and limit
        _, username, limit_str = parts
        
        # Validate limit
        try:
            limit = int(limit_str)
            if limit < 1:
                raise ValueError("Limit must be at least 1")
        except ValueError:
            bot.reply_to(message, "❌ Limit must be a positive number.")
            return
        
        # Update the limit
        success = account_manager.set_daily_limit(username, limit)
        
        if success:
            bot.reply_to(
                message,
                f"✅ Set daily limit for @{username} to {limit} requests."
            )
        else:
            bot.reply_to(message, f"❌ Account @{username} not found.")
    
    @bot.message_handler(commands=['setcooldown'])
    def set_cooldown_command(message: types.Message):
        """
        Set the cooldown period for an account.
        Format: /setcooldown username hours
        """
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "❌ Sorry, only admins can change account settings.")
            return
        
        # Check command format
        parts = message.text.strip().split()
        if len(parts) != 3:
            bot.reply_to(message, 
                "⚠️ Please use the format: /setcooldown username hours\n\n"
                "For example: /setcooldown myinstauser 12"
            )
            return
        
        # Extract username and hours
        _, username, hours_str = parts
        
        # Validate hours
        try:
            hours = int(hours_str)
            if hours < 1:
                raise ValueError("Hours must be at least 1")
        except ValueError:
            bot.reply_to(message, "❌ Hours must be a positive number.")
            return
        
        # Update the cooldown
        success = account_manager.set_cooldown_hours(username, hours)
        
        if success:
            bot.reply_to(
                message,
                f"✅ Set cooldown period for @{username} to {hours} hours."
            )
        else:
            bot.reply_to(message, f"❌ Account @{username} not found.")
            
    # Return the registered commands for documentation
    return [
        {'command': 'addaccount', 'description': 'Add a new Instagram account'},
        {'command': 'removeaccount', 'description': 'Remove an Instagram account'},
        {'command': 'accounts', 'description': 'List all registered Instagram accounts'},
        {'command': 'rotate', 'description': 'Manually rotate to the next Instagram account'},
        {'command': 'setlimit', 'description': 'Set the daily request limit for an account'},
        {'command': 'setcooldown', 'description': 'Set the cooldown period for an account'},
    ]