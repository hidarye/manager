#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script for Telegram Channel Bot
This script helps create the PostgreSQL database and user for the bot.
"""

import os
import sys
import getpass
import subprocess
from pathlib import Path

def check_postgresql():
    """Check if PostgreSQL is installed and accessible"""
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ PostgreSQL found: {result.stdout.strip()}")
            return True
        else:
            print("❌ PostgreSQL not found in PATH")
            return False
    except FileNotFoundError:
        print("❌ PostgreSQL not installed or not in PATH")
        return False

def create_database():
    """Create database and user using psql"""
    print("\n🔧 Setting up PostgreSQL database...")
    
    # Get PostgreSQL superuser credentials
    pg_user = input("Enter PostgreSQL superuser (default: postgres): ").strip() or "postgres"
    pg_password = getpass.getpass("Enter PostgreSQL superuser password: ")
    pg_host = input("Enter PostgreSQL host (default: localhost): ").strip() or "localhost"
    pg_port = input("Enter PostgreSQL port (default: 5432): ").strip() or "5432"
    
    print("\n📝 Database configuration:")
    db_name = input("Enter database name (default: telegram_bot_db): ").strip() or "telegram_bot_db"
    bot_user = input("Enter bot user name (default: bot_user): ").strip() or "bot_user"
    bot_password = getpass.getpass("Enter bot user password (default: secure_bot_password_123): ") or "secure_bot_password_123"
    
    # Create SQL commands
    sql_commands = f"""
-- Create database
CREATE DATABASE {db_name};

-- Create user for the bot
CREATE USER {bot_user} WITH PASSWORD '{bot_password}';

-- Grant privileges to the bot user
GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {bot_user};

-- Connect to the database
\\c {db_name};

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO {bot_user};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {bot_user};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {bot_user};

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {bot_user};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {bot_user};
"""
    
    # Write SQL to temporary file
    sql_file = Path("temp_setup.sql")
    sql_file.write_text(sql_commands)
    
    try:
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = pg_password
        
        # Run psql command
        cmd = [
            'psql',
            '-h', pg_host,
            '-p', pg_port,
            '-U', pg_user,
            '-d', 'postgres',  # Connect to default postgres database first
            '-f', str(sql_file)
        ]
        
        print("\n🚀 Executing database setup...")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database setup completed successfully!")
            
            # Create .env file with database URL
            database_url = f"postgresql://{bot_user}:{bot_password}@{pg_host}:{pg_port}/{db_name}"
            update_env_file(database_url)
            
        else:
            print("❌ Database setup failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running database setup: {e}")
        return False
    finally:
        # Clean up temporary file
        if sql_file.exists():
            sql_file.unlink()
    
    return True

def update_env_file(database_url):
    """Update .env file with database URL"""
    env_file = Path(".env")
    
    if env_file.exists():
        # Read existing .env file
        content = env_file.read_text()
        lines = content.split('\n')
        
        # Update DATABASE_URL line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('DATABASE_URL='):
                lines[i] = f"DATABASE_URL={database_url}"
                updated = True
                break
        
        if not updated:
            lines.append(f"DATABASE_URL={database_url}")
        
        # Write back to file
        env_file.write_text('\n'.join(lines))
        print(f"✅ Updated .env file with database URL")
    else:
        # Create new .env file from example
        env_example = Path(".env.example")
        if env_example.exists():
            content = env_example.read_text()
            content = content.replace(
                'DATABASE_URL=postgresql://username:password@localhost:5432/telegram_bot',
                f'DATABASE_URL={database_url}'
            )
            env_file.write_text(content)
            print(f"✅ Created .env file with database URL")
        else:
            print("⚠️  .env.example not found. Please create .env file manually with:")
            print(f"DATABASE_URL={database_url}")

def test_connection():
    """Test database connection"""
    print("\n🧪 Testing database connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from database import create_tables, SessionLocal
        
        # Create tables
        create_tables()
        print("✅ Database tables created successfully")
        
        # Test connection
        db = SessionLocal()
        try:
            # Simple query to test connection
            db.execute("SELECT 1")
            print("✅ Database connection test successful")
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🐘 PostgreSQL Database Setup for Telegram Bot")
    print("=" * 50)
    
    # Check if PostgreSQL is available
    if not check_postgresql():
        print("\n📥 Please install PostgreSQL first:")
        print("- Ubuntu/Debian: sudo apt install postgresql postgresql-contrib")
        print("- CentOS/RHEL: sudo yum install postgresql-server postgresql-contrib")
        print("- macOS: brew install postgresql")
        print("- Windows: Download from https://www.postgresql.org/download/")
        return 1
    
    # Create database
    if not create_database():
        return 1
    
    # Test connection
    if not test_connection():
        print("\n⚠️  Database setup completed but connection test failed.")
        print("Please check your .env file and database configuration.")
        return 1
    
    print("\n🎉 PostgreSQL setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Your database is ready to use")
    print("2. Start the bot with: python start.py")
    print("3. The bot will automatically create the required tables")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())