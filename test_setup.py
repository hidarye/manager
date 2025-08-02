#!/usr/bin/env python3
"""
Test script to verify bot setup and configuration
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required packages can be imported"""
    print("🧪 Testing package imports...")
    
    try:
        import telegram
        print("✅ python-telegram-bot")
    except ImportError:
        print("❌ python-telegram-bot - run: pip install python-telegram-bot")
        return False
    
    try:
        import sqlalchemy
        print("✅ sqlalchemy")
    except ImportError:
        print("❌ sqlalchemy - run: pip install sqlalchemy")
        return False
    
    try:
        import dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv - run: pip install python-dotenv")
        return False
    
    try:
        import apscheduler
        print("✅ apscheduler")
    except ImportError:
        print("❌ apscheduler - run: pip install apscheduler")
        return False
    
    return True

def test_env_config():
    """Test environment configuration"""
    print("\n🔧 Testing environment configuration...")
    
    if not Path(".env").exists():
        print("❌ .env file not found")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    admin_user_id = os.getenv('ADMIN_USER_ID')
    
    if not bot_token or bot_token == 'your_bot_token_here':
        print("❌ BOT_TOKEN not configured properly")
        return False
    else:
        print("✅ BOT_TOKEN configured")
    
    if not admin_user_id or admin_user_id == 'your_telegram_user_id':
        print("❌ ADMIN_USER_ID not configured properly")
        return False
    else:
        print("✅ ADMIN_USER_ID configured")
    
    return True

def test_database():
    """Test database setup"""
    print("\n💾 Testing database setup...")
    
    try:
        from database import create_tables, SessionLocal, Channel
        create_tables()
        print("✅ Database tables created successfully")
        
        # Test database connection
        db = SessionLocal()
        try:
            # Simple query to test connection
            count = db.query(Channel).count()
            print(f"✅ Database connection working (found {count} channels)")
        finally:
            db.close()
        
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_bot_initialization():
    """Test bot initialization without starting"""
    print("\n🤖 Testing bot initialization...")
    
    try:
        from bot import TelegramChannelBot
        bot = TelegramChannelBot()
        print("✅ Bot initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Bot initialization error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Bot Setup Tests")
    print("=" * 40)
    
    tests = [
        ("Package Imports", test_imports),
        ("Environment Config", test_env_config),
        ("Database Setup", test_database),
        ("Bot Initialization", test_bot_initialization)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n❌ {test_name} failed")
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your bot is ready to run.")
        print("Start the bot with: python start.py")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())