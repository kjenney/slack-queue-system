#!/usr/bin/env python3
"""
Cron job script for processing Slack messages and queue items
Run this via cron to process commands and send notifications
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.queue_manager import QueueManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging():
    """Setup logging configuration"""
    
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Create a log file with today's date
    log_file = log_dir / f"cron_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """Main cron job execution"""
    
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("Starting cron job execution")
    
    try:
        # Initialize queue manager
        db_path = str(project_root / 'data' / 'queue.db')
        manager = QueueManager(db_path=db_path)
        
        # Process Slack commands
        logger.info("Processing Slack commands...")
        manager.process_slack_commands()
        
        # Check for overdue items and notify
        overdue_items = manager.get_overdue_items()
        if overdue_items:
            logger.info(f"Found {len(overdue_items)} overdue items")
            
            # Send notification about overdue items
            channels = os.getenv('SLACK_CHANNELS', '').split(',')
            for channel in channels:
                if channel.strip():
                    msg = f"⚠️ *Overdue Tasks Alert*\n"
                    msg += f"There are {len(overdue_items)} overdue tasks:\n"
                    
                    for item in overdue_items[:5]:  # Limit to first 5
                        msg += f"• #{item['id']}: {item['title']} (Due: {item['due_date']})\n"
                    
                    if len(overdue_items) > 5:
                        msg += f"... and {len(overdue_items) - 5} more"
                    
                    manager.slack.send_message(channel=channel.strip(), text=msg)
        
        # Send daily summary if it's the configured time
        hour = int(os.getenv('DAILY_SUMMARY_HOUR', '9'))
        current_hour = datetime.now().hour
        
        if current_hour == hour:
            logger.info("Sending daily summary...")
            manager.send_daily_summary()
        
        # Clean up old processed messages (weekly)
        if datetime.now().weekday() == 0 and current_hour == 2:  # Monday at 2 AM
            logger.info("Running weekly cleanup...")
            manager.db.cleanup_old_processed_messages(days=7)
        
        logger.info("Cron job completed successfully")
        
    except Exception as e:
        logger.error(f"Error during cron job execution: {e}", exc_info=True)
        
        # Send error notification to Slack if critical
        try:
            error_channel = os.getenv('SLACK_ERROR_CHANNEL', os.getenv('SLACK_CHANNELS', '').split(',')[0])
            if error_channel:
                from src.slack_client import SlackClient
                slack = SlackClient()
                slack.send_message(
                    channel=error_channel.strip(),
                    text=f"❌ Queue system cron job error: {str(e)}"
                )
        except:
            pass  # Don't fail the entire job if error notification fails
        
        sys.exit(1)

if __name__ == "__main__":
    main()
