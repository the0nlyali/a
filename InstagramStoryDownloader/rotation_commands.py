"""
Handler for auto rotation commands in the Telegram bot.
"""

import logging
from typing import List, Optional
import telebot
from telebot import types

from account_manager import AccountManager

def is_admin(user_id: int, admin_ids: Optional[List[int]]) -> bool:
    """Check if a user is an admin."""
    if not admin_ids:
        return False
    return user_id in admin_ids

def register_rotation_commands(bot: telebot.TeleBot, instagram_handler, admin_ids: Optional[List[int]] = None):
    """
    Register automatic account rotation commands with the Telegram bot.
    
    Args:
        bot: The Telegram bot instance
        instagram_handler: The InstagramHandler instance
        admin_ids: List of Telegram user IDs that have admin privileges
    """
    if admin_ids is None:
        admin_ids = []
    
    @bot.message_handler(commands=['autorotate', 'startrotation'])
    def start_autorotate_command(message: types.Message):
        """
        Start the automatic account rotation system.
        Command: /autorotate or /startrotation
        """
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "⛔ Sorry, this command is only available to administrators.")
            return
        
        try:
            # Start the auto rotation
            success = instagram_handler.start_auto_rotation()
            
            if success:
                bot.reply_to(
                    message,
                    "✅ Automatic account rotation system has been activated!\n\n"
                    "Instagram accounts will be rotated automatically based on usage limits "
                    "and time intervals to avoid hitting Instagram's rate limits."
                )
            else:
                bot.reply_to(
                    message,
                    "⚠️ Failed to start automatic rotation system. Check logs for more details."
                )
        except Exception as e:
            logging.error(f"Error in autorotate command: {e}")
            bot.reply_to(message, f"❌ Error starting auto-rotation: {str(e)}")

    @bot.message_handler(commands=['stoprotation'])
    def stop_autorotate_command(message: types.Message):
        """
        Stop the automatic account rotation system.
        Command: /stoprotation
        """
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "⛔ Sorry, this command is only available to administrators.")
            return
        
        try:
            # Stop the auto rotation
            success = instagram_handler.stop_auto_rotation()
            
            if success:
                bot.reply_to(
                    message,
                    "✅ Automatic account rotation system has been deactivated.\n\n"
                    "You can still rotate accounts manually using the /rotate command."
                )
            else:
                bot.reply_to(
                    message,
                    "⚠️ Failed to stop automatic rotation system. It may not be running, "
                    "or there was an error. Check logs for more details."
                )
        except Exception as e:
            logging.error(f"Error in stoprotation command: {e}")
            bot.reply_to(message, f"❌ Error stopping auto-rotation: {str(e)}")

    @bot.message_handler(commands=['rotationstatus'])
    def rotation_status_command(message: types.Message):
        """
        Get the current status of the automatic rotation system.
        Command: /rotationstatus
        """
        user_id = message.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, admin_ids):
            bot.reply_to(message, "⛔ Sorry, this command is only available to administrators.")
            return
        
        try:
            # Get rotation status
            status = instagram_handler.get_auto_rotation_status()
            
            # Format the status message
            if status.get('error'):
                status_msg = f"⚠️ Auto-rotation status: {status.get('error')}"
            else:
                active = status.get('active', False)
                last_rotation = status.get('last_rotation', 'Never')
                rotation_count = status.get('rotation_count', 0)
                check_interval = status.get('check_interval', 0)
                
                if active:
                    status_text = "✅ Active"
                else:
                    status_text = "❌ Inactive"
                
                status_msg = (
                    f"📊 *Auto-Rotation Status*\n\n"
                    f"Status: {status_text}\n"
                    f"Total rotations: {rotation_count}\n"
                    f"Last rotation: {last_rotation}\n"
                    f"Check interval: {check_interval//60} minutes"
                )
                
                # Also include account status
                account_manager = getattr(instagram_handler, 'account_manager', None)
                if account_manager:
                    current = account_manager.get_current_account()
                    if current:
                        username = current.get('username', 'None')
                        req_count = current.get('request_count', 0)
                        daily_limit = current.get('daily_limit', 0)
                        
                        status_msg += f"\n\nCurrent account: @{username}"
                        status_msg += f"\nRequests: {req_count}/{daily_limit}"
                        
                        # Calculate percentage used
                        if daily_limit > 0:
                            percent_used = (req_count / daily_limit) * 100
                            status_msg += f" ({percent_used:.1f}%)"
            
            # Send the status message
            try:
                bot.reply_to(message, status_msg, parse_mode='Markdown')
            except Exception:
                # If markdown fails, try without formatting
                bot.reply_to(message, status_msg)
                
        except Exception as e:
            logging.error(f"Error in rotationstatus command: {e}")
            bot.reply_to(message, f"❌ Error getting rotation status: {str(e)}")