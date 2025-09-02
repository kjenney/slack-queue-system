#!/bin/bash

# Slack Queue System Installation Script
# This script sets up the Slack queue system on a Linux machine

set -e  # Exit on error

echo "================================"
echo "Slack Queue System Installation"
echo "================================"

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Warning: This script is designed for Linux. You may need to adjust for your OS."
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "1. Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python version: $PYTHON_VERSION"

echo "2. Creating virtual environment..."
cd "$SCRIPT_DIR"
python3 -m venv venv

echo "3. Activating virtual environment..."
source venv/bin/activate

echo "4. Upgrading pip..."
pip install --upgrade pip

echo "5. Installing Python dependencies..."
pip install -r requirements.txt

echo "6. Creating .env file from template..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your Slack credentials."
else
    echo ".env file already exists. Skipping..."
fi

echo "7. Setting up cron job..."
# Get the full path to the Python interpreter in the virtual environment
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
CRON_SCRIPT="$SCRIPT_DIR/src/cron_job.py"

# Create a cron entry
CRON_ENTRY="*/5 * * * * cd $SCRIPT_DIR && $PYTHON_PATH $CRON_SCRIPT >> $SCRIPT_DIR/logs/cron.log 2>&1"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "$CRON_SCRIPT"; then
    echo "Cron job already exists. Skipping..."
else
    # Add the cron entry
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "Added cron job to run every 5 minutes"
fi

echo "8. Setting executable permissions..."
chmod +x src/*.py
chmod +x setup.sh

echo "9. Creating initial database..."
$PYTHON_PATH -c "from src.database import DatabaseManager; DatabaseManager()"

echo ""
echo "================================"
echo "Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your Slack Bot Token and channel configuration"
echo "2. Ensure your Slack app has the following OAuth scopes:"
echo "   - channels:history"
echo "   - channels:read"
echo "   - chat:write"
echo "   - groups:history (for private channels)"
echo "   - groups:read (for private channels)"
echo "   - users:read"
echo "3. Add the bot to the channels you want to monitor"
echo "4. The cron job will run every 5 minutes to process commands"
echo ""
echo "To test the installation:"
echo "  source venv/bin/activate"
echo "  python src/cron_job.py"
echo ""
echo "To view logs:"
echo "  tail -f logs/cron.log"
echo ""
echo "Available Slack commands:"
echo "  !add task [description] - Add a new task"
echo "  !list - Show pending tasks"
echo "  !complete [task_id] - Mark task as complete"
echo "  !status - Show queue statistics"
echo "  !help - Show help message"
