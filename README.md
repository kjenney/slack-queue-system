# Slack Queue System

A completely open-source queue management system that integrates with Slack, designed for Linux servers. Process action items and tasks through Slack commands without requiring public webhooks.

## Features

- **Slack Integration**: Manage tasks directly from Slack using simple commands
- **SQLite Database**: Lightweight, file-based database for queue storage
- **Cron-based Processing**: No webhooks needed - uses cron jobs to poll Slack
- **Priority Management**: Support for critical, high, medium, and low priority tasks
- **Assignee Tracking**: Assign tasks to specific team members
- **Due Date Management**: Track due dates and get overdue notifications
- **Daily Summaries**: Automatic daily queue status reports
- **Activity Logging**: Complete audit trail of all queue actions
- **100% Open Source**: All components are open source (Apache, MIT, or BSD licensed)

## Architecture

```
slack-queue-system/
├── src/
│   ├── queue_manager.py    # Main queue management logic
│   ├── slack_client.py     # Slack API integration
│   ├── database.py         # SQLite database operations
│   ├── cron_job.py        # Cron job entry point
│   └── api_server.py      # Local REST API server
├── config/
├── data/                   # SQLite database storage
├── logs/                   # Application logs
├── requirements.txt        # Python dependencies
├── setup.sh               # Installation script
└── .env.example           # Environment variable template
```

## Requirements

- Linux operating system
- Python 3.8 or higher
- SQLite3 (usually pre-installed on Linux)
- Slack workspace with bot creation permissions

## Installation

### 1. Clone or Copy the Project

```bash
cd /path/to/your/directory
# The project has been created at the specified location
```

### 2. Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Queue Manager") and select your workspace
4. Navigate to "OAuth & Permissions"
5. Add the following Bot Token Scopes:
   - `channels:history` - View messages in public channels
   - `channels:read` - View basic channel information
   - `chat:write` - Send messages
   - `groups:history` - View messages in private channels (optional)
   - `groups:read` - View private channel information (optional)
   - `users:read` - View user information
6. Install the app to your workspace
7. Copy the Bot User OAuth Token (starts with `xoxb-`)

### 3. Run the Setup Script

```bash
cd slack-queue-system
chmod +x setup.sh
./setup.sh
```

### 4. Configure Environment Variables

Edit the `.env` file with your Slack credentials:

```bash
nano .env
```

Update these values:
- `SLACK_BOT_TOKEN`: Your bot token from step 2
- `SLACK_CHANNELS`: Comma-separated list of channels to monitor
- `DAILY_SUMMARY_HOUR`: Hour to send daily summary (0-23)

### 5. Add Bot to Channels

In Slack, add your bot to the channels you want to monitor:
- Type `/invite @YourBotName` in each channel

## Usage

### Slack Commands

Send these commands in any monitored Slack channel:

- `!add task [description]` - Add a new task to the queue
- `!list` - Show pending tasks
- `!complete [task_id]` - Mark a task as complete
- `!status` - Show queue statistics
- `!help` - Show available commands

### Examples

```
User: !add task Review pull request #142
Bot: ✅ Added task #1: Review pull request #142

User: !list
Bot: 📋 Pending Tasks:
     • #1: Review pull request #142 (medium)
     • #2: Update documentation (low)

User: !complete 1
Bot: ✅ Marked task #1 as completed!

User: !status
Bot: 📊 Queue Status:
     • Pending: 3
     • In Progress: 2
     • Completed Today: 5
     • Total Items: 47
```

## Cron Job Configuration

The setup script automatically configures a cron job to run every 5 minutes:

```bash
*/5 * * * * cd /path/to/slack-queue-system && ./venv/bin/python src/cron_job.py
```

To modify the frequency, edit your crontab:

```bash
crontab -e
```

Common cron schedules:
- `*/5 * * * *` - Every 5 minutes (default)
- `*/10 * * * *` - Every 10 minutes
- `0 * * * *` - Every hour
- `*/2 * * * *` - Every 2 minutes (for testing)

## Manual Operations

### Test the System

```bash
cd slack-queue-system
source venv/bin/activate
python src/cron_job.py
```

### Local API Server

Start the local REST API server for programmatic access:

```bash
source venv/bin/activate
python src/api_server.py
```

The API server runs on `http://localhost:5000` by default and provides these endpoints:

**Update Task Status:**
```bash
# Set task #5 to in_progress
curl -X PUT http://localhost:5000/api/tasks/5/status \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Set task #5 to completed
curl -X PUT http://localhost:5000/api/tasks/5/status \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

**Get Tasks:**
```bash
# Get all tasks
curl http://localhost:5000/api/tasks

# Get tasks by status
curl http://localhost:5000/api/tasks?status=in_progress

# Get specific task
curl http://localhost:5000/api/tasks/5
```

**Other Endpoints:**
```bash
# Get queue statistics
curl http://localhost:5000/api/stats

# Create new task
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "New task", "description": "Task description", "priority": "high"}'

# Health check
curl http://localhost:5000/api/health
```

Valid task statuses: `pending`, `in_progress`, `completed`, `cancelled`

### Direct Database Operations

```bash
source venv/bin/activate
python src/database.py  # Test database operations
```

### View Logs

```bash
tail -f logs/cron.log
tail -f logs/queue_manager.log
```

## Advanced Configuration

### Database Management

The SQLite database is stored in `data/queue.db`. You can interact with it directly:

```bash
sqlite3 data/queue.db
.tables
.schema queue_items
SELECT * FROM queue_items WHERE status='pending';
```

### Custom Priority Levels

Edit `src/queue_manager.py` to modify priority levels and their emoji indicators:

```python
priority_emoji = {
    'low': '🟢',
    'medium': '🟡', 
    'high': '🔴',
    'critical': '🚨'
}
```

### Notification Schedule

Modify when daily summaries are sent by changing `DAILY_SUMMARY_HOUR` in `.env`.

## Troubleshooting

### Bot Not Responding

1. Check if the bot is in the channel: Look for the bot in the channel member list
2. Verify credentials: Ensure `SLACK_BOT_TOKEN` is correct in `.env`
3. Check logs: `tail -f logs/cron.log`
4. Test manually: `python src/cron_job.py`

### Database Issues

```bash
# Reset database
rm data/queue.db
python -c "from src.database import DatabaseManager; DatabaseManager()"
```

### Permission Errors

```bash
# Fix file permissions
chmod +x src/*.py
chmod 755 logs/
chmod 755 data/
```

## Security Notes

- Never commit `.env` file to version control
- Store bot tokens securely
- Use private channels for sensitive tasks
- Regularly rotate Slack tokens
- Consider encrypting the SQLite database for sensitive data

## Open Source Components

All components used are fully open source:

- **Python**: PSF License
- **slack-sdk**: Apache License 2.0
- **python-dotenv**: BSD 3-Clause License
- **schedule**: MIT License
- **flask**: BSD 3-Clause License
- **SQLite**: Public Domain

## License

This project can be used under the MIT License.

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Verify Slack app permissions
3. Ensure cron job is running: `crontab -l`
4. Test components individually using the test scripts
