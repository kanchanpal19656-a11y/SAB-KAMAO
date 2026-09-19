from flask import Flask, render_template_string, request, session, redirect, url_for, flash
import sqlite3
import random
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sab_kamao_secret_key_123'

def init_db():
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (phone TEXT PRIMARY KEY, balance REAL DEFAULT 0.0, profile_pic TEXT DEFAULT '', referral_code TEXT UNIQUE, total_withdrawn REAL DEFAULT 0.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, amount REAL, title TEXT, timestamp DATETIME DEFAULT (datetime('now', 'localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, provider_phone TEXT, title TEXT, payment_method TEXT, otp TEXT, status TEXT DEFAULT 'OPEN')''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_phone TEXT, referred_phone TEXT, status TEXT DEFAULT 'REGISTERED', milestone_paid INTEGER DEFAULT 0, timestamp DATETIME DEFAULT (datetime('now', 'localtime')))''')
    conn.commit()
    conn.close()

with app.app_context():
    init_db()

# ---------------- FILE UPLOAD CONFIG ----------------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- MAIL CONFIGURATION ----------------
SENDER_EMAIL = "rp619653@gmail.com"
SENDER_PASSWORD = "sybt bsag faxj bqip"  # Gmail App Password (16 digit)
ADMIN_EMAIL = "rp619653@gmail.com"

def send_email_otp(to_email, otp_code):
    try:
        print(f"==========================================")
        print(f"🔑 LIVE SCREEN OTP FOR {to_email} : {otp_code}")
        print(f"==========================================")
        return otp_code
    except Exception as e:
        print("OTP Error:", e)
        return otp_code

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
    <title>Sab Kamao - Login</title>
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
        input[type=email], input[type=number], input[type=text], input[type=file], input[type=submit] {
            width: 100%; padding: 12px; margin: 8px 0; border-radius: 10px; font-size: 14px;
        }
        input[type=email], input[type=number], input[type=text] {
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
              <div style="background: #e1f5fe; color: #01579b; padding: 12px; border-radius: 8px; margin: 10px 0; font-weight: bold; font-size: 15px; border: 1px solid #b3e5fc;">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if msg %}
            <p style="color:#e74c3c; font-weight:bold; font-size:14px;">{{ msg }}</p>
        {% endif %}

        {% if not otp_sent %}
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="step" value="send_otp">
                <input type="email" name="user_id" placeholder="Enter Gmail Address" required>
                <input type="text" name="ref_code_input" placeholder="Referral Code (Optional)" value="{{ request.args.get('ref', '') }}">
                <label style="font-size:12px; color:#555; display:block; text-align:left; margin-top:5px;">Profile Picture (Optional):</label>
                <input type="file" name="profile_pic" accept="image/*">
                <input type="submit" value="Send OTP to Email">
            </form>
        {% else %}
            <p style="color:#27ae60; font-weight:bold; font-size:14px;">📩 OTP Sent Successfully!</p>
            <form method="POST">
                <input type="hidden" name="step" value="verify_otp">
                <input type="number" name="entered_otp" placeholder="Enter 4-Digit OTP" required>
                <input type="submit" value="Verify OTP & Login">
            </form>
        {% endif %}
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
        input, select { width: 100%; padding: 11px; margin: 8px 0; border: 1px solid #ccc; border-radius: 8px; font-size: 15px; }
        input[type=submit], button { background: #27ae60; color: white; border: none; font-weight: bold; cursor: pointer; padding: 12px; border-radius: 8px; width: 100%; font-size: 16px; margin-top: 5px; }
        .timer { font-size: 32px; font-weight: bold; color: #e67e22; text-align: center; margin: 10px 0; }
        .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: #ffffff; display: flex; justify-content: space-around; align-items: center; padding: 8px 0; border-top: 1px solid #e0e0e0; z-index: 99999; box-shadow: 0 -4px 15px rgba(0,0,0,0.08); }
        .nav-item { text-decoration: none; text-align: center; flex: 1; color: #333; cursor: pointer; }
        .nav-icon { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 3px auto; }
        .red-grad { background: linear-gradient(135deg, #FF512F, #DD2476); box-shadow: 0 3px 8px rgba(221,36,118,0.3); }
        .green-grad { background: linear-gradient(135deg, #11998e, #38ef7d); box-shadow: 0 3px 8px rgba(56,239,125,0.3); }
        .blue-grad { background: linear-gradient(135deg, #2193b0, #6dd5ed); box-shadow: 0 3px 8px rgba(33,147,176,0.3); }
        .purple-grad { background: linear-gradient(135deg, #8E2DE2, #4A00E0); box-shadow: 0 3px 8px rgba(142,45,226,0.3); }
        .profile-avatar {
            width: 80px; height: 80px; border-radius: 50%; object-fit: cover;
            border: 3px solid #27ae60; margin: 0 auto 10px auto; display: flex;
            align-items: center; justify-content: center; font-size: 40px; background: #e8f5e9;
        }
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
        {% if msg %}
            <div class="card" style="color:#1c4d25; font-weight:bold; text-align:center;">{{ msg|safe }}</div>
        {% endif %}

        {% if page == 'home' %}
            <div class="card">
                <h3 style="margin-top:0; color:#1c4d25;">💼 Available Tasks (Kam Lo)</h3>
                {% if not open_tasks %}
                    <p style="color:#888;">Abhi koi open task nahi hai.</p>
                {% endif %}
                {% for task in open_tasks %}
                    <div style="border-bottom:1px solid #eee; padding:10px 0;">
                        <b>{{ task[1] }}</b><br>
                        <small style="color:#555;">Payment Mode: <b>{{ task[2] }}</b></small>
                        <form method="POST" style="margin-top:5px;" onsubmit="startTaskTimer('{{ task[1] }}')">
                            <input type="hidden" name="action" value="verify_task_otp">
                            <input type="hidden" name="task_id" value="{{ task[0] }}">
                            <input type="number" name="otp" placeholder="Enter OTP from Task Owner" required>
                            <input type="submit" value="Start Work with OTP">
                        </form>
                    </div>
                {% endfor %}
            </div>

            {% if session.get('active_task') %}
                <div class="card">
                    <h3 style="text-align:center; color:#1c4d25; margin-top:0;">⏱️ Live Work Counter</h3>
                    <p style="text-align:center; margin:0; color:#555;">Active Task: <b id="active-task-title">{{ session.get('active_task_title') }}</b></p>
                    <div class="timer" id="time-display">00:00:00</div>
                    <div style="text-align:center; font-size:20px; color:#27ae60; font-weight:bold;" id="earning-display">Earned: ₹0.00</div>
                    <form method="POST" style="margin-top:15px;" onsubmit="clearTaskTimer()">
                        <input type="hidden" name="action" value="complete_work">
                        <input type="hidden" name="elapsed_seconds" id="elapsed_seconds" value="0">
                        <input type="submit" value="Finish Work & Collect Earnings" style="background:#e74c3c;">
                    </form>
                </div>
            {% endif %}
        {% endif %}

        {% if page == 'kam_do' %}
            <div class="card">
                <h3 style="margin-top:0; color:#1c4d25;">➕ Post a New Task (Kam Do)</h3>
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
                    <input type="submit" value="Post Task & Generate OTP">
                </form>
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
            <span style="font-size:10px; font-weight:700; color:#2c3e50; display:block;">Kam Lo</span>
        </a>
        <a href="/kam_do" class="nav-item">
            <div class="nav-icon green-grad">
                <i class="fa-solid fa-rectangle-ad" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:10px; font-weight:700; color:#2c3e50; display:block;">Kam Do</span>
        </a>
        <a href="/refer" class="nav-item">
            <div class="nav-icon purple-grad">
                <i class="fa-solid fa-gift" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:10px; font-weight:700; color:#2c3e50; display:block;">Refer</span>
        </a>
        <a href="/withdraw" class="nav-item">
            <div class="nav-icon blue-grad">
                <i class="fa-solid fa-wallet" style="font-size:16px; color:#fff;"></i>
            </div>
            <span style="font-size:10px; font-weight:700; color:#2c3e50; display:block;">Withdraw</span>
        </a>
    </div>

    <div id="profileModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:100000; justify-content:center; align-items:center;">
        <div style="background:#fff; padding:20px; border-radius:15px; width:88%; max-width:360px; text-align:center; position:relative; box-shadow:0 10px 25px rgba(0,0,0,0.2);">
            <span onclick="closeProfileModal()" style="position:absolute; right:15px; top:10px; font-size:24px; cursor:pointer; font-weight:bold; color:#888;">&times;</span>
            {% if profile_pic %}
                <img src="/static/uploads/{{ profile_pic }}" class="profile-avatar">
            {% else %}
                <div class="profile-avatar">👤</div>
            {% endif %}
            <h3 style="margin:5px 0; color:#1c4d25;">User Profile</h3>
            <p style="margin:5px 0; color:#555; font-size:14px;"><b>ID:</b> {{ phone }}</p>
            <p style="margin:5px 0 15px 0; color:#27ae60; font-weight:bold; font-size:16px;">Balance: ₹{{ balance }}</p>

            <button onclick="toggleEditProfile()" style="background:#3498db; margin-bottom:8px; font-size:14px; padding:9px;">✏️ Edit Profile Pic</button>
            <div id="editProfileSection" style="display:none; background:#f9f9f9; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid #ddd;">
                <form method="POST" action="/update_profile" enctype="multipart/form-data">
                    <label style="font-size:12px; font-weight:bold; display:block; text-align:left;">Choose New Photo:</label>
                    <input type="file" name="new_profile_pic" accept="image/*" required style="font-size:12px;">
                    <input type="submit" value="Upload & Save" style="background:#27ae60; padding:8px; font-size:13px; margin-top:5px;">
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

        const ratePerHour = 75;
        function startTaskTimer(taskTitle) {
            if (!localStorage.getItem('sab_kamao_seconds')) {
                localStorage.setItem('sab_kamao_seconds', '0');
            }
        }
        function clearTaskTimer() {
            localStorage.removeItem('sab_kamao_seconds');
        }
        function updateTimer() {
            const timerElem = document.getElementById('time-display');
            if (timerElem) {
                let seconds = parseInt(localStorage.getItem('sab_kamao_seconds') || '0');
                {% if session.get('active_task') %}
                seconds++;
                localStorage.setItem('sab_kamao_seconds', seconds);
                {% endif %}
                
                document.getElementById('elapsed_seconds').value = seconds;
                let hrs = Math.floor(seconds / 3600);
                let mins = Math.floor((seconds % 3600) / 60);
                let secs = seconds % 60;
                let formattedTime = (hrs < 10 ? "0" + hrs : hrs) + ":" + (mins < 10 ? "0" + mins : mins) + ":" + (secs < 10 ? "0" + secs : secs);
                timerElem.innerText = formattedTime;
                let currentEarning = ((seconds / 3600) * ratePerHour).toFixed(2);
                document.getElementById('earning-display').innerText = "Earned: ₹" + currentEarning;
            }
        }
        setInterval(updateTimer, 1000);
    </script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ""
    otp_sent = False
    ref_code_input = request.args.get('ref', '').strip()
    
    if request.method == 'POST':
        step = request.form.get('step')
        if step == 'send_otp':
            user_id = request.form.get('user_id', '').strip().lower()
            ref_code_input = request.form.get('ref_code_input', '').strip()
            profile_pic_filename = ''
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{user_id}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    profile_pic_filename = filename

            if "@" in user_id and "." in user_id:
                gen_otp = str(random.randint(1000, 9999))
                session['temp_user'] = user_id
                session['temp_login_otp'] = gen_otp
                session['temp_profile_pic'] = profile_pic_filename
                session['temp_ref_code'] = ref_code_input
                send_email_otp(user_id, gen_otp)
                flash(f"🔑 Aapka Test OTP yeh raha: {gen_otp}", "success")
                otp_sent = True
            else:
                msg = "❌ Kripya sahi Gmail address dalein."
        elif step == 'verify_otp':
            entered_otp = request.form.get('entered_otp', '').strip()
            correct_otp = session.get('temp_login_otp')
            user_id = session.get('temp_user')
            profile_pic = session.get('temp_profile_pic', '')
            ref_code = session.get('temp_ref_code', '')

            if entered_otp and entered_otp == correct_otp:
                session['phone'] = user_id
                session['logged_in'] = True
                session.pop('temp_login_otp', None)
                session.pop('temp_user', None)
                session.pop('temp_profile_pic', None)
                session.pop('temp_ref_code', None)

                conn = sqlite3.connect('sab_kamao.db')
                c = conn.cursor()
                c.execute('SELECT phone, referral_code FROM users WHERE phone = ?', (user_id,))
                row = c.fetchone()
                
                my_unique_ref = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))

                if not row:
                    c.execute('INSERT INTO users (phone, balance, profile_pic, referral_code) VALUES (?, 0.0, ?, ?)', (user_id, profile_pic, my_unique_ref))
                    conn.commit()

                    # Process Referral if code exists and valid
                    if ref_code:
                        c.execute('SELECT phone FROM users WHERE referral_code = ?', (ref_code,))
                        referrer = c.fetchone()
                        if referrer and referrer[0] != user_id:
                            referrer_phone = referrer[0]
                            # Give Instant ₹100 to referrer
                            c.execute('UPDATE users SET balance = balance + 100.0 WHERE phone = ?', (referrer_phone,))
                            c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                                        (referrer_phone, 100.0, f"Referral Bonus (User: {user_id})"))
                            # Record in referrals history
                            c.execute('INSERT INTO referrals (referrer_phone, referred_phone, status) VALUES (?, ?, ?)',
                                        (referrer_phone, user_id, 'REGISTERED'))
                            conn.commit()
                elif profile_pic:
                    c.execute('UPDATE users SET profile_pic = ? WHERE phone = ?', (profile_pic, user_id))
                    conn.commit()
                conn.close()
                return redirect(url_for('home'))
            else:
                otp_sent = True
                msg = "❌ Galat OTP! Screen par ya Render Logs par aaya OTP dalein."

    return render_template_string(LOGIN_TEMPLATE, msg=msg, otp_sent=otp_sent, ref_code_input=ref_code_input)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    phone = session.get('phone')
    if 'new_profile_pic' in request.files:
        file = request.files['new_profile_pic']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{phone}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn = sqlite3.connect('sab_kamao.db')
            c = conn.cursor()
            c.execute('UPDATE users SET profile_pic = ? WHERE phone = ?', (filename, phone))
            conn.commit()
            conn.close()
    return redirect(request.referrer or url_for('home'))

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
            task_id = request.form.get('task_id')
            input_otp = request.form.get('otp', '').strip()
            c.execute("SELECT otp, title FROM tasks WHERE id = ? AND status = 'OPEN'", (task_id,))
            task = c.fetchone()
            if task and str(task[0]).strip() == str(input_otp):
                c.execute("UPDATE tasks SET status = 'IN_PROGRESS' WHERE id = ?", (task_id,))
                conn.commit()
                session['active_task'] = task_id
                session['active_task_title'] = task[1]
                msg = "🎉 OTP Verified! Work Started. Timer chalu ho gaya hai."
            else:
                msg = "❌ Galat OTP या Task Pehle se active hai!"
        elif action == 'complete_work':
            total_time_seconds = float(request.form.get('elapsed_seconds', 0))
            hours = total_time_seconds / 3600
            total_earned = round(hours * 75, 2)
            if total_earned < 1.0:
                total_earned = 1.0
            c.execute('UPDATE users SET balance = balance + ? WHERE phone = ?', (total_earned, phone))
            c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                        (phone, total_earned, "Work Earned (₹75/hr)"))
            active_task_id = session.get('active_task')
            if active_task_id:
                c.execute("UPDATE tasks SET status = 'COMPLETED' WHERE id = ?", (active_task_id,))
            conn.commit()
            session.pop('active_task', None)
            session.pop('active_task_title', None)
            msg = f"🎉 Work Finished! Aapne ₹{total_earned} kamaye aur Wallet me add ho gaye!"

    c.execute("SELECT balance, profile_pic FROM users WHERE phone=?", (phone,))
    res = c.fetchone()
    balance = res[0] if res else 0.0
    profile_pic = res[1] if res else ''

    c.execute("SELECT id, title, payment_method FROM tasks WHERE status = 'OPEN'")
    open_tasks = c.fetchall()
    conn.close()

    return render_template_string(HTML_TEMPLATE, page='home', phone=phone, balance=balance, profile_pic=profile_pic, open_tasks=open_tasks, msg=msg)

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
            gen_otp = str(random.randint(1000, 9999))
            c.execute("INSERT INTO tasks (provider_phone, title, payment_method, otp) VALUES (?, ?, ?, ?)",
                        (phone, title, pay_method, gen_otp))
            conn.commit()
            msg = f"✅ Task Posted! OTP: <b style='font-size:22px; color:#e67e22;'>{gen_otp}</b> (Ye OTP kaam karne wale ko dein)"

    c.execute("SELECT balance, profile_pic FROM users WHERE phone=?", (phone,))
    res = c.fetchone()
    balance = res[0] if res else 0.0
    profile_pic = res[1] if res else ''
    conn.close()

    return render_template_string(HTML_TEMPLATE, page='kam_do', phone=phone, balance=balance, profile_pic=profile_pic, msg=msg)

@app.route('/refer', methods=['GET'])
def refer():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    phone = session.get('phone')
    conn = sqlite3.connect('sab_kamao.db')
    c = conn.cursor()

    c.execute("SELECT balance, profile_pic, referral_code FROM users WHERE phone=?", (phone,))
    user = c.fetchone()
    balance = user[0] if user else 0.0
    profile_pic = user[1] if user else ''
    ref_code = user[2] if user and user[2] else 'REF123'

    # Fetch Permanent Referral History with referred user's email/phone and timestamp
    c.execute("SELECT referred_phone, timestamp, status FROM referrals WHERE referrer_phone = ? ORDER BY id DESC", (phone,))
    refer_history = c.fetchall()
    conn.close()

    return render_template_string(HTML_TEMPLATE, page='refer', phone=phone, balance=balance, profile_pic=profile_pic, ref_code=ref_code, refer_history=refer_history)

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
                # Deduct balance and update total withdrawn
                new_total_withdrawn = total_withdrawn_so_far + amount
                c.execute('UPDATE users SET balance = balance - ?, total_withdrawn = ? WHERE phone = ?', (amount, new_total_withdrawn, phone))
                c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                            (phone, -amount, f"Withdrawal ({withdraw_type.upper()})"))
                conn.commit()

                # Check if this user was referred by someone and hit the ₹5000 milestone
                c.execute("SELECT referrer_phone, milestone_paid FROM referrals WHERE referred_phone = ?", (phone,))
                ref_record = c.fetchone()
                if ref_record and ref_record[1] == 0: # Milestone not paid yet
                    if new_total_withdrawn >= 5000:
                        referrer_phone = ref_record[0]
                        # Give ₹500 bonus to referrer automatically
                        c.execute('UPDATE users SET balance = balance + 500.0 WHERE phone = ?', (referrer_phone,))
                        c.execute("INSERT INTO transactions (phone, amount, title) VALUES (?, ?, ?)",
                                    (referrer_phone, 500.0, f"Referral Milestone Bonus (User {phone} crossed ₹5000 withdrawal)"))
                        c.execute("UPDATE referrals SET milestone_paid = 1, status = 'MILESTONE_REACHED' WHERE referred_phone = ?", (phone,))
                        conn.commit()

                send_withdrawal_email(phone, amount, withdraw_type, details_str)
                msg = f"✅ ₹{amount} Withdrawal Request Submitted!"

    c.execute("SELECT balance, profile_pic, total_withdrawn FROM users WHERE phone=?", (phone,))
    res = c.fetchone()
    balance = res[0] if res else 0.0
    profile_pic = res[1] if res else ''
    total_withdrawn = res[2] if res else 0.0
    conn.close()

    return render_template_string(HTML_TEMPLATE, page='withdraw', phone=phone, balance=balance, profile_pic=profile_pic, total_withdrawn=total_withdrawn, msg=msg)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
