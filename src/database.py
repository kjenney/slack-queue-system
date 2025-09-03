#!/usr/bin/env python3
"""
Database Manager for SQLite queue storage
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os

class DatabaseManager:
    """Manages SQLite database operations for the queue system"""
    
    def __init__(self, db_path: str = 'data/queue.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Queue items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS queue_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    assignee TEXT,
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    slack_user TEXT,
                    slack_channel TEXT,
                    metadata TEXT
                )
            ''')
            
            # Processed messages table (to avoid reprocessing)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_ts TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    UNIQUE(message_ts, channel)
                )
            ''')
            
            # Activity log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    action TEXT NOT NULL,
                    user TEXT,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (item_id) REFERENCES queue_items (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_queue_status 
                ON queue_items(status)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_queue_assignee 
                ON queue_items(assignee)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_queue_due_date 
                ON queue_items(due_date)
            ''')
            
            conn.commit()
            
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def add_queue_item(self, title: str, description: str = "", 
                      priority: str = "medium", assignee: str = None,
                      due_date: str = None, slack_user: str = None,
                      slack_channel: str = None, metadata: Dict = None) -> int:
        """Add a new item to the queue"""
        
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO queue_items 
                (title, description, priority, assignee, due_date, 
                 created_at, updated_at, slack_user, slack_channel, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title, description, priority, assignee, due_date,
                now, now, slack_user, slack_channel,
                json.dumps(metadata) if metadata else None
            ))
            
            item_id = cursor.lastrowid
            
            # Log the action
            self._log_activity(cursor, item_id, 'created', slack_user)
            
            conn.commit()
            
        return item_id
    
    def update_item_status(self, item_id: int, status: str, user: str = None) -> bool:
        """Update the status of a queue item"""
        
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update status
            completed_at = now if status == 'completed' else None
            
            cursor.execute('''
                UPDATE queue_items 
                SET status = ?, updated_at = ?, completed_at = ?
                WHERE id = ?
            ''', (status, now, completed_at, item_id))
            
            if cursor.rowcount > 0:
                # Log the action
                self._log_activity(cursor, item_id, f'status_changed_to_{status}', user)
                conn.commit()
                return True
                
        return False
    
    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Get a queue item by ID"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM queue_items WHERE id = ?', (item_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
                
        return None
    
    def get_all_items(self) -> List[Dict]:
        """Get all queue items"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM queue_items ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_items_by_status(self, status: str, assignee: str = None) -> List[Dict]:
        """Get items by status, optionally filtered by assignee"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if assignee:
                cursor.execute('''
                    SELECT * FROM queue_items 
                    WHERE status = ? AND assignee = ?
                    ORDER BY 
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        due_date ASC
                ''', (status, assignee))
            else:
                cursor.execute('''
                    SELECT * FROM queue_items 
                    WHERE status = ?
                    ORDER BY 
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                        END,
                        due_date ASC
                ''', (status,))
                
            return [dict(row) for row in cursor.fetchall()]
    
    def get_overdue_items(self) -> List[Dict]:
        """Get all overdue items"""
        
        today = datetime.now().date().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM queue_items 
                WHERE status IN ('pending', 'in_progress')
                AND due_date < ?
                AND due_date IS NOT NULL
                ORDER BY due_date ASC
            ''', (today,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_queue_stats(self) -> Dict:
        """Get statistics about the queue"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count by status
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM queue_items
                GROUP BY status
            ''')
            
            for row in cursor.fetchall():
                stats[row[0]] = row[1]
                
            # Completed today
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            
            cursor.execute('''
                SELECT COUNT(*) FROM queue_items
                WHERE status = 'completed'
                AND completed_at >= ?
            ''', (today_start,))
            
            stats['completed_today'] = cursor.fetchone()[0]
            
            # Total items
            cursor.execute('SELECT COUNT(*) FROM queue_items')
            stats['total'] = cursor.fetchone()[0]
            
            # Fill in missing statuses with 0
            for status in ['pending', 'in_progress', 'completed', 'cancelled']:
                if status not in stats:
                    stats[status] = 0
                    
        return stats
    
    def is_message_processed(self, message_ts: str, channel: str) -> bool:
        """Check if a Slack message has already been processed"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM processed_messages
                WHERE message_ts = ? AND channel = ?
            ''', (message_ts, channel))
            
            return cursor.fetchone()[0] > 0
    
    def mark_message_processed(self, message_ts: str, channel: str):
        """Mark a Slack message as processed"""
        
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO processed_messages (message_ts, channel, processed_at)
                    VALUES (?, ?, ?)
                ''', (message_ts, channel, now))
                conn.commit()
            except sqlite3.IntegrityError:
                # Message already processed
                pass
    
    def _log_activity(self, cursor, item_id: int, action: str, 
                     user: str = None, details: str = None):
        """Log an activity to the activity log"""
        
        cursor.execute('''
            INSERT INTO activity_log (item_id, action, user, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (item_id, action, user, datetime.now().isoformat(), details))
    
    def get_item_history(self, item_id: int) -> List[Dict]:
        """Get the activity history for a queue item"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM activity_log
                WHERE item_id = ?
                ORDER BY timestamp DESC
            ''', (item_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_processed_messages(self, days: int = 7):
        """Clean up old processed message records"""
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM processed_messages
                WHERE processed_at < ?
            ''', (cutoff,))
            
            deleted = cursor.rowcount
            conn.commit()
            
            if deleted > 0:
                self.logger.info(f"Cleaned up {deleted} old processed message records")

def main():
    """Test the database manager"""
    
    logging.basicConfig(level=logging.INFO)
    
    db = DatabaseManager()
    
    # Add test item
    item_id = db.add_queue_item(
        title="Test task",
        description="This is a test task",
        priority="high",
        assignee="john.doe"
    )
    
    print(f"Created item #{item_id}")
    
    # Get stats
    stats = db.get_queue_stats()
    print(f"Queue stats: {stats}")
    
    # Get pending items
    pending = db.get_items_by_status('pending')
    print(f"Pending items: {len(pending)}")

if __name__ == "__main__":
    main()
