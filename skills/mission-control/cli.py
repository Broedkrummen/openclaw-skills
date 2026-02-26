#!/usr/bin/env python3
"""Mission Control CLI - Command-line interface for mission control operations."""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config


def get_db_connection():
    """Get a database connection using the config path."""
    db_path = os.path.expanduser('~/.openclaw/mission/mission.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_start(args):
    """Start the dashboard (launches Flask app)."""
    import subprocess
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
    if os.path.exists(app_path):
        print("Starting Mission Control dashboard...")
        subprocess.run(['python3', app_path])
    else:
        # Try to find the dashboard another way
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(skill_dir):
            if f.endswith('.py') and 'app' in f.lower():
                print(f"Starting {f}...")
                subprocess.run(['python3', os.path.join(skill_dir, f)])
                return
        print("No dashboard app found in skill directory.")


def cmd_task_add(args):
    """Add a new task."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO tasks (title, agent_id, priority, status, created_at)
            VALUES (?, ?, ?, 'pending', datetime('now'))
        ''', (args.title, args.agent, args.priority))
        conn.commit()
        task_id = cursor.lastrowid
        print(f"Task created: #{task_id} - {args.title} (agent: {args.agent}, priority: {args.priority})")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        print("Make sure the database exists and has a 'tasks' table.")
    finally:
        conn.close()


def cmd_task_list(args):
    """List tasks, optionally filtered by status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if args.status:
            cursor.execute('SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC', (args.status,))
        else:
            cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        
        tasks = cursor.fetchall()
        if not tasks:
            print("No tasks found.")
            return
        
        print(f"{'ID':<5} {'Title':<30} {'Agent':<10} {'Priority':<10} {'Status':<12}")
        print("-" * 70)
        for task in tasks:
            print(f"{task['id']:<5} {task['title'][:28]:<30} {str(task['agent_id']):<10} {task['priority']:<10} {task['status']:<12}")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()


def cmd_msg_send(args):
    """Send a message between agents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO messages (from_agent, to_agent, content, created_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (args.msg_from, args.msg_to, args.content))
        conn.commit()
        msg_id = cursor.lastrowid
        print(f"Message sent: #{msg_id} from {args.msg_from} to {args.msg_to}")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        print("Make sure the database exists and has a 'messages' table.")
    finally:
        conn.close()


def cmd_file_upload(args):
    """Upload a file to an agent."""
    path = Path(args.path)
    if not path.exists():
        print(f"Error: File not found: {args.path}")
        return
    
    # Store file reference in database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO files (filename, path, agent_id, uploaded_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (path.name, str(path.resolve()), args.file_to))
        conn.commit()
        file_id = cursor.lastrowid
        print(f"File uploaded: #{file_id} ({path.name}) -> agent {args.file_to}")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        print("Make sure the database exists and has a 'files' table.")
    finally:
        conn.close()


def cmd_status(args):
    """Show status of all agents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Try to get agent statuses
        cursor.execute('SELECT * FROM agents ORDER BY name')
        agents = cursor.fetchall()
        
        if not agents:
            print("No agents registered.")
            return
        
        print(f"{'Agent ID':<15} {'Name':<20} {'Status':<15} {'Last Seen':<20}")
        print("-" * 70)
        for agent in agents:
            print(f"{agent['id']:<15} {agent.get('name', 'N/A'):<20} {agent.get('status', 'unknown'):<15} {agent.get('last_seen', 'Never'):<20}")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
        print("Make sure the database exists and has an 'agents' table.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Mission Control CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # start command
    start_parser = subparsers.add_parser('start', help='Start the dashboard')
    
    # task add command
    task_add_parser = subparsers.add_parser('task', help='Task operations')
    task_subparsers = task_add_parser.add_subparsers(dest='task_command', help='Task subcommands')
    
    add_parser = task_subparsers.add_parser('add', help='Add a new task')
    add_parser.add_argument('title', help='Task title')
    add_parser.add_argument('--agent', required=True, help='Agent ID to assign task')
    add_parser.add_argument('--priority', required=True, choices=['low', 'medium', 'high', 'critical'], help='Task priority')
    
    list_parser = task_subparsers.add_parser('list', help='List tasks')
    list_parser.add_argument('--status', help='Filter by status (pending, in_progress, completed)')
    
    # msg send command
    msg_parser = subparsers.add_parser('msg', help='Message operations')
    msg_subparsers = msg_parser.add_subparsers(dest='msg_command', help='Message subcommands')
    
    send_parser = msg_subparsers.add_parser('send', help='Send a message')
    send_parser.add_argument('--from', dest='msg_from', required=True, help='Sender agent ID')
    send_parser.add_argument('--to', dest='msg_to', required=True, help='Recipient agent ID')
    send_parser.add_argument('content', help='Message content')
    
    # file upload command
    file_parser = subparsers.add_parser('file', help='File operations')
    file_subparsers = file_parser.add_subparsers(dest='file_command', help='File subcommands')
    
    upload_parser = file_subparsers.add_parser('upload', help='Upload a file to an agent')
    upload_parser.add_argument('path', help='Path to file')
    upload_parser.add_argument('--to', dest='file_to', required=True, help='Target agent ID')
    
    # status command
    status_parser = subparsers.add_parser('status', help='Show all agent statuses')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to appropriate command handler
    if args.command == 'start':
        cmd_start(args)
    elif args.command == 'task':
        if args.task_command == 'add':
            cmd_task_add(args)
        elif args.task_command == 'list':
            cmd_task_list(args)
        else:
            task_add_parser.print_help()
    elif args.command == 'msg':
        if args.msg_command == 'send':
            cmd_msg_send(args)
        else:
            msg_parser.print_help()
    elif args.command == 'file':
        if args.file_command == 'upload':
            cmd_file_upload(args)
        else:
            file_parser.print_help()
    elif args.command == 'status':
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
