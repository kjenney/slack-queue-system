#!/usr/bin/env python3
"""
Slack Client for interacting with Slack API
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SlackClient:
    """Handles all Slack API interactions"""
    
    def __init__(self):
        self.token = os.getenv('SLACK_BOT_TOKEN')
        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN environment variable not set")
            
        self.client = WebClient(token=self.token)
        self.logger = logging.getLogger(__name__)
        self.bot_user_id = self._get_bot_user_id()
        
    def _get_bot_user_id(self) -> str:
        """Get the bot's user ID"""
        try:
            response = self.client.auth_test()
            return response['user_id']
        except SlackApiError as e:
            self.logger.error(f"Error getting bot user ID: {e}")
            return None
    
    def send_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> bool:
        """Send a message to a Slack channel"""
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
            self.logger.info(f"Message sent to {channel}")
            return True
        except SlackApiError as e:
            self.logger.error(f"Error sending message: {e}")
            return False
    
    def get_recent_messages(self, channel: str, hours: int = 1) -> List[Dict]:
        """Get recent messages from a channel"""
        
        # Calculate timestamp for X hours ago
        oldest = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        try:
            response = self.client.conversations_history(
                channel=channel,
                oldest=str(oldest),
                limit=100
            )
            
            messages = []
            for msg in response['messages']:
                # Skip bot's own messages
                if msg.get('user') == self.bot_user_id:
                    continue
                    
                # Skip messages without text
                if 'text' not in msg:
                    continue
                    
                messages.append({
                    'ts': msg['ts'],
                    'user': msg.get('user', 'unknown'),
                    'text': msg['text'],
                    'thread_ts': msg.get('thread_ts')
                })
                
            return messages
            
        except SlackApiError as e:
            self.logger.error(f"Error getting messages from {channel}: {e}")
            return []
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get information about a Slack user"""
        
        try:
            response = self.client.users_info(user=user_id)
            return {
                'id': user_id,
                'name': response['user']['name'],
                'real_name': response['user'].get('real_name', ''),
                'email': response['user'].get('profile', {}).get('email', '')
            }
        except SlackApiError as e:
            self.logger.error(f"Error getting user info for {user_id}: {e}")
            return None
    
    def list_channels(self) -> List[Dict]:
        """List all channels the bot is a member of"""
        
        try:
            response = self.client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True
            )
            
            channels = []
            for channel in response['channels']:
                if channel.get('is_member'):
                    channels.append({
                        'id': channel['id'],
                        'name': channel['name'],
                        'is_private': channel.get('is_private', False)
                    })
                    
            return channels
            
        except SlackApiError as e:
            self.logger.error(f"Error listing channels: {e}")
            return []
    
    def send_formatted_message(self, channel: str, blocks: List[Dict]) -> bool:
        """Send a formatted message with blocks to Slack"""
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks
            )
            self.logger.info(f"Formatted message sent to {channel}")
            return True
        except SlackApiError as e:
            self.logger.error(f"Error sending formatted message: {e}")
            return False
    
    def create_task_block(self, task_id: int, title: str, 
                         priority: str, assignee: str = None,
                         due_date: str = None) -> List[Dict]:
        """Create a formatted block for a task"""
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Task #{task_id}*\n{title}"
                }
            },
            {
                "type": "context",
                "elements": []
            }
        ]
        
        # Add priority
        priority_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴',
            'critical': '🚨'
        }
        
        context_elements = [
            {
                "type": "mrkdwn",
                "text": f"{priority_emoji.get(priority, '⚪')} Priority: {priority}"
            }
        ]
        
        if assignee:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"👤 Assignee: {assignee}"
            })
            
        if due_date:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"📅 Due: {due_date}"
            })
            
        blocks[1]['elements'] = context_elements
        
        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Complete"
                    },
                    "style": "primary",
                    "value": f"complete_{task_id}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "In Progress"
                    },
                    "value": f"progress_{task_id}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Cancel"
                    },
                    "style": "danger",
                    "value": f"cancel_{task_id}"
                }
            ]
        })
        
        return blocks

def main():
    """Test the Slack client"""
    
    logging.basicConfig(level=logging.INFO)
    
    client = SlackClient()
    
    # List available channels
    channels = client.list_channels()
    print("Available channels:")
    for ch in channels:
        print(f"  - {ch['name']} ({ch['id']})")
    
    # Test sending a message (if SLACK_CHANNELS is set)
    test_channel = os.getenv('SLACK_CHANNELS', '').split(',')[0]
    if test_channel:
        client.send_message(
            channel=test_channel,
            text="🤖 Slack Queue System is online!"
        )

if __name__ == "__main__":
    main()
