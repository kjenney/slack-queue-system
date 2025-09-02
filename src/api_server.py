#!/usr/bin/env python3
"""
Local API server for queue management
Provides REST endpoints to manage queue tasks
"""

from flask import Flask, request, jsonify
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.queue_manager import QueueManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize queue manager
db_path = str(project_root / 'data' / 'queue.db')
queue_manager = QueueManager(db_path=db_path)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks with optional status filter"""
    status = request.args.get('status')
    
    try:
        if status:
            tasks = queue_manager.db.get_items_by_status(status)
        else:
            tasks = queue_manager.db.get_all_items()
        
        return jsonify({
            'success': True,
            'tasks': tasks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task by ID"""
    try:
        task = queue_manager.db.get_item_by_id(task_id)
        if task:
            return jsonify({
                'success': True,
                'task': task
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """Update task status"""
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({
            'success': False,
            'error': 'Status is required'
        }), 400
    
    status = data['status']
    valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
    
    if status not in valid_statuses:
        return jsonify({
            'success': False,
            'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
        }), 400
    
    try:
        success = queue_manager.update_item_status(task_id, status)
        if success:
            return jsonify({
                'success': True,
                'message': f'Task #{task_id} status updated to {status}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update task status'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({
            'success': False,
            'error': 'Title is required'
        }), 400
    
    try:
        task_id = queue_manager.db.add_item(
            title=data['title'],
            description=data.get('description', ''),
            priority=data.get('priority', 'medium'),
            due_date=data.get('due_date'),
            user=data.get('user', 'api')
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': f'Task #{task_id} created successfully'
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get queue statistics"""
    try:
        stats = queue_manager.db.get_queue_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'queue-api'
    })

if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5000))
    host = os.getenv('API_HOST', '127.0.0.1')
    debug = os.getenv('API_DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Queue API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)