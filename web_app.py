from flask import Flask, render_template_string, request, session, redirect, url_for, flash, make_response
import sqlite3
import random
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import math

app = Flask(__name__)
app.secret_key = 'sab_kamao_secret_key_123'

def init_db():
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (phone TEXT PRIMARY KEY, balance REAL DEFAULT 0.0, profile_pic TEXT DEFAULT '', referral_code TEXT UNIQUE, total_withdrawn REAL DEFAULT 0.0, password TEXT, lat REAL DEFAULT 28.4744, lng REAL DEFAULT 77.5040, location_name TEXT DEFAULT 'Greater Noida')''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, amount REAL, title TEXT, timestamp DATETIME DEFAULT (datetime('now', 'localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, provider_phone TEXT, title TEXT, payment_method TEXT, otp TEXT, status TEXT DEFAULT 'OPEN', worker_phone TEXT DEFAULT '', start_time TEXT DEFAULT '', completion_otp TEXT DEFAULT '', finish_time TEXT DEFAULT '', lat REAL DEFAULT 28.4744, lng REAL DEFAULT 77.5040, location_name TEXT DEFAULT 'Greater Noida', amount_earned REAL DEFAULT 0.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_phone TEXT, referred_phone TEXT, status TEXT DEFAULT 'REGISTERED', milestone_paid INTEGER DEFAULT 0, timestamp DATETIME DEFAULT (datetime('now', 'localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS reels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uploader_phone TEXT, caption TEXT, video_filename TEXT, likes INTEGER DEFAULT 0, timestamp DATETIME DEFAULT (datetime('now', 'localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS reel_comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, reel_id INTEGER, commenter_phone TEXT, comment_text TEXT, timestamp DATETIME DEFAULT (datetime('now', 'localtime')))''')
    
    for col, c_type in [("total_withdrawn", "REAL DEFAULT 0.0"), ("referral_code", "TEXT"), ("password", "TEXT"), ("lat", "REAL DEFAULT 28.4744"), ("lng", "REAL DEFAULT 77.5040"), ("location_name", "TEXT DEFAULT 'Greater Noida'")]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {c_type}")
        except:
            pass
            
    for col, c_type in [("worker_phone", "TEXT DEFAULT ''"), ("start_time", "TEXT DEFAULT ''"), ("completion_otp", "TEXT DEFAULT ''"), ("finish_time", "TEXT DEFAULT ''"), ("lat", "REAL DEFAULT 28.4744"), ("lng", "REAL DEFAULT 77.5040"), ("location_name", "TEXT DEFAULT 'Greater Noida'"), ("amount_earned", "REAL DEFAULT 0.0")]:
        try:
            c.execute(f"ALTER TABLE tasks ADD COLUMN {col} {c_type}")
        except:
            pass

    conn.commit()
    conn.close()

with app.app_context():
    init_db()

UPLOAD_FOLDER = 'static/uploads'
VIDEO_FOLDER = 'static/videos'
ALLOWED_IMG_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VID_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['VIDEO_FOLDER'] = VIDEO_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(VIDEO_FOLDER):
    os.makedirs(VIDEO_FOLDER)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

SENDER_EMAIL = "rp619653@gmail.com"
SENDER_PASSWORD = "sybt bsag faxj bqip"  
ADMIN_EMAIL = "rp619653@gmail.com"

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def send_withdrawal_email(phone_or_email, amount, withdraw_type, details):
    try:
        subject = f"🚨 New Withdrawal Alert: ₹{amount} from {phone_or_email}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Sab Kamao - New Withdrawal Request</h2>
            <p><b>User:</b> {phone_or_email}</p>
            <p><b>Amount:</b> ₹{amount}</p>
            <p><b>Withdrawal Method:</b> {withdraw_type.upper()}</p>
            <p><b>Payment Details:</b> {details}</p>
        </body>
        </html>
        """
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=5)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Withdrawal Email Error:", e)
        return False

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sab Kamao - Login / Signup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #ffffff;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; margin: 0; padding: 20px;
        }
        .card {
            background: #ffffff; padding: 30px 25px; border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08); width: 100%; max-width: 360px;
            text-align: center; border: 1px solid #eaeaea;
        }
        .logo-box { width: 100px; height: 100px; margin: 0 auto 10px auto; }
        h2 { color: #1c4d25; margin: 0 0 4px 0; font-size: 28px; font-weight: 800; }
        p.subtitle { color: #27ae60; margin: 0 0 22px 0; font-size: 14px; font-weight: 600; }
        input[type=email], input[type=password], input[type=text], input[type=file], input[type=submit] {
            width: 100%; padding: 12px; margin: 8px 0; border-radius: 10px; font-size: 14px;
        }
        input[type=email], input[type=password], input[type=text] {
            border: 1.5px solid #27ae60; text-align: center; font-weight: bold; outline: none; background: #fdfdfd;
        }
        input[type=submit] { background: #1c4d25; color: white; border: none; font-weight: bold; cursor: pointer; transition: 0.3s; }
        input[type=submit]:hover { background: #27ae60; }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo-box">
            <svg viewBox="0 0 200 200" width="100%" height="100%">
                <path d="M 100 20 A 80 80 0 1 1 20 100" fill="none" stroke="#1c4d25" stroke-width="14" stroke-linecap="round"/>
                <polygon points="100,8 115,25 90,30" fill="#1c4d25"/>
                <polygon points="12,100 25,85 30,110" fill="#1c4d25"/>
                <rect x="60" y="55" width="80" height="55" rx="5" fill="#f39c12"/>
                <rect x="55" y="45" width="90" height="15" rx="3" fill="#e67e22"/>
                <rect x="92" y="45" width="16" height="65" fill="#1c4d25"/>
                <text x="75" y="90" font-family="Arial" font-size="26" font-weight="bold" fill="#1c4d25">₹</text>
                <path d="M 45 130 C 60 110, 90 115, 110 120 C 130 125, 155 110, 150 135 C 140 155, 100 160, 65 150 Z" fill="#1c4d25"/>
            </svg>
        </div>
        <h2>Sab Kamao</h2>
        <p class="subtitle">Local Work. Simple Earnings.</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div style="background: #e1f5fe; color: #01579b; padding: 12px; border-radius: 8px; margin: 10px 0; font-weight: bold; font-size: 14px; border: 1px solid #b3e5fc;">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if msg %}
            <p style="color:#e74c3c; font-weight:bold; font-size:14px;">{{ msg }}</p>
        {% endif %}

        <form method="POST" enctype="multipart/form-data">
            <input type="email" name="email" placeholder="Enter Valid Gmail Address" required>
            <input type="password" name="password" placeholder="Enter Account Password" required>
            <input type="text" name="ref_code_input" placeholder="Referral Code (Optional)" value="{{ request.args.get('ref', '') }}">
            <label style="font-size:12px; color:#555; display:block; text-align:left; margin-top:5px;">Profile Picture (Optional):</label>
            <input type="file" name="profile_pic" accept="image/*">
            <input type="submit" value="Login / Signup">
        </form>
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sab Kamao</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #eef2f5; margin: 0; padding-bottom: 90px; }
        .header { background: #1c4d25; color: white; padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; }
        .header-title { font-weight: bold; font-size: 18px; }
        .header-sub { font-size: 12px; font-weight: normal; margin-top: 2px; }
        .menu-btn { font-size: 22px; cursor: pointer; color: white; padding: 5px; }
        .container { padding: 15px; }
        .card { background: white; padding: 18px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); margin-bottom: 15px; }
        input, select, textarea { width: 100%; padding: 11px; margin: 8px 0; border: 1px solid #ccc; border-radius: 8px; font-size: 15px; }
        input[type=submit], button { background: #27ae60; color: white; border: none; font-weight: bold; cursor: pointer; padding: 12px; border-radius: 8px; width: 100%; font-size: 16px; margin-top: 5px; }
        .timer { font-size: 32px; font-weight: bold; color: #e67e22; text-align: center; margin: 10px 0; }
        .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: #ffffff; display: flex; justify-content: space-around; align-items: center; padding: 8px 0; border-top: 1px solid #e0e0e0; z-index: 99999; box-shadow: 0 -4px 15px rgba(0,0,0,0.08); }
        .nav-item { text-decoration: none; text-align: center; flex: 1; color: #333; cursor: pointer; }
        .nav-icon { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 3px auto; }
        .red-grad { background: linear-gradient(135deg, #FF512F, #DD2476); box-shadow: 0 3px 8px rgba(221,36,118,0.3); }
        .green-grad { background: linear-gradient(135deg, #11998e, #38ef7d); box-shadow: 0 3px 8px rgba(56,239,125,0.3); }
        .blue-grad { background: linear-gradient(135deg, #2193b0, #6dd5ed); box-shadow: 0 3px 8px rgba(33,147,176,0.3); }
        .purple-grad { background: linear-gradient(135deg, #8E2DE2, #4A00E0); box-shadow: 0 3px 8px rgba(142,45,226,0.3); }
        .pink-grad { background: linear-gradient(135deg, #f12711, #f5af19); box-shadow: 0 3px 8px rgba(245,175,25,0.3); }
        .profile-avatar {
            width: 80px; height: 80px; border-radius: 50%; object-fit: cover;
            border: 3px solid #27ae60; margin: 0 auto 10px auto; display: flex;
            align-items: center; justify-content: center; font-size: 40px; background: #e8f5e9;
        }
        .task-avatar {
            width: 45px; height: 45px; border-radius: 50%; object-fit: cover;
            border: 2px solid #27ae60; display: inline-block; vertical-align: middle; margin-right: 10px; background: #e8f5e9; text-align:center; line-height:45px; font-size:20px;
        }
        .reel-card { background: #000; border-radius: 12px; overflow: hidden; margin-bottom: 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.15); color: #fff; }
        .reel-header { padding: 12px; display: flex; align-items: center; background: rgba(0,0,0,0.7); justify-content: space-between; }
        .reel-avatar { width: 38px; height: 38px; border-radius: 50%; object-fit: cover; border: 2px solid #27ae60; margin-right: 10px; background: #333; text-align:center; line-height:38px; font-size:16px; }
        .reel-video { width: 100%; max-height: 400px; background: #111; display: block; object-fit: contain; }
        .reel-footer { padding: 12px; background: rgba(0,0,0,0.8); }
        .refer-box { background: #f9fdfa; border: 2px dashed #27ae60; padding: 15px; border-radius: 10px; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="header-title">Sab Kamao - ₹75/Hour</div>
            <div class="header-sub">Wallet: <b>₹{{ balance }}</b> | User: <b>{{ phone }}</b></div>
        </div>
        <div class="menu-btn" onclick="openProfileModal()">
            <i class="fa-solid fa-bars"></i>
        </div>
    </div>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div style="background: #e1f5fe; color: #01579b; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; font-size: 14px; border: 1px solid #b3e5fc;">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if msg %}
            <div class="card" style="color:#1c4d25; font-weight:bold; text-align:center;">{{ msg|safe }}</div>
        {% endif %}

        {% if page == 'home' %}
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0; color:#1c4d25;">💼 Available Tasks (3 KM Range)</h3>
                    <a href="/" style="background:#27ae60; color:#fff; padding:6px 10px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:bold;"><i class="fa-solid fa-sync"></i> Refresh</a>
                </div>
                <p style="font-size:12px; color:#555; margin-bottom:15px;">📍 Aapki Location: <b>{{ user_loc_name }}</b></p>
                
                {% if active_task_info %}
                    <div style="background:#fff3e0; border:1px solid #ffe0b2; padding:12px; border-radius:8px; margin-bottom:15px; text-align:center;">
                        <p style="margin:0; color:#d84315; font-size:13px; font-weight:bold;">⚠️ Aapka ek task pehle se active/pending hai! Naya task lene ke liye pehle apna current task complete karein.</p>
                    </div>
                {% endif %}

                {% if not open_tasks %}
                    <p style="color:#888;">Aapke 3 km range mein abhi koi open task nahi hai.</p>
                {% endif %}
                
                {% for task in open_tasks %}
                    <div style="border-bottom:1px solid #eee; padding:12px 0; display:flex; align-items:center;">
                        <div>
                            {% if task[7] %}
                                <img src="/static/uploads/{{ task[7] }}" class="task-avatar">
                            {% else %}
                                <div class="task-avatar">👤</div>
                            {% endif %}
                        </div>
                        <div style="flex:1;">
                            <b>{{ task[1] }}</b><br>
                            <small style="color:#555;">Owner: <b>{{ task[6] }}</b> | Mode: <b>{{ task[2] }}</b></small><br>
                            <small style="color:#e67e22;">📍 <b>{{ task[8] }}</b> ({{ "%.2f"|format(task[9]) }} KM away)</small>
                            
                            {% if active_task_info %}
                                <button disabled style="background:#ccc; cursor:not-allowed; padding:8px; font-size:13px; margin-top:8px;">Task Locked (Complete Previous First)</button>
                            {% else %}
                                <form method="POST" style="margin-top:8px;" onsubmit="initTaskStart('{{ task[0] }}')">
                                    <input type="hidden" name="action" value="verify_task_otp">
                                    <input type="hidden" name="task_id" value="{{ task[0] }}">
                                    <input type="number" name="otp" placeholder="Enter OTP from Task Owner" required style="padding:8px; font-size:13px;">
                                    <input type="submit" value="Start Work with OTP" style="padding:8px; font-size:13px;">
                                </form>
                            {% endif %}
                        </div>
                    </div>
                {% endfor %}
            </div>

            {% if active_task_info %}
                <div class="card">
                    <h3 style="text-align:center; color:#1c4d25; margin-top:0;">⏱️ Live Work Counter</h3>
                    <p style="text-align:center; margin:0; color:#555;">Active Task: <b>{{ active_task_info[1] }}</b></p>
                    <div class="timer" id="time-display">00:00:00</div>
                    <div style="text-align:center; font-size:20px; color:#27ae60; font-weight:bold;" id="earning-display">Earned: ₹0.00</div>
                    
                    {% if not active_task_info[3] %}
                        <form method="POST" style="margin-top:15px;" onsubmit="clearTaskTimer('{{ active_task_info[0] }}')">
                            <input type="hidden" name="action" value="worker_finish_work">
                            <input type="hidden" name="task_id" value="{{ active_task_info[0] }}">
                            <input type="hidden" name="elapsed_seconds" id="elapsed_seconds" value="0">
                            <input type="submit" value="Finish Work & Get Owner OTP" style="background:#e67e22;">
                        </form>
                    {% else %}
                        <div style="background:#e8f5e9; border:1px solid #27ae60; padding:12px; border-radius:8px; text-align:center; margin-top:15px;">
                            <p style="margin:0 0 5px 0; font-size:13px; color:#2e7d32;"><b>Your Completion OTP:</b></p>
                            <span style="font-size:26px; font-weight:bold; color:#1c4d25;">{{ active_task_info[3] }}</span>
                            <p style="margin:5px 0 0 0; font-size:11px; color:#555;">Ye OTP Kam Dene Wale (Task Owner) ko dein taaki wo final submit karein.</p>
                        </div>
                    {% endif %}
                </div>
            {% endif %}
        {% endif %}

        {% if page == 'kam_do' %}
            <div class="card">
                <h3 style="margin-top:0; color:#1c4d25;">➕ Post a New Task (Kam Do)</h3>
                <div style="background:#f9fdfa; border:1px solid #27ae60; padding:10px; border-radius:8px; margin-bottom:10px; font-size:13px; color:#1c4d25;">
                    📍 Task Location (Aapki Profile Location): <b>{{ user_loc_name }}</b>
                </div>
                <form method="POST">
                    <input type="hidden" name="action" value="create_task">
                    <label style="font-weight:600; font-size:14px;">Task Description:</label>
                    <input type="text" name="title" placeholder="e.g. Dukan par helper ka kaam" required>
                    <label style="font-weight:600; font-size:14px;">Payment Mode:</label>
                    <select name="pay_method" required>
                        <option value="Cash Deposit">Cash Deposit</option>
                        <option value="UPI Transfer">UPI Transfer</option>
                        <option value="Bank Transfer">Bank Transfer</option>
                    </select>
                    <input type="submit" value="Post Task & Generate OTP" style="margin-top:10px;">
                </form>
            </div>

            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0; color:#1c4d25;"><i class="fa-solid fa-list-check"></i> My Posted Tasks & History</h3>
                    <a href="/download_pdf?type=owner" style="background:#3498db; color:#fff; padding:6px 10px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:bold;"><i class="fa-solid fa-download"></i> PDF</a>
                </div>
                {% if not my_tasks %}
                    <p style="color:#888; font-size:14px;">Aapne abhi tak koi task post nahi kiya hai.</p>
                {% else %}
                    {% for t in my_tasks %}
                        <div style="border-bottom:1px solid #eee; padding:12px 0;">
                            <b>{{ t[1] }}</b><br>
                            <small style="color:#555;">Mode: <b>{{ t[2] }}</b> | Start OTP: <b style="color:#e67e22;">{{ t[3] }}</b></small><br>
                            <small style="color:#555;">📍 Location: <b>{{ t[7] }}</b></small><br>
                            <small style="color:#666;">Posted Time: {{ t[5] }}</small><br>
                            <small style="color:#666;">Status: <b>{{ t[4] }}</b></small>
                            {% if t[4] == 'COMPLETED' %}
                                <br><small style="color:#27ae60;">Finished Time: {{ t[6] }}</small>
                            {% endif %}
                            
                            {% if t[4] == 'WAITING_OWNER_APPROVAL' %}
                                <div style="background:#fff3e0; padding:10px; border-radius:8px; margin-top:8px; border:1px solid #ffe0b2;">
                                    <p style="margin:0 0 5px 0; font-size:12px; color:#d84315;"><b>Worker ne kaam khatam kar liya hai. Worker dwara diya gaya Completion OTP yahan dalein:</b></p>
                                    <form method="POST">
                                        <input type="hidden" name="action" value="owner_verify_completion">
                                        <input type="hidden" name="task_id" value="{{ t[0] }}">
                                        <input type="number" name="entered_completion_otp" placeholder="Enter Completion OTP" required style="padding:8px; font-size:13px;">
                                        <input type="submit" value="Final Complete & Close Task" style="background:#27ae60; padding:8px; font-size:13px;">
                                    </form>
                                </div>
                            {% endif %}
                        </div>
                    {% endfor %}
                {% endif %}
            </div>
        {% endif %}

        {% if page == 'reels' %}
            <div class="card">
                <h3 style="margin-top:0; color:#1c4d25;"><i class="fa-solid fa-video"></i> Upload Public Reel</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="upload_reel">
                    <label style="font-weight:600; font-size:14px;">Caption / Title:</label>
                    <input type="text" name="caption" placeholder="Write something about your video..." required>
                    <label style="font-weight:600; font-size:14px; display:block; margin-top:5px;">Select Video File (MP4/MOV):</label>
                    <input type="file" name="reel_video" accept="video/*" required style="font-size:13px;">
                    <input type="submit" value="Upload & Publish Publicly" style="background:#f39c12; margin-top:10px;">
                </form>
            </div>

            <div>
                <h3 style="color:#1c4d25; margin-bottom:12px;"><i class="fa-solid fa-film"></i> Public Reels Feed</h3>
                {% if not all_reels %}
                    <p style="color:#888; text-align:center;">Abhi koi reel upload nahi ki gayi hai. Pehli reel aap upload karein!</p>
                {% else %}
                    {% for reel in all_reels %}
                        <div class="reel-card">
                            <div class="reel-header">
                                <div style="display:flex; align-items:center;">
                                    {% if reel[5] %}
                                        <img src="/static/uploads/{{ reel[5] }}" class="reel-avatar">
                                    {% else %}
                                        <div class="reel-avatar">👤</div>
                                    {% endif %}
                                    <div>
                                        <b style="font-size:14px; color:#fff;">{{ reel[1] }}</b><br>
                                        <small style="color:#aaa; font-size:11px;">{{ reel[4] }}</small>
                                    </div>
                                </div>
                                {% if reel[1] == phone %}
                                    <div>
                                        <button onclick="toggleEditReel('{{ reel[0] }}')" style="background:#3498db; border:none; color:#fff; padding:4px 8px; font-size:11px; border-radius:4px; width:auto; margin-right:4px;">✏️ Edit</button>
                                        <form method="POST" style="display:inline;" onsubmit="return confirm('Kya aap is reel ko delete karna chahte hain?');">
                                            <input type="hidden" name="action" value="delete_reel">
                                            <input type="hidden" name="reel_id" value="{{ reel[0] }}">
                                            <button type="submit" style="background:#e74c3c; border:none; color:#fff; padding:4px 8px; font-size:11px; border-radius:4px; width:auto;">🗑️ Delete</button>
                                        </form>
                                    </div>
                                {% endif %}
                            </div>

                            <!-- Edit Reel Form (Hidden by default) -->
                            {% if reel[1] == phone %}
                                <div id="edit_reel_{{ reel[0] }}" style="display:none; background:#222; padding:10px; border-bottom:1px solid #444;">
                                    <form method="POST">
                                        <input type="hidden" name="action" value="edit_reel">
                                        <input type="hidden" name="reel_id" value="{{ reel[0] }}">
                                        <input type="text" name="new_caption" value="{{ reel[2] }}" required style="background:#333; color:#fff; border:1px solid #555; padding:8px; font-size:13px;">
                                        <input type="submit" value="Update Title" style="background:#27ae60; padding:6px; font-size:12px;">
                                    </form>
                                </div>
                            {% endif %}

                            <video src="/static/videos/{{ reel[3] }}" controls class="reel-video"></video>
                            
                            <div class="reel-footer">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                    <span style="font-size:14px; color:#fff; font-weight:bold; flex:1;">{{ reel[2] }}</span>
                                    <form method="POST" style="margin:0;">
                                        <input type="hidden" name="action" value="like_reel">
                                        <input type="hidden" name="reel_id" value="{{ reel[0] }}">
                                        <button type="submit" style="background:transparent; border:1px solid #e74c3c; color:#e74c3c; padding:4px 10px; font-size:12px; border-radius:20px; width:auto;">
                                            <i class="fa-solid fa-heart"></i> {{ reel[6] }}
                                        </button>
                                    </form>
                                </div>

                                <!-- Comments Section -->
                                <div style="border-top:1px solid #333; padding-top:8px; margin-top:8px;">
                                    <small style="color:#aaa; font-weight:bold;"><i class="fa-solid fa-comments"></i> Comments:</small>
                                    <div style="max-height:100px; overflow-y:auto; margin:5px 0;">
                                        {% set comments = get_reel_comments(reel[0]) %}
                                        {% if not comments %}
                                            <p style="color:#778; font-size:11px; margin:2px 0;">No comments yet. Be the first to comment!</p>
                                        {% else %}
                                            {% for comm in comments %}
                                                <div style="font-size:11px; margin-bottom:4px; background:#1a1a1a; padding:5px; border-radius:4px;">
                                                    <b style="color:#27ae60;">{{ comm[0] }}:</b> <span style="color:#ddd;">{{ comm[1] }}</span>
                                                </div>
                                            {% endfor %}
                                        {% endif %}
                                    </div>
                                    <form method="POST" style="display:flex; gap:5px; margin-top:5px;">
                                        <input type="hidden" name="action" value="add_comment">
                                        <input type="hidden" name="reel_id" value="{{ reel[0] }}">
                                        <input type="text" name="comment_text" placeholder="Write a comment..." required style="background:#222; color:#fff; border:1px solid #444; padding:6px; font-size:12px; margin:0; border-radius:4px; flex:1;">
                                        <button type="submit" style="background:#3498db; padding:6px 12px; font-size:12px; margin:0; border-radius:4px; width:auto;">Post</button>
                                    </form>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% endif %}
            </div>
        {% endif %}

        {% if page == 'refer' %}
            <div class="card">
                <h3 style="margin-top:0; color:#8E2DE2;"><i class="fa-solid fa-gift"></i> Refer & Earn</h3>
                <p style="color:#555; font-size:14px;">Apne doston ko invite karein! Har naye registration par <b>Instant ₹100</b> paayein, aur jab wo ₹5000 tak withdraw kar lenge toh <b>₹500 Extra Bonus</b> auto-add hoga!</p>
                <div class="refer-box">
                    <p style="margin:0 0 5px 0; font-size:12px; color:#666;">Aapka Refer Link:</p>
                    <input type="text" id="refLink" value="{{ request.host_url }}login?ref={{ ref_code }}" readonly style="background:#fff; text-align:center; font-size:13px; font-weight:bold; border:1px solid #27ae60;">
                    <button onclick="copyRefLink()" style="background:#8E2DE2; margin-top:5px; padding:8px; font-size:14px;"><i class="fa-solid fa-copy"></i> Copy Referral Link</button>
                </div>
            </div>

            <div class="card">
                <h3 style="margin-top:0; color:#1c4d25;"><i class="fa-solid fa-history"></i> Referral History (Permanent)</h3>
                {% if not refer_history %}
                    <p style="color:#888; font-size:14px;">Abhi tak kisi ko refer nahi kiya hai.</p>
                {% else %}
                    <div style="overflow-x:auto;">
                        <table style="width:100%; border-collapse:collapse; font-size:13px;">
                            <tr style="background:#f2f2f2; text-align:left;">
                                <th style="padding:8px; border-bottom:1px solid #ddd;">Gmail ID</th>
                                <th style="padding:8px; border-bottom:1px solid #ddd;">Date</th>
                                <th style="padding:8px; border-bottom:1px solid #ddd;">Status</th>
                            </tr>
                            {% for ref in refer_history %}
                            <tr>
                                <td style="padding:8px; border-bottom:1px solid #eee; word-break:break-all;"><b>{{ ref[0] }}</b></td>
                                <td style="padding:8px; border-bottom:1px solid #eee; color:#666; font-size:11px;">{{ ref[1] }}</td>
                                <td style="padding:8px; border-bottom:1px solid #eee;">
                                    {% if ref[2] == 'MILESTONE_REACHED' %}
                                        <span style="color:#27ae60; font-weight:bold;">₹500 Bonus Paid</span>
                                    {% else %}
                                        <span style="color:#e67e22; font-weight:bold;">₹100 Credited</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                {% endif %}
            </div>
        {% endif %}

        {% if page == 'withdraw' %}
            <div class="card">
                <h3 style="margin-top:0; color:#1c4d25;">💸 Withdraw Funds</h3>
                <p style="font-size:12px; color:#555;">Total Withdrawn So Far: <b>₹{{ total_withdrawn }}</b></p>
                <form method="POST">
                    <input type="hidden" name="action" value="withdraw">
                    <label>Enter Amount (₹):</label>
                    <input type="number" name="amount" placeholder="Amount (Min ₹300)" min="1" required>
                    <label>Withdrawal Method:</label>
                    <select name="withdraw_type" id="withdraw_type" onchange="toggleWithdrawFields()" required>
                        <option value="upi">UPI Transfer</option>
                        <option value="bank">Bank Transfer</option>
                    </select>
                    <div id="upi-section">
                        <label>UPI ID:</label>
                        <input type="text" name="upi_id" placeholder="e.g. example@upi or 9876543210@paytm">
                    </div>
                    <div id="bank-section" style="display:none;">
                        <label>Account Holder Name:</label>
                        <input type="text" name="acc_holder" placeholder="Enter Full Name">
                        <label>Bank Name:</label>
                        <input type="text" name="bank_name" placeholder="e.g. SBI / HDFC / Paytm Bank">
                        <label>Account Number:</label>
                        <input type="number" name="acc_number" placeholder="Enter Account Number">
                        <label>IFSC Code:</label>
                        <input type="text" name="ifsc_code" placeholder="e.g. SBIN0001234" style="text-transform:uppercase;">
                    </div>
                    <input type="submit" value="Submit Withdrawal Request">
                </form>
            </div>
        {% endif %}
    </div>

    <div class="bottom-nav">
        <a href="/" class="nav-item">
            <div class="nav-icon red-grad">
                <i class="fa-solid fa-briefcase" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:9px; font-weight:700; color:#2c3e50; display:block;">Kam Lo</span>
        </a>
        <a href="/kam_do" class="nav-item">
            <div class="nav-icon green-grad">
                <i class="fa-solid fa-rectangle-ad" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:9px; font-weight:700; color:#2c3e50; display:block;">Kam Do</span>
        </a>
        <a href="/reels" class="nav-item">
            <div class="nav-icon pink-grad">
                <i class="fa-solid fa-clapperboard" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:9px; font-weight:700; color:#2c3e50; display:block;">Reels</span>
        </a>
        <a href="/refer" class="nav-item">
            <div class="nav-icon purple-grad">
                <i class="fa-solid fa-gift" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:9px; font-weight:700; color:#2c3e50; display:block;">Refer</span>
        </a>
        <a href="/withdraw" class="nav-item">
            <div class="nav-icon blue-grad">
                <i class="fa-solid fa-wallet" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:9px; font-weight:700; color:#2c3e50; display:block;">Withdraw</span>
        </a>
    </div>

    <div id="profileModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:100000; justify-content:center; align-items:center;">
        <div style="background:#fff; padding:20px; border-radius:15px; width:88%; max-width:360px; text-align:center; position:relative; box-shadow:0 10px 25px rgba(0,0,0,0.2); max-height: 90vh; overflow-y: auto;">
            <span onclick="closeProfileModal()" style="position:absolute; right:15px; top:10px; font-size:24px; cursor:pointer; font-weight:bold; color:#888;">&times;</span>
            {% if profile_pic %}
                <img src="/static/uploads/{{ profile_pic }}" class="profile-avatar">
            {% else %}
                <div class="profile-avatar">👤</div>
            {% endif %}
            <h3 style="margin:5px 0; color:#1c4d25;">User Profile</h3>
            <p style="margin:5px 0; color:#555; font-size:14px; word-break:break-all;"><b>ID:</b> {{ phone }}</p>
            <p style="margin:5px 0 15px 0; color:#27ae60; font-weight:bold; font-size:16px;">Balance: ₹{{ balance }}</p>

            <button onclick="toggleEditProfile()" style="background:#3498db; margin-bottom:8px; font-size:14px; padding:9px;">✏️ Edit Profile Pic</button>
            <div id="editProfileSection" style="display:none; background:#f9f9f9; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid #ddd;">
                <form method="POST" action="/update_profile" enctype="multipart/form-data">
                    <label style="font-size:12px; font-weight:bold; display:block; text-align:left;">Choose New Photo:</label>
                    <input type="file" name="new_profile_pic" accept="image/*" required style="font-size:12px;">
                    <input type="submit" value="Upload & Save" style="background:#27ae60; padding:8px; font-size:13px; margin-top:5px;">
                </form>
            </div>

            <button onclick="toggleWorkHistory()" style="background:#2c3e50; margin-bottom:8px; font-size:14px; padding:9px;">📜 Work History & PDF</button>
            <div id="workHistorySection" style="display:none; background:#f9f9f9; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid #ddd; text-align:left; max-height:220px; overflow-y:auto;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <h4 style="margin:0; color:#1c4d25; font-size:13px;">Completed History:</h4>
                    <a href="/download_pdf?type=worker" style="background:#3498db; color:#fff; padding:4px 8px; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;"><i class="fa-solid fa-download"></i> PDF Download</a>
                </div>
                {% if not work_history %}
                    <p style="font-size:12px; color:#888;">Abhi tak koi work history nahi hai.</p>
                {% else %}
                    {% for wh in work_history %}
                        <div style="border-bottom:1px solid #e0e0e0; padding:8px 0; font-size:12px;">
                            <b>{{ wh[0] }}</b><br>
                            <span style="color:#27ae60; font-weight:bold;">Earned: ₹{{ wh[1] }}</span><br>
                            <span style="color:#555;">Started: {{ wh[2] }}</span><br>
                            <span style="color:#555;">Finished: {{ wh[3] or 'In Progress' }}</span><br>
                            <span style="color:#666;">Status: <b>{{ wh[4] }}</b></span>
                        </div>
                    {% endfor %}
                {% endif %}
            </div>

            <button onclick="toggleLocationEdit()" style="background:#16a085; margin-bottom:8px; font-size:14px; padding:9px;">📍 Location Settings</button>
            <div id="locationEditSection" style="display:none; background:#f9f9f9; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid #ddd; text-align:left;">
                <form method="POST" action="/update_location">
                    <label style="font-size:11px; font-weight:bold;">Area / Address Name:</label>
                    <input type="text" name="location_name" id="prof_loc_name" value="{{ user_loc_name }}" required style="font-size:13px; padding:8px; margin:2px 0 6px 0;">
                    <input type="hidden" name="lat" id="prof_lat" value="{{ user_lat }}">
                    <input type="hidden" name="lng" id="prof_lng" value="{{ user_lng }}">
                    <button type="button" onclick="getProfileLocation()" style="background:#3498db; padding:6px; font-size:12px; margin-bottom:6px;">📡 Get Live Location</button>
                    <input type="submit" value="Save Location" style="background:#16a085; padding:8px; font-size:13px;">
                </form>
            </div>

            <button onclick="toggleChangePassword()" style="background:#e67e22; margin-bottom:8px; font-size:14px; padding:9px;">🔑 Change Password</button>
            <div id="changePasswordSection" style="display:none; background:#f9f9f9; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid #ddd; text-align:left;">
                <form method="POST" action="/change_password">
                    <label style="font-size:11px; font-weight:bold;">Old Password:</label>
                    <input type="password" name="old_password" placeholder="Enter old password" required style="font-size:13px; padding:8px; margin:4px 0 8px 0;">
                    <label style="font-size:11px; font-weight:bold;">New Password:</label>
                    <input type="password" name="new_password" placeholder="Enter new password" required style="font-size:13px; padding:8px; margin:4px 0 8px 0;">
                    <input type="submit" value="Update Password" style="background:#e67e22; padding:8px; font-size:13px; margin-top:5px;">
                </form>
            </div>

            <a href="/withdraw" style="display:block; background:#27ae60; color:#fff; padding:10px; border-radius:8px; text-decoration:none; font-weight:bold; margin-bottom:8px; font-size:14px;">💸 Withdraw Funds</a>
            <a href="mailto:rp619653@gmail.com?subject=Sab%20Kamao%20Support%20Help" style="display:block; background:#f39c12; color:#fff; padding:10px; border-radius:8px; text-decoration:none; font-weight:bold; margin-bottom:8px; font-size:14px;">🎧 Customer Service</a>
            <a href="/logout" style="display:block; background:#e74c3c; color:#fff; padding:10px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:14px;">🚪 Logout</a>
        </div>
    </div>

    <script>
        function openProfileModal() { document.getElementById('profileModal').style.display = 'flex'; }
        function closeProfileModal() { document.getElementById('profileModal').style.display = 'none'; }
        function toggleEditProfile() {
            var elem = document.getElementById('editProfileSection');
            elem.style.display = elem.style.display === 'none' ? 'block' : 'none';
        }
        function toggleWorkHistory() {
            var elem = document.getElementById('workHistorySection');
            elem.style.display = elem.style.display === 'none' ? 'block' : 'none';
        }
        function toggleLocationEdit() {
            var elem = document.getElementById('locationEditSection');
            elem.style.display = elem.style.display === 'none' ? 'block' : 'none';
        }
        function toggleChangePassword() {
            var elem = document.getElementById('changePasswordSection');
            elem.style.display = elem.style.display === 'none' ? 'block' : 'none';
        }
        function toggleEditReel(reelId) {
            var elem = document.getElementById('edit_reel_' + reelId);
            elem.style.display = elem.style.display === 'none' ? 'block' : 'none';
        }
        function toggleWithdrawFields() {
            var typeElem = document.getElementById('withdraw_type');
            if(!typeElem) return;
            var type = typeElem.value;
            if(type === 'bank') {
                document.getElementById('bank-section').style.display = 'block';
                document.getElementById('upi-section').style.display = 'none';
            } else {
                document.getElementById('bank-section').style.display = 'none';
                document.getElementById('upi-section').style.display = 'block';
            }
        }
        function copyRefLink() {
            var copyText = document.getElementById("refLink");
            copyText.select();
            copyText.setSelectionRange(0, 99999);
            navigator.clipboard.writeText(copyText.value);
            alert("Referral link copied to clipboard!");
        }

        function getProfileLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    var lat = position.coords.latitude;
                    var lng = position.coords.longitude;
                    document.getElementById('prof_lat').value = lat;
                    document.getElementById('prof_lng').value = lng;
                    
                    fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat=' + lat + '&lon=' + lng)
                        .then(response => response.json())
                        .then(data => {
                            if(data && data.address) {
                                var name = data.address.suburb || data.address.neighbourhood || data.address.city || data.address.town || data.display_name;
                                document.getElementById('prof_loc_name').value = name;
                            }
                        }).catch(e => console.log(e));

                    alert("Location & Address fetched!");
                }, function(error) {
                    alert("Unable to retrieve live location.");
                });
            }
        }

        const ratePerHour = 75;

        function initTaskStart(taskId) {
            localStorage.removeItem('sab_kamao_start_' + taskId);
            localStorage.setItem('sab_kamao_start_' + taskId, Date.now().toString());
        }

        function clearTaskTimer(taskId) {
            localStorage.removeItem('sab_kamao_start_' + taskId);
        }

        function updateTimer() {
            const timerElem = document.getElementById('time-display');
            if (timerElem) {
                {% if active_task_info %}
                    var activeId = "{{ active_task_info[0] }}";
                    var key = 'sab_kamao_start_' + activeId;
                    let startTime = localStorage.getItem(key);
                    if (!startTime) {
                        startTime = Date.now().toString();
                        localStorage.setItem(key, startTime);
                    }
                    let now = Date.now();
                    let seconds = Math.floor((now - parseInt(startTime)) / 1000);
                    if (seconds < 0) seconds = 0;

                    document.getElementById('elapsed_seconds').value = seconds;
                    let hrs = Math.floor(seconds / 3600);
                    let mins = Math.floor((seconds % 3600) / 60);
                    let secs = seconds % 60;
                    let formattedTime = (hrs < 10 ? "0" + hrs : hrs) + ":" + (mins < 10 ? "0" + mins : mins) + ":" + (secs < 10 ? "0" + secs : secs);
                    timerElem.innerText = formattedTime;
                    let currentEarning = ((seconds / 3600) * ratePerHour).toFixed(2);
                    document.getElementById('earning-display').innerText = "Earned: ₹" + currentEarning;
                {% endif %}
            }
        }
        setInterval(updateTimer, 1000);
        window.onload = updateTimer;
    </script>
</body>
</html>
"""

def get_reel_comments(reel_id):
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()
    c.execute("SELECT commenter_phone, comment_text, timestamp FROM reel_comments WHERE reel_id = ? ORDER BY id DESC", (reel_id,))
    comms = c.fetchall()
    conn.close()
    return comms

app.jinja_env.globals.update(get_reel_comments=get_reel_comments)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ""
    ref_code_input = request.args.get('ref', '').strip()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        ref_code_input = request.form.get('ref_code_input', '').strip()
        
        profile_pic_filename = ''
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename, ALLOWED_IMG_EXTENSIONS):
                filename = secure_filename(f"{email}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_pic_filename = filename

        if "@" in email and "." in email and len(password) > 0:
            conn = sqlite3.connect('sab_kamao.db')
            c = conn.cursor()
            c.execute('SELECT phone, password, referral_code FROM users WHERE phone = ?', (email,))
            row = c.fetchone()
            
            my_unique_ref = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))

            if not row:
                hashed_pw = generate_password_hash(password)
                c.execute('INSERT INTO users (phone, balance, profile_pic, referral_code, password, location_name) VALUES (?, 0.0, ?, ?, ?, ?)', 
                            (email, profile_pic_filename, my_unique_ref, hashed_pw, 'Greater Noida'))
                conn.commit()

                if ref_code_input:
                    c.execute('SELECT phone FROM users WHERE referral_code = ?', (ref_code_input,))
                    referrer = c.fetchone()
                    if referrer and referrer[0] != email:
                        referrer_phone = referrer[0]
                        c.execute('UPDATE users SET balance = balance + 100.0 WHERE phone = ?', (referrer_phone,))
                        c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                                    (referrer_phone, 100.0, f"Referral Bonus (User: {email})"))
                        c.execute('INSERT INTO referrals (referrer_phone, referred_phone, status) VALUES (?, ?, ?)',
                                    (referrer_phone, email, 'REGISTERED'))
                        conn.commit()
                
                session['phone'] = email
                session['logged_in'] = True
                conn.close()
                flash("🎉 Account Successfully Created & Logged In!", "success")
                return redirect(url_for('home'))
            else:
                stored_hash = row[1]
                if not stored_hash:
                    c.execute('UPDATE users SET password = ? WHERE phone = ?', (generate_password_hash(password), email))
                    conn.commit()
                    stored_hash = generate_password_hash(password)

                if check_password_hash(stored_hash, password):
                    session['phone'] = email
                    session['logged_in'] = True
                    if profile_pic_filename:
                        c.execute('UPDATE users SET profile_pic = ? WHERE phone = ?', (profile_pic_filename, email))
                        conn.commit()
                    if not row[2]:
                        c.execute('UPDATE users SET referral_code = ? WHERE phone = ?', (my_unique_ref, email))
                        conn.commit()
                    conn.close()
                    return redirect(url_for('home'))
                else:
                    conn.close()
                    msg = "❌ Galat Password! Kripya sahi password dalein."
        else:
            msg = "❌ Kripya valid Gmail address aur password dalein."

    return render_template_string(LOGIN_TEMPLATE, msg=msg, ref_code_input=ref_code_input)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    phone = session.get('phone')
    if 'new_profile_pic' in request.files:
        file = request.files['new_profile_pic']
        if file and allowed_file(file.filename, ALLOWED_IMG_EXTENSIONS):
            filename = secure_filename(f"{phone}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn = sqlite3.connect('sab_kamao.db')
            c = conn.cursor()
            c.execute('UPDATE users SET profile_pic = ? WHERE phone = ?', (filename, phone))
            conn.commit()
            conn.close()
            flash("✅ Profile picture updated successfully!", "success")
    return redirect(request.referrer or url_for('home'))

@app.route('/update_location', methods=['POST'])
def update_location():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    phone = session.get('phone')
    try:
        location_name = request.form.get('location_name', 'Greater Noida').strip()
        lat = float(request.form.get('lat', 28.4744))
        lng = float(request.form.get('lng', 77.5040))
        conn = sqlite3.connect('sab_kamao.db')
        c = conn.cursor()
        c.execute('UPDATE users SET lat = ?, lng = ?, location_name = ? WHERE phone = ?', (lat, lng, location_name, phone))
        conn.commit()
        conn.close()
        flash("✅ Location successfully updated!", "success")
    except Exception as e:
        flash("❌ Invalid location values!", "danger")
    return redirect(url_for('home'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    phone = session.get('phone')
    old_password = request.form.get('old_password', '').strip()
    new_password = request.form.get('new_password', '').strip()

    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE phone = ?', (phone,))
    row = c.fetchone()
    conn.close()

    if row and row[0] and check_password_hash(row[0], old_password):
        if len(new_password) > 0:
            new_hashed = generate_password_hash(new_password)
            conn = sqlite3.connect('sab_kamao.db')
            c = conn.cursor()
            c.execute('UPDATE users SET password = ? WHERE phone = ?', (new_hashed, phone))
            conn.commit()
            conn.close()
            flash("✅ Password successfully changed!", "success")
        else:
            flash("❌ Naya password khali nahi ho sakta.", "danger")
    else:
        flash("❌ Purana password galat hai!", "danger")

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    msg = ""
    phone = session.get('phone')
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'verify_task_otp':
            c.execute("SELECT id FROM tasks WHERE worker_phone = ? AND status IN ('IN_PROGRESS', 'WAITING_OWNER_APPROVAL')", (phone,))
            existing_active = c.fetchone()
            if existing_active:
                msg = "❌ Aapka ek task pehle se active hai! Naya task shuru nahi kar sakte."
            else:
                task_id = request.form.get('task_id')
                input_otp = request.form.get('otp', '').strip()
                c.execute("SELECT otp, title FROM tasks WHERE id = ? AND status = 'OPEN'", (task_id,))
                task = c.fetchone()
                if task and str(task[0]).strip() == str(input_otp):
                    start_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    c.execute("UPDATE tasks SET status = 'IN_PROGRESS', worker_phone = ?, start_time = ? WHERE id = ?", (phone, start_dt, task_id))
                    conn.commit()
                    msg = "🎉 OTP Verified! Work Started. Timer chalu ho gaya hai."
                else:
                    msg = "❌ Galat OTP ya Task Pehle se active hai!"
        elif action == 'worker_finish_work':
            task_id = request.form.get('task_id')
            total_time_seconds = float(request.form.get('elapsed_seconds', 0))
            hours = total_time_seconds / 3600
            total_earned = round(hours * 75, 2)
            if total_earned < 1.0:
                total_earned = 1.0
            
            comp_otp = str(random.randint(1000, 9999))
            finish_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            c.execute("UPDATE tasks SET status = 'WAITING_OWNER_APPROVAL', completion_otp = ?, finish_time = ?, amount_earned = ? WHERE id = ? AND worker_phone = ?", 
                        (comp_otp, finish_dt, total_earned, task_id, phone))
            
            c.execute('UPDATE users SET balance = balance + ? WHERE phone = ?', (total_earned, phone))
            c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                        (phone, total_earned, f"Work Earned: ₹{total_earned} (₹75/hr)"))
            conn.commit()
            msg = f"🎉 Work Finished! Aapne ₹{total_earned} kamaye. Ab Kam Dene Wale (Owner) ko apna Completion OTP dein taaki wo task final close kar sake."

    c.execute("SELECT balance, profile_pic, lat, lng, location_name FROM users WHERE phone=?", (phone,))
    res = c.fetchone()
    balance = res[0] if res else 0.0
    profile_pic = res[1] if res else ''
    user_lat = res[2] if res and res[2] else 28.4744
    user_lng = res[3] if res and res[3] else 77.5040
    user_loc_name = res[4] if res and res[4] else 'Greater Noida'

    c.execute("SELECT id, title, status, completion_otp, start_time, amount_earned FROM tasks WHERE worker_phone = ? AND status IN ('IN_PROGRESS', 'WAITING_OWNER_APPROVAL')", (phone,))
    active_task_info = c.fetchone()

    open_tasks = []
    if not active_task_info:
        c.execute("SELECT t.id, t.title, t.payment_method, t.otp, t.lat, t.lng, t.provider_phone, u.profile_pic, t.location_name FROM tasks t JOIN users u ON t.provider_phone = u.phone WHERE t.status = 'OPEN'")
        all_open_tasks = c.fetchall()
        for t in all_open_tasks:
            t_id, t_title, t_pay, t_otp, t_lat, t_lng, t_provider, t_dp, t_loc_name = t
            dist = calculate_distance(user_lat, user_lng, t_lat, t_lng)
            if dist <= 3.5: 
                open_tasks.append((t_id, t_title, t_pay, t_otp, t_lat, t_lng, t_provider, t_dp, t_loc_name, dist))

    c.execute("SELECT title, amount_earned, start_time, finish_time, status FROM tasks WHERE worker_phone = ? ORDER BY id DESC", (phone,))
    work_history = c.fetchall()

    conn.close()

    return render_template_string(HTML_TEMPLATE, page='home', phone=phone, balance=balance, profile_pic=profile_pic, open_tasks=open_tasks, active_task_info=active_task_info, user_lat=user_lat, user_lng=user_lng, user_loc_name=user_loc_name, work_history=work_history, msg=msg)

@app.route('/kam_do', methods=['GET', 'POST'])
def kam_do():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    msg = ""
    phone = session.get('phone')
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_task':
            title = request.form.get('title')
            pay_method = request.form.get('pay_method')
            
            c.execute("SELECT lat, lng, location_name FROM users WHERE phone = ?", (phone,))
            u_data = c.fetchone()
            t_lat = u_data[0] if u_data else 28.4744
            t_lng = u_data[1] if u_data else 77.5040
            task_loc_name = u_data[2] if u_data else 'Greater Noida'

            gen_otp = str(random.randint(1000, 9999))
            post_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT INTO tasks (provider_phone, title, payment_method, otp, status, start_time, lat, lng, location_name) VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)",
                        (phone, title, pay_method, gen_otp, post_dt, t_lat, t_lng, task_loc_name))
            conn.commit()
            msg = f"✅ Task Posted! OTP: <b style='font-size:22px; color:#e67e22;'>{gen_otp}</b> (Ye OTP kaam karne wale ko dein)"
        elif action == 'owner_verify_completion':
            task_id = request.form.get('task_id')
            entered_otp = request.form.get('entered_completion_otp', '').strip()
            c.execute("SELECT completion_otp, provider_phone FROM tasks WHERE id = ? AND status = 'WAITING_OWNER_APPROVAL'", (task_id,))
            t_row = c.fetchone()
            if t_row and t_row[1] == phone and str(t_row[0]).strip() == str(entered_otp):
                c.execute("UPDATE tasks SET status = 'COMPLETED' WHERE id = ?", (task_id,))
                conn.commit()
                msg = "✅ Task successfully verified and closed!"
            else:
                msg = "❌ Galat Completion OTP!"

    c.execute("SELECT balance, profile_pic, lat, lng, location_name FROM users WHERE phone=?", (phone,))
    res = c.fetchone()
    balance = res[0] if res else 0.0
    profile_pic = res[1] if res else ''
    user_lat = res[2] if res and res[2] else 28.4744
    user_lng = res[3] if res and res[3] else 77.5040
    user_loc_name = res[4] if res and res[4] else 'Greater Noida'

    c.execute("SELECT id, title, payment_method, otp, status, start_time, finish_time, location_name FROM tasks WHERE provider_phone = ? ORDER BY id DESC", (phone,))
    my_tasks = c.fetchall()

    c.execute("SELECT title, amount_earned, start_time, finish_time, status FROM tasks WHERE worker_phone = ? ORDER BY id DESC", (phone,))
    work_history = c.fetchall()

    conn.close()

    return render_template_string(HTML_TEMPLATE, page='kam_do', phone=phone, balance=balance, profile_pic=profile_pic, my_tasks=my_tasks, user_lat=user_lat, user_lng=user_lng, user_loc_name=user_loc_name, work_history=work_history, msg=msg)

@app.route('/reels', methods=['GET', 'POST'])
def reels():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    msg = ""
    phone = session.get('phone')
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'upload_reel':
            caption = request.form.get('caption', '').strip()
            if 'reel_video' in request.files:
                file = request.files['reel_video']
                if file and allowed_file(file.filename, ALLOWED_VID_EXTENSIONS):
                    vid_filename = secure_filename(f"{phone}_{int(datetime.now().timestamp())}_{file.filename}")
                    file.save(os.path.join(app.config['VIDEO_FOLDER'], vid_filename))
                    
                    c.execute("INSERT INTO reels (uploader_phone, caption, video_filename) VALUES (?, ?, ?)",
                                (phone, caption, vid_filename))
                    conn.commit()
                    msg = "✅ Reel successfully uploaded and published publicly!"
                else:
                    msg = "❌ Invalid video format! Please upload MP4/MOV."
        elif action == 'like_reel':
            reel_id = request.form.get('reel_id')
            c.execute("UPDATE reels SET likes = likes + 1 WHERE id = ?", (reel_id,))
            conn.commit()
        elif action == 'edit_reel':
            reel_id = request.form.get('reel_id')
            new_caption = request.form.get('new_caption', '').strip()
            c.execute("UPDATE reels SET caption = ? WHERE id = ? AND uploader_phone = ?", (new_caption, reel_id, phone))
            conn.commit()
            msg = "✅ Reel title updated successfully!"
        elif action == 'delete_reel':
            reel_id = request.form.get('reel_id')
            c.execute("SELECT video_filename FROM reels WHERE id = ? AND uploader_phone = ?", (reel_id, phone))
            row = c.fetchone()
            if row:
                v_file = row[0]
                try:
                    os.remove(os.path.join(app.config['VIDEO_FOLDER'], v_file))
                except:
                    pass
                c.execute("DELETE FROM reels WHERE id = ?", (reel_id,))
                c.execute("DELETE FROM reel_comments WHERE reel_id = ?", (reel_id,))
                conn.commit()
                msg = "🗑️ Reel deleted successfully!"
        elif action == 'add_comment':
            reel_id = request.form.get('reel_id')
            comment_text = request.form.get('comment_text', '').strip()
            if comment_text:
                c.execute("INSERT INTO reel_comments (reel_id, commenter_phone, comment_text) VALUES (?, ?, ?)",
                            (reel_id, phone, comment_text))
                conn.commit()

    c.execute("SELECT balance, profile_pic, lat, lng, location_name FROM users WHERE phone=?", (phone,))
    res = c.fetchone()
    balance = res[0] if res else 0.0
    profile_pic = res[1] if res else ''
    user_lat = res[2] if res and res[2] else 28.4744
    user_lng = res[3] if res and res[3] else 77.5040
    user_loc_name = res[4] if res and res[4] else 'Greater Noida'

    c.execute("SELECT r.id, r.uploader_phone, r.caption, r.video_filename, r.timestamp, u.profile_pic, r.likes FROM reels r JOIN users u ON r.uploader_phone = u.phone ORDER BY r.id DESC")
    all_reels = c.fetchall()

    c.execute("SELECT title, amount_earned, start_time, finish_time, status FROM tasks WHERE worker_phone = ? ORDER BY id DESC", (phone,))
    work_history = c.fetchall()

    conn.close()

    return render_template_string(HTML_TEMPLATE, page='reels', phone=phone, balance=balance, profile_pic=profile_pic, all_reels=all_reels, user_lat=user_lat, user_lng=user_lng, user_loc_name=user_loc_name, work_history=work_history, msg=msg)

@app.route('/refer', methods=['GET'])
def refer():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    phone = session.get('phone')
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()

    c.execute("SELECT balance, profile_pic, referral_code, lat, lng, location_name FROM users WHERE phone=?", (phone,))
    user = c.fetchone()
    balance = user[0] if user else 0.0
    profile_pic = user[1] if user else ''
    ref_code = user[2] if user and user[2] else 'REF123'
    user_lat = user[3] if user and user[3] else 28.4744
    user_lng = user[4] if user and user[4] else 77.5040
    user_loc_name = user[5] if user and user[5] else 'Greater Noida'

    c.execute("SELECT referred_phone, timestamp, status FROM referrals WHERE referrer_phone = ? ORDER BY id DESC", (phone,))
    refer_history = c.fetchall()

    c.execute("SELECT title, amount_earned, start_time, finish_time, status FROM tasks WHERE worker_phone = ? ORDER BY id DESC", (phone,))
    work_history = c.fetchall()

    conn.close()

    return render_template_string(HTML_TEMPLATE, page='refer', phone=phone, balance=balance, profile_pic=profile_pic, ref_code=ref_code, refer_history=refer_history, user_lat=user_lat, user_lng=user_lng, user_loc_name=user_loc_name, work_history=work_history)

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    msg = ""
    phone = session.get('phone')
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'withdraw':
            amount = float(request.form.get('amount', 0))
            withdraw_type = request.form.get('withdraw_type')

            if withdraw_type == 'upi':
                upi_id = request.form.get('upi_id', '')
                details_str = f"UPI ID: {upi_id}"
            else:
                acc_holder = request.form.get('acc_holder', '')
                bank_name = request.form.get('bank_name', '')
                acc_number = request.form.get('acc_number', '')
                ifsc_code = request.form.get('ifsc_code', '').upper()
                details_str = f"Name: {acc_holder}\nBank: {bank_name}\nAccount No: {acc_number}\nIFSC: {ifsc_code}"

            c.execute('SELECT balance, total_withdrawn FROM users WHERE phone = ?', (phone,))
            res = c.fetchone()
            current_bal = res[0] if res else 0.0
            total_withdrawn_so_far = res[1] if res else 0.0

            if amount < 300:
                msg = "❌ Minimum withdrawal amount is ₹300!"
            elif amount > current_bal:
                msg = "❌ Insufficient Balance!"
            else:
                new_total_withdrawn = total_withdrawn_so_far + amount
                c.execute('UPDATE users SET balance = balance - ?, total_withdrawn = ? WHERE phone = ?', (amount, new_total_withdrawn, phone))
                c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                            (phone, -amount, f"Withdrawal ({withdraw_type.upper()})"))
                conn.commit()

                c.execute("SELECT referrer_phone, milestone_paid FROM referrals WHERE referred_phone = ?", (phone,))
                ref_record = c.fetchone()
                if ref_record and ref_record[1] == 0: 
                    if new_total_withdrawn >= 5000:
                        referrer_phone = ref_record[0]
                        c.execute('UPDATE users SET balance = balance + 500.0 WHERE phone = ?', (referrer_phone,))
                        c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                                    (referrer_phone, 500.0, f"Referral Milestone Bonus (User {phone} crossed ₹5000 withdrawal)"))
                        c.execute("UPDATE referrals SET milestone_paid = 1, status = 'MILESTONE_REACHED' WHERE referred_phone = ?", (phone,))
                        conn.commit()

                send_withdrawal_email(phone, amount, withdraw_type, details_str)
                msg = f"✅ ₹{amount} Withdrawal Request Submitted!"

    c.execute("SELECT balance, profile_pic, total_withdrawn, lat, lng, location_name FROM users WHERE phone=?", (phone,))
    res = c.fetchone()
    balance = res[0] if res else 0.0
    profile_pic = res[1] if res else ''
    total_withdrawn = res[2] if res else 0.0
    user_lat = res[3] if res and res[3] else 28.4744
    user_lng = res[4] if res and res[4] else 77.5040
    user_loc_name = res[5] if res and res[5] else 'Greater Noida'

    c.execute("SELECT title, amount_earned, start_time, finish_time, status FROM tasks WHERE worker_phone = ? ORDER BY id DESC", (phone,))
    work_history = c.fetchall()

    conn.close()

    return render_template_string(HTML_TEMPLATE, page='withdraw', phone=phone, balance=balance, profile_pic=profile_pic, total_withdrawn=total_withdrawn, user_lat=user_lat, user_lng=user_lng, user_loc_name=user_loc_name, work_history=work_history, msg=msg)

@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    phone = session.get('phone')
    history_type = request.args.get('type', 'worker')
    
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()
    if history_type == 'owner':
        c.execute("SELECT title, payment_method, status, start_time, finish_time, location_name FROM tasks WHERE provider_phone = ? ORDER BY id DESC", (phone,))
        title_text = "Task Provider History Report"
    else:
        c.execute("SELECT title, amount_earned, start_time, finish_time, status FROM tasks WHERE worker_phone = ? ORDER BY id DESC", (phone,))
        title_text = "Worker Earnings & History Report"
    rows = c.fetchall()
    conn.close()

    html_content = f"""
    <html>
    <head><title>{title_text}</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h2>{title_text}</h2>
        <p><b>User Account:</b> {phone}</p>
        <p><b>Generated Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <table border="1" cellpadding="8" cellspacing="0" style="width:100%; border-collapse:collapse; font-size:13px;">
            <tr style="background:#f2f2f2;">
                <th>Task Title</th>
                <th>Details / Earnings</th>
                <th>Start Time</th>
                <th>Finish Time</th>
                <th>Status</th>
            </tr>
    """
    for r in rows:
        html_content += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
    html_content += """
        </table>
        <br><button onclick="window.print()" style="padding:10px 20px; background:#27ae60; color:#fff; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">Print / Save as PDF</button>
    </body>
    </html>
    """
    response = make_response(html_content)
    response.headers["Content-Type"] = "text/html"
    return response

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
