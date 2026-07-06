from flask import Flask, request, redirect, render_template
import requests
import os
import re
import sqlite3
import random
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')

# ===== AYARLAR =====
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
BOT_TOKEN = os.getenv('BOT_TOKEN')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/callback')
PORT = int(os.getenv('PORT', 5000))

# ===== DISCORD API =====
DISCORD_AUTH_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL = "https://discord.com/api/v10"

# ============================================================
# VERİTABANI
# ============================================================

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY,
                  username TEXT,
                  access_token TEXT,
                  refresh_token TEXT,
                  created_at TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_user(user_id, username, access_token, refresh_token):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users 
                 (user_id, username, access_token, refresh_token, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, username, access_token, refresh_token, datetime.now()))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username, access_token FROM users')
    users = c.fetchall()
    conn.close()
    return users

def count_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    count = c.fetchone()[0]
    conn.close()
    return count

def delete_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def delete_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM users')
    conn.commit()
    conn.close()

init_db()

# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def extract_invite_code(url):
    match = re.search(r'discord(?:\.com\/invite|\.gg)\/([a-zA-Z0-9\-_]+)', url)
    if match:
        return match.group(1)
    return None

def get_guild_id_from_invite(invite_code):
    url = f"{DISCORD_API_URL}/invites/{invite_code}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('guild', {}).get('id'), data.get('guild', {}).get('name')
    return None, None

def add_user_to_guild(guild_id, user_id, access_token):
    headers = {
        'Authorization': f'Bot {BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {'access_token': access_token}
    url = f"{DISCORD_API_URL}/guilds/{guild_id}/members/{user_id}"
    try:
        response = requests.put(url, headers=headers, json=data)
        return response.status_code in [200, 201, 204]
    except:
        return False

def bot_leave_guild(guild_id):
    headers = {'Authorization': f'Bot {BOT_TOKEN}'}
    url = f"{DISCORD_API_URL}/users/@me/guilds/{guild_id}"
    response = requests.delete(url, headers=headers)
    return response.status_code == 204

# ============================================================
# ROTALAR
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify guilds.join'
    }
    auth_url = f"{DISCORD_AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return render_template('error.html', 
            hata="Yetkilendirme kodu alınamadı!",
            detay="Lütfen tekrar deneyin.")

    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    token_response = requests.post(DISCORD_TOKEN_URL, data=token_data, headers=headers)
    
    if token_response.status_code != 200:
        return render_template('error.html',
            hata="Token alınamadı!",
            detay=f"Hata kodu: {token_response.status_code}")

    token_json = token_response.json()
    access_token = token_json.get('access_token')
    refresh_token = token_json.get('refresh_token')
    
    if not access_token:
        return render_template('error.html',
            hata="Access token bulunamadı!",
            detay="Lütfen tekrar deneyin.")

    user_headers = {'Authorization': f'Bearer {access_token}'}
    user_response = requests.get(f"{DISCORD_API_URL}/users/@me", headers=user_headers)
    
    if user_response.status_code != 200:
        return render_template('error.html',
            hata="Kullanıcı bilgileri alınamadı!",
            detay=f"Hata kodu: {user_response.status_code}")

    user_data = user_response.json()
    user_id = user_data.get('id')
    username = user_data.get('username')
    
    if not user_id:
        return render_template('error.html',
            hata="Kullanıcı ID bulunamadı!",
            detay="Lütfen tekrar deneyin.")

    save_user(user_id, username, access_token, refresh_token)

    return render_template('success.html', 
        username=username,
        user_id=user_id)

@app.route('/admin')
def admin():
    users = get_all_users()
    toplam = count_users()
    return render_template('admin.html', users=users, toplam=toplam)

@app.route('/admin/delete/<user_id>')
def admin_delete_user(user_id):
    delete_user(user_id)
    return redirect('/admin')

@app.route('/admin/delete-selected', methods=['POST'])
def admin_delete_selected():
    user_ids = request.form.getlist('selected_users')
    if user_ids:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        for user_id in user_ids:
            c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    return redirect('/admin')

@app.route('/admin/join', methods=['POST'])
def admin_join():
    guild_url = request.form.get('guild_url', '').strip()
    count_str = request.form.get('count', '').strip()
    
    if not guild_url:
        return render_template('error.html',
            hata="Sunucu URL'si gerekli!",
            detay="Lütfen geçerli bir davet linki girin.")

    invite_code = extract_invite_code(guild_url)
    if not invite_code:
        return render_template('error.html',
            hata="Geçersiz sunucu URL'si!",
            detay="Örnek: discord.gg/abcd1234")

    guild_id, guild_name = get_guild_id_from_invite(invite_code)
    if not guild_id:
        return render_template('error.html',
            hata="Sunucu bulunamadı!",
            detay="Davet linki geçersiz veya süresi dolmuş.")

    total_users = count_users()
    if total_users == 0:
        return render_template('error.html',
            hata="Hiç üye yok!",
            detay="Önce kullanıcıların yetki vermesi gerekir.")

    try:
        selected_count = int(count_str)
        if selected_count < 1:
            selected_count = 1
        if selected_count > total_users:
            selected_count = total_users
    except:
        selected_count = total_users

    all_users = get_all_users()
    if selected_count >= len(all_users):
        selected_users = all_users
    else:
        selected_users = random.sample(all_users, selected_count)

    def process_join():
        success = 0
        failed = 0
        
        for user_id, username, access_token in selected_users:
            try:
                if add_user_to_guild(guild_id, user_id, access_token):
                    success += 1
                else:
                    failed += 1
            except:
                failed += 1
            time.sleep(1.5)
        
        time.sleep(300)
        bot_leave_guild(guild_id)

    thread = threading.Thread(target=process_join)
    thread.start()

    return render_template('processing.html',
        guild_name=guild_name,
        total_users=len(selected_users),
        toplam_kullanici=total_users)

@app.route('/admin/clear')
def clear_users():
    delete_all_users()
    return redirect('/admin')

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 ÜYE EKLEME SİSTEMİ")
    print("=" * 50)
    print(f"📍 Site: http://localhost:{PORT}")
    print(f"🔑 Admin: http://localhost:{PORT}/admin")
    print("=" * 50)
    app.run(debug=True, port=PORT)