#!/bin/bash

# Telegram Channel Management Bot Setup Script
echo "🤖 Setting up Telegram Channel Management Bot..."
echo "================================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Python 3.8 or higher is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

echo "✅ pip3 is available"

# Install requirements
echo "📦 Installing Python packages..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ All packages installed successfully"
else
    echo "❌ Failed to install packages"
    exit 1
fi

# Check PostgreSQL installation
echo "🐘 Checking PostgreSQL installation..."
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL is installed"
else
    echo "⚠️  PostgreSQL not found. Please install PostgreSQL:"
    echo "- Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "- CentOS/RHEL: sudo yum install postgresql-server postgresql-contrib"
    echo "- macOS: brew install postgresql"
    echo ""
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created from template"
    echo ""
    echo "⚠️  IMPORTANT: Please edit the .env file and add your:"
    echo "   - BOT_TOKEN (get from @BotFather)"
    echo "   - ADMIN_USER_ID (get from @userinfobot)"
    echo ""
    echo "📝 Edit .env file now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        elif command -v vi &> /dev/null; then
            vi .env
        else
            echo "Please edit .env file manually with your preferred editor"
        fi
    fi
else
    echo "✅ .env file already exists"
fi

# Make start.py executable
chmod +x start.py

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Set up PostgreSQL database: python3 setup_postgres.py"
echo "2. Make sure your .env file has the correct BOT_TOKEN and ADMIN_USER_ID"
echo "3. Test setup: python3 test_setup.py"
echo "4. Run the bot with: python3 start.py"
echo ""
echo "📚 For detailed instructions, see README.md"
echo ""