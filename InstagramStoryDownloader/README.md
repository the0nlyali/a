# Instagram Content Downloader Telegram Bot

A Telegram bot that allows users to download Instagram stories, posts, and reels by providing profile URLs or usernames.

## Features

- Download Instagram stories from public profiles
- Download Instagram posts (including carousel posts with multiple photos/videos)
- Download Instagram reels (videos)
- Support for both image and video content
- Simple user interface through Telegram commands
- Handles various error cases (private accounts, invalid URLs, etc.)
- In-app Instagram credential management using secure memory-only storage
- Interactive Instagram verification code handling (simply send the code when prompted)
- Web interface to monitor bot status
- 24/7 operation with keep-alive mechanism

## Requirements

- Python 3.11+
- pyTelegramBotAPI (telebot) library
- instagrapi library for Instagram interaction
- Flask for web interface
- Pillow (PIL) for image processing

## Environment Variables

The bot requires the following environment variables:

- `TELEGRAM_TOKEN`: Your Telegram Bot API token (required)

Instagram credentials can now be provided directly through the bot's `/login` command instead of environment variables, which provides better security since credentials are stored only in memory and not in environment variables or on disk.

## Usage

1. Start a chat with the bot on Telegram
2. Send the bot one of the following:
   - An Instagram profile URL or username to download stories (e.g., `https://www.instagram.com/username` or just `username`)
   - An Instagram post URL to download posts (e.g., `https://www.instagram.com/p/CODE`)
   - An Instagram reel URL to download reels (e.g., `https://www.instagram.com/reel/CODE`)
3. The bot will download and send the requested content to you

### Bot Commands

- `/start` - Show welcome message and basic instructions
- `/help` - Display detailed help information
- `/login username password` - Set your Instagram credentials (stored in memory with optional session saving)
- `/status` - Check if you're currently logged in to Instagram
- `/verify CODE` - Enter the 6-digit verification code when Instagram requires authentication verification (alternatively, simply send the code when prompted - the bot will recognize it automatically)

### Instagram Authentication Process

The bot has an improved Instagram authentication system that:

1. Provides multiple login retry attempts with appropriate error handling
2. Saves login sessions to improve reconnection speed (stored locally in the temp directory)
3. Automatically detects when Instagram requires verification codes
4. Clearly identifies different types of login errors (wrong credentials, IP blocks, challenges)
5. Provides specific error messages to guide you through the login process
6. Automatically handles Instagram security challenges with interactive verification
7. Offers a simple verification process where you can just type the 6-digit code without commands
8. Shows clear success/failure messages throughout the login process

## Technical Details

The bot uses:
- pyTelegramBotAPI (telebot) for Telegram API interaction
- instagrapi for accessing Instagram content (more reliable than instaloader)
- Flask web server for monitoring and keep-alive
- Multi-threading to handle both web interface and bot operation
- Temporary local storage for downloaded media before sending
- Self-pinging mechanism to prevent the application from sleeping
- Interactive verification system for handling Instagram security challenges (with user state tracking)
- Non-blocking background authentication to avoid web server disruptions
- Secure in-memory credential storage with better security
- Session persistence with optional login session saving for faster reconnections
- Multiple login retry attempts with detailed error reporting
- Dedicated login commands directly in the Telegram interface
- Enhanced error handling with specific error messages for different login issues

## Web Interface

The bot includes a simple web interface that:
- Shows the current bot status
- Displays the time of the last keep-alive ping
- Provides usage instructions
- Auto-refreshes every 5 minutes to help keep the bot alive

## Keeping the Bot Running 24/7

The bot includes a built-in keep-alive mechanism that:
1. Pings itself every 5 minutes
2. Has an auto-refresh meta tag in the web interface
3. Logs ping activity for monitoring

For even more reliable 24/7 operation, you can:
- Set up an external service like UptimeRobot to ping your app
- Upgrade to a paid Replit plan that supports always-on applications

## Limitations

- Can only access public Instagram profiles or profiles the bot has access to via provided credentials
- Large video files may not be sendable via Telegram (50MB limit)
- Instagram may rate-limit excessive requests (basic protection built in)
- Instagram frequently requires verification codes for login (handled interactively by the bot)
- Instagram may temporarily block logins from server IP addresses (bot includes clear error messages)
- Server environments may trigger Instagram's security systems more frequently than personal devices
- Session saving helps reduce login frequency but cannot completely avoid Instagram security checks
- Free Replit instances may still sleep despite keep-alive mechanisms
- Currently no caching system (identical requests will re-download content)
- Downloading from private profiles requires valid Instagram credentials
