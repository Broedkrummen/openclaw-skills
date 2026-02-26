import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Database initialization
def init_db():
    """Initialize SQLite database with tables"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    c = conn.cursor()
    
    # Agents table
    c.execute('''CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        agent_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (agent_id) REFERENCES agents (id)
    )''')
    
    # Messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        content TEXT NOT NULL,
        channel TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Files table
    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        size INTEGER,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# HTML Templates (inline)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Mission Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #00d4ff; }
        .nav { margin-bottom: 20px; }
        .nav a { color: #00d4ff; margin-right: 20px; text-decoration: none; }
        .card { background: #16213e; padding: 20px; margin: 10px 0; border-radius: 8px; }
        .status { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; }
        .status.active { background: #00d4ff; color: #000; }
        .status.pending { background: #f39c12; color: #000; }
        .status.completed { background: #27ae60; color: #fff; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #333; }
        input, textarea { width: 100%; padding: 10px; margin: 5px 0; background: #0f3460; border: 1px solid #333; color: #eee; }
        button { padding: 10px 20px; background: #00d4ff; border: none; color: #000; cursor: pointer; }
        button:hover { background: #00a3cc; }
        .search-box { margin: 20px 0; }
    </style>
</head>
<body>
    <h1>🚀 Mission Control</h1>
    <div class="nav">
        <a href="#agents">Agents</a>
        <a href="#tasks">Tasks</a>
        <a href="#messages">Messages</a>
        <a href="#memory">Memory Search</a>
    </div>
    
    <div class="card" id="agents">
        <h2>🤖 Agents</h2>
        <div id="agents-list">Loading...</div>
    </div>
    
    <div class="card" id="tasks">
        <h2>📋 Tasks</h2>
        <form method="POST" action="/api/tasks">
            <input type="text" name="title" placeholder="Task title" required>
            <textarea name="description" placeholder="Description"></textarea>
            <button type="submit">Add Task</button>
        </form>
        <div id="tasks-list">Loading...</div>
    </div>
    
    <div class="card" id="messages">
        <h2>💬 Messages</h2>
        <form method="POST" action="/api/messages">
            <input type="text" name="sender" placeholder="Sender" required>
            <textarea name="content" placeholder="Message content" required></textarea>
            <input type="text" name="channel" placeholder="Channel (optional)">
            <button type="submit">Send Message</button>
        </form>
        <div id="messages-list">Loading...</div>
    </div>
    
    <div class="card" id="memory">
        <h2>🧠 Memory Search</h2>
        <div class="search-box">
            <form method="GET" action="/api/memory/search">
                <input type="text" name="q" placeholder="Search memory..." value="{{ request.args.get('q', '') }}">
                <button type="submit">Search</button>
            </form>
        </div>
        <div id="memory-results">Loading...</div>
    </div>
    
    <script>
        async function loadData() {
            // Load agents
            const agentsRes = await fetch('/api/agents');
            const agents = await agentsRes.json();
            document.getElementById('agents-list').innerHTML = agents.length ? 
                '<table><tr><th>ID</th><th>Name</th><th>Status</th><th>Created</th></tr>' + 
                agents.map(a => `<tr><td>${a.id}</td><td>${a.name}</td><td><span class="status ${a.status}">${a.status}</span></td><td>${a.created_at}</td></tr>`).join('') + 
                '</table>' : '<p>No agents found</p>';
            
            // Load tasks
            const tasksRes = await fetch('/api/tasks');
            const tasks = await tasksRes.json();
            document.getElementById('tasks-list').innerHTML = tasks.length ?
                '<table><tr><th>ID</th><th>Title</th><th>Status</th><th>Created</th></tr>' +
                tasks.map(t => `<tr><td>${t.id}</td><td>${t.title}</td><td><span class="status ${t.status}">${t.status}</span></td><td>${t.created_at}</td></tr>`).join('') +
                '</table>' : '<p>No tasks found</p>';
            
            // Load messages
            const msgsRes = await fetch('/api/messages');
            const msgs = await msgsRes.json();
            document.getElementById('messages-list').innerHTML = msgs.length ?
                '<table><tr><th>Sender</th><th>Content</th><th>Channel</th><th>Time</th></tr>' +
                msgs.map(m => `<tr><td>${m.sender}</td><td>${m.content}</td><td>${m.channel || '-'}</td><td>${m.created_at}</td></tr>`).join('') +
                '</table>' : '<p>No messages found</p>';
            
            // Load memory search if query exists
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('q')) {
                const memRes = await fetch(`/api/memory/search?q=${encodeURIComponent(urlParams.get('q'))}`);
                const memData = await memRes.json();
                document.getElementById('memory-results').innerHTML = memData.results && memData.results.length ?
                    memData.results.map(r => `<p><strong>${r.file}</strong>: ${r.preview}...</p>`).join('') :
                    '<p>No results found</p>';
            } else {
                document.getElementById('memory-results').innerHTML = '<p>Enter a search term above</p>';
            }
        }
        loadData();
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    """Dashboard homepage"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/agents', methods=['GET'])
def list_agents():
    """List all agents"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM agents ORDER BY created_at DESC')
    agents = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(agents)

@app.route('/api/agents', methods=['POST'])
def create_agent():
    """Create a new agent"""
    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    c = conn.cursor()
    c.execute('INSERT INTO agents (name, status) VALUES (?, ?)', 
              (data.get('name', 'Unknown'), data.get('status', 'active')))
    conn.commit()
    agent_id = c.lastrowid
    conn.close()
    return jsonify({'id': agent_id, 'message': 'Agent created'}), 201

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """List all tasks"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    tasks = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.form if request.form else request.get_json()
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    c = conn.cursor()
    c.execute('INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)',
              (data.get('title'), data.get('description', ''), data.get('status', 'pending')))
    conn.commit()
    task_id = c.lastrowid
    conn.close()
    return jsonify({'id': task_id, 'message': 'Task created'}), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    data = request.get_json()
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    c = conn.cursor()
    c.execute('UPDATE tasks SET title=?, description=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
              (data.get('title'), data.get('description'), data.get('status'), task_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Task updated'})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Task deleted'})

@app.route('/api/messages', methods=['GET'])
def list_messages():
    """List all messages"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM messages ORDER BY created_at DESC LIMIT 100')
    messages = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(messages)

@app.route('/api/messages', methods=['POST'])
def create_message():
    """Create a new message"""
    data = request.form if request.form else request.get_json()
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    c = conn.cursor()
    c.execute('INSERT INTO messages (sender, content, channel) VALUES (?, ?, ?)',
              (data.get('sender'), data.get('content'), data.get('channel')))
    conn.commit()
    msg_id = c.lastrowid
    conn.close()
    return jsonify({'id': msg_id, 'message': 'Message sent'}), 201

@app.route('/api/memory/search', methods=['GET'])
def search_memory():
    """Search memory files"""
    query = request.args.get('q', '').lower()
    memory_dir = app.config['MEMORY_DIR']
    results = []
    
    if os.path.exists(memory_dir):
        for filename in os.listdir(memory_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(memory_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read().lower()
                        if query in content:
                            # Find context around the match
                            idx = content.find(query)
                            start = max(0, idx - 50)
                            end = min(len(content), idx + 100)
                            preview = content[start:end].replace('\n', ' ')
                            results.append({
                                'file': filename,
                                'preview': preview,
                                'path': filepath
                            })
                except Exception as e:
                    pass
    
    return jsonify({'query': query, 'results': results})

@app.route('/api/files', methods=['GET'])
def list_files():
    """List all files"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM files ORDER BY uploaded_at DESC')
    files = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(files)

@app.route('/api/files', methods=['POST'])
def upload_file():
    """Upload a file (metadata only)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    filepath = os.path.join('/tmp', file.filename)
    file.save(filepath)
    
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    c = conn.cursor()
    c.execute('INSERT INTO files (filename, filepath, size) VALUES (?, ?, ?)',
              (file.filename, filepath, os.path.getsize(filepath)))
    conn.commit()
    file_id = c.lastrowid
    conn.close()
    
    return jsonify({'id': file_id, 'message': 'File uploaded'}), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
