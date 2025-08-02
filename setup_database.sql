-- PostgreSQL Database Setup Script for Telegram Channel Bot
-- Run this script as a PostgreSQL superuser to create the database and user

-- Create database
CREATE DATABASE telegram_bot_db;

-- Create user for the bot
CREATE USER bot_user WITH PASSWORD 'secure_bot_password_123';

-- Grant privileges to the bot user
GRANT ALL PRIVILEGES ON DATABASE telegram_bot_db TO bot_user;

-- Connect to the telegram_bot_db database
\c telegram_bot_db;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO bot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO bot_user;

-- Display connection info
\echo 'Database setup completed!'
\echo 'Database: telegram_bot_db'
\echo 'User: bot_user'
\echo 'Password: secure_bot_password_123'
\echo ''
\echo 'Update your .env file with:'
\echo 'DATABASE_URL=postgresql://bot_user:secure_bot_password_123@localhost:5432/telegram_bot_db'