#!/usr/bin/env python3
"""
Initialize the Slack Queue System
This script helps with initial setup and configuration
"""

import os
import sys
from pathlib import Path

def main():
    """Initialize the queue system"""
    
    print("Slack Queue System Initializer")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # Get project root
    project_root = Path(__file__).parent
    
    # Create necessary directories
    dirs = ['data', 'logs', 'config']
    for dir_name in dirs:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✓ Created directory: {dir_name}/")
    
    # Check for .env file
    env_file = project_root / '.env'
    if not env_file.exists():
        example_file = project_root / '.env.example'
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✓ Created .env file from template")
            print("  → Please edit .env with your Slack credentials")
        else:
            print("✗ .env.example not found")
    else:
        print("✓ .env file already exists")
    
    # Initialize database
    try:
        sys.path.insert(0, str(project_root))
        from src.database import DatabaseManager
        
        db_path = project_root / 'data' / 'queue.db'
        db = DatabaseManager(str(db_path))
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        sys.exit(1)
    
    print("\nSetup complete! Next steps:")
    print("1. Edit .env file with your Slack Bot Token")
    print("2. Run: ./setup.sh")
    print("3. Add the bot to your Slack channels")

if __name__ == "__main__":
    main()
