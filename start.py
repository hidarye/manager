#!/usr/bin/env python3
"""
Startup script for Telegram Channel Management Bot
This script checks the environment and starts the bot safely.
"""

import os
import sys
from pathlib import Path

def check_requirements():
    """Check if all requirements are installed"""
    try:
        import telegram
        import sqlalchemy
        import dotenv
        import apscheduler
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found")
        print("Please copy .env.example to .env and fill in your bot token and user ID")
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    admin_user_id = os.getenv('ADMIN_USER_ID')
    
    if not bot_token:
        print("❌ BOT_TOKEN not found in .env file")
        return False
    
    if not admin_user_id:
        print("❌ ADMIN_USER_ID not found in .env file")
        return False
    
    print("✅ Environment variables are configured")
    return True

def main():
    """Main startup function"""
    print("🤖 Starting Telegram Channel Management Bot...")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check environment
    if not check_env_file():
        sys.exit(1)
    
    print("=" * 50)
    print("🚀 Starting bot...")
    
    # Import and run bot
    try:
        from bot import TelegramChannelBot
        bot = TelegramChannelBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()