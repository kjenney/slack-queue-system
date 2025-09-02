#!/usr/bin/env python3
"""
Slack Queue System - Main Queue Manager
Manages action items through Slack integration
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.slack_client import SlackClient
from src.database import DatabaseManager

class QueueManager:
    """Manages the action item queue system"""
    
    def __init__(self, db_path: str = 'data/queue.db'):
        self.db = DatabaseManager(db_path)
        self.slack = SlackClient()
        self.logger = logging.getLogger(__name__)
        
    def add_item(self, title: str, description: str = "", 
                 priority: str = "medium", assignee: str = None,
                 due_date: str = None, slack_user: str = None,
                 slack_channel: str = None) -> int:
        """Add a new item to the queue"""
        
        item_id = self.db.add_queue_item(
            title=title,
            description=description,
            priority=priority,
            assignee=assignee,
            due_date=due_date,
            slack_user=slack_user,
            slack_channel=slack_channel
        )
        
        self.logger.info(f"Added queue item #{item_id}: {title}")
        return item_id
    
    def update_item_status(self, item_id: int, status: str) -> bool:
        """Update the status of a queue item"""
        
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if status not in valid_statuses:
            self.logger.error(f"Invalid status: {status}")
            return False
            
        success = self.db.update_item_status(item_id, status)
        if success:
            self.logger.info(f"Updated item #{item_id} status to {status}")
            
            # Notify Slack if item was completed or cancelled
            if status in ['completed', 'cancelled']:
                item = self.db.get_item_by_id(item_id)
                if item and item['slack_channel']:
                    self.slack.send_message(
                        channel=item['slack_channel'],
                        text=f"✅ Task #{item_id} '{item['title']}' has been {status}"
                    )
        
        return success
    
    def get_pending_items(self, assignee: str = None) -> List[Dict]:
        """Get all pending items, optionally filtered by assignee"""
        return self.db.get_items_by_status('pending', assignee)
    
    def get_overdue_items(self) -> List[Dict]:
        """Get all overdue items"""
        return self.db.get_overdue_items()
    
    def process_slack_commands(self):
        """Process commands from Slack messages"""
        
        # Get recent messages from configured channels
        channels = os.getenv('SLACK_CHANNELS', '').split(',')
        
        for channel in channels:
            if not channel.strip():
                continue
                
            channel_name = channel.strip()
            channel_id = self.slack.resolve_channel_id(channel_name)
            
            if not channel_id:
                self.logger.warning(f"Could not resolve channel '{channel_name}' - skipping")
                continue
                
            messages = self.slack.get_recent_messages(channel_id)
            
            for msg in messages:
                # Skip if already processed
                if self.db.is_message_processed(msg['ts'], channel_id):
                    continue
                
                # Parse command
                command_data = self._parse_slack_command(msg['text'])
                
                if command_data:
                    self._execute_command(
                        command_data, 
                        msg.get('user', 'unknown'),
                        channel_id
                    )
                    
                    # Mark as processed
                    self.db.mark_message_processed(msg['ts'], channel_id)
    
    def _parse_slack_command(self, text: str) -> Optional[Dict]:
        """Parse Slack message for queue commands"""
        
        text = text.lower().strip()
        
        # Command patterns
        if text.startswith('!add task'):
            parts = text[9:].strip()
            return {
                'action': 'add',
                'title': parts
            }
        elif text.startswith('!list'):
            return {'action': 'list'}
        elif text.startswith('!complete'):
            try:
                item_id = int(text.split()[1])
                return {
                    'action': 'complete',
                    'item_id': item_id
                }
            except (IndexError, ValueError):
                return None
        elif text.startswith('!status'):
            return {'action': 'status'}
        elif text.startswith('!help'):
            return {'action': 'help'}
            
        return None
    
    def _execute_command(self, command: Dict, user: str, channel: str):
        """Execute a parsed command"""
        
        action = command.get('action')
        
        if action == 'add':
            item_id = self.add_item(
                title=command['title'],
                slack_user=user,
                slack_channel=channel
            )
            self.slack.send_message(
                channel=channel,
                text=f"✅ Added task #{item_id}: {command['title']}"
            )
            
        elif action == 'list':
            items = self.get_pending_items()
            if items:
                msg = "📋 *Pending Tasks:*\n"
                for item in items[:10]:  # Limit to 10 items
                    msg += f"• #{item['id']}: {item['title']} ({item['priority']})\n"
            else:
                msg = "No pending tasks!"
            self.slack.send_message(channel=channel, text=msg)
            
        elif action == 'complete':
            if self.update_item_status(command['item_id'], 'completed'):
                self.slack.send_message(
                    channel=channel,
                    text=f"✅ Marked task #{command['item_id']} as completed!"
                )
            else:
                self.slack.send_message(
                    channel=channel,
                    text=f"❌ Could not find task #{command['item_id']}"
                )
                
        elif action == 'status':
            stats = self.db.get_queue_stats()
            msg = f"""📊 *Queue Status:*
• Pending: {stats['pending']}
• In Progress: {stats['in_progress']}
• Completed Today: {stats['completed_today']}
• Total Items: {stats['total']}"""
            self.slack.send_message(channel=channel, text=msg)
            
        elif action == 'help':
            msg = """*Available Commands:*
• `!add task [description]` - Add a new task
• `!list` - Show pending tasks
• `!complete [task_id]` - Mark task as complete
• `!status` - Show queue statistics
• `!help` - Show this help message"""
            self.slack.send_message(channel=channel, text=msg)
    
    def send_daily_summary(self):
        """Send daily summary to Slack"""
        
        stats = self.db.get_queue_stats()
        overdue = self.get_overdue_items()
        
        msg = f"""📅 *Daily Queue Summary*
        
*Statistics:*
• Pending Tasks: {stats['pending']}
• In Progress: {stats['in_progress']}
• Completed Today: {stats['completed_today']}

*Overdue Tasks:* {len(overdue)}"""
        
        if overdue:
            msg += "\n"
            for item in overdue[:5]:
                msg += f"\n• #{item['id']}: {item['title']} (Due: {item['due_date']})"
        
        # Send to all configured channels
        channels = os.getenv('SLACK_CHANNELS', '').split(',')
        for channel in channels:
            if channel.strip():
                self.slack.send_message(channel=channel.strip(), text=msg)

def main():
    """Main entry point for the queue manager"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/queue_manager.log'),
            logging.StreamHandler()
        ]
    )
    
    manager = QueueManager()
    
    # Process any pending Slack commands
    manager.process_slack_commands()
    
    # Check if we should send daily summary (e.g., at 9 AM)
    now = datetime.now()
    if now.hour == 9 and now.minute < 5:
        manager.send_daily_summary()

if __name__ == "__main__":
    main()
