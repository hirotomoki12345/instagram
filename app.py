from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from instagrapi import Client
import os
from datetime import timedelta
from collections import defaultdict
from time import time

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=30)

# Instagramクライアントの初期化
ig_client = Client()

# リクエスト制限用の変数
request_counts = defaultdict(lambda: {'count': 0, 'last_reset': time()})

MAX_REQUESTS = 100
REQUEST_RESET_TIME = 3600  # 1時間

def check_rate_limit(username):
    now = time()
    user_data = request_counts[username]
    
    if now - user_data['last_reset'] > REQUEST_RESET_TIME:
        user_data['count'] = 0
        user_data['last_reset'] = now
    
    if user_data['count'] >= MAX_REQUESTS:
        return False
    
    user_data['count'] += 1
    return True

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            ig_client.login(username, password)
            session['username'] = username
            session['password'] = password
            session.permanent = True
            return redirect(url_for('dashboard'))
        except Exception as e:
            return f"Login failed: {e}"

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    if not check_rate_limit(session['username']):
        return "Rate limit exceeded. Please try again later.", 429

    try:
        user_id = ig_client.user_id_from_username(session['username'])
        user_info = ig_client.user_info(user_id)
    except Exception as e:
        return f"Failed to fetch user info: {e}"

    return render_template('dashboard.html', user_info=user_info)

@app.route('/dm')
def dm():
    if 'username' not in session:
        return redirect(url_for('login'))

    if not check_rate_limit(session['username']):
        return "Rate limit exceeded. Please try again later.", 429

    try:
        inbox = ig_client.direct_threads()
    except Exception as e:
        return f"Failed to fetch DMs: {e}"

    return render_template('dm.html', inbox=inbox)

@app.route('/fetch_dms')
def fetch_dms():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if not check_rate_limit(session['username']):
        return "Rate limit exceeded. Please try again later.", 429

    try:
        inbox = ig_client.direct_threads()
        response = []
        for thread in inbox:
            messages = [msg.dict() for msg in ig_client.direct_messages(thread.id)]
            response.append({
                'thread_title': thread.thread_title,
                'id': thread.id,
                'messages': messages
            })
        return jsonify({'inbox': response})
    except Exception as e:
        return f"Failed to fetch DMs: {e}"

@app.route('/send_dm/<int:thread_id>', methods=['POST'])
def send_dm(thread_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    if not check_rate_limit(session['username']):
        return "Rate limit exceeded. Please try again later.", 429

    message = request.form['message']
    try:
        ig_client.direct_answer(thread_id, message)
        return redirect(url_for('dm'))
    except Exception as e:
        return f"Failed to send DM: {e}"

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('password', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5420)
