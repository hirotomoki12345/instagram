from flask import Flask, render_template, request, redirect, url_for, session
from instagrapi import Client
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)  # セッションの暗号化に使用されるキー
app.permanent_session_lifetime = timedelta(days=30)  # セッションの有効期限を30日に設定

# Instagramクライアントの初期化
ig_client = Client()

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
            # セッションにユーザー情報を保存
            session['username'] = username
            session['password'] = password
            session.permanent = True  # セッションを永続的にする
            return redirect(url_for('dashboard'))
        except Exception as e:
            return f"Login failed: {e}"

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

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

    try:
        # DMを取得する
        inbox = ig_client.direct_threads()
    except Exception as e:
        return f"Failed to fetch DMs: {e}"

    return render_template('dm.html', inbox=inbox)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('password', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
