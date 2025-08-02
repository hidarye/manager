@echo off
echo 🤖 Setting up Telegram Channel Management Bot...
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo ✅ Python is installed

REM Install requirements
echo 📦 Installing Python packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install packages
    pause
    exit /b 1
)

echo ✅ All packages installed successfully

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    copy .env.example .env
    echo ✅ .env file created from template
    echo.
    echo ⚠️  IMPORTANT: Please edit the .env file and add your:
    echo    - BOT_TOKEN ^(get from @BotFather^)
    echo    - ADMIN_USER_ID ^(get from @userinfobot^)
    echo.
    echo Opening .env file for editing...
    notepad .env
) else (
    echo ✅ .env file already exists
)

echo.
echo 🎉 Setup completed successfully!
echo.
echo 📋 Next steps:
echo 1. Make sure your .env file has the correct BOT_TOKEN and ADMIN_USER_ID
echo 2. Run the bot with: python start.py
echo    or: python bot.py
echo.
echo 📚 For detailed instructions, see README.md
echo.
pause