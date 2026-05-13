import os
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# ---------------- SECRET ----------------
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

DB_NAME = "database.db"

# ---------------- SHAREPOINT SYNC FOLDER ----------------
SYNC_FOLDER = r"C:\Users\YourName\EyeGenVisionTeam\Documents\Operations\Patient Form Consolidated Data\incoming_data"

# ---------------- SAFE CLEAN FUNCTION ----------------
def clean(value):
    return "" if value is None else value

# ---------------- DB ----------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db:
        db.close()

# ---------------- INIT DB ----------------
def init_db():
    db = get_db()

    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient TEXT,
        reason TEXT,
        date TEXT,
        status TEXT,
        patient_type TEXT DEFAULT 'Existing',
        dob TEXT,
        work_type TEXT,
        hobbies TEXT,
        vision_goals TEXT,
        vision_insurance TEXT,
        medical_insurance TEXT,
        medical_insurance_accepted TEXT,
        vsp_essential_eye_care TEXT
    )
    """)

    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")

    existing = db.execute(
        "SELECT * FROM users WHERE username=?",
        (admin_user,)
    ).fetchone()

    if not existing:
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (admin_user, generate_password_hash(admin_pass))
        )

    db.commit()

with app.app_context():
    init_db()

# ---------------- SHAREPOINT JSON EXPORT ----------------
def save_to_sharepoint_folder(data, record_id):
    try:
        if not os.path.exists(SYNC_FOLDER):
            os.makedirs(SYNC_FOLDER)

        filename = f"patient_{record_id}_{int(datetime.now().timestamp())}.json"
        filepath = os.path.join(SYNC_FOLDER, filename)

        payload = {
            "id": record_id,
            "patient": clean(data.get("patient")),
            "dob": clean(data.get("dob")),
            "status": clean(data.get("status")),
            "work_type": clean(data.get("work_type")),
            "hobbies": clean(data.get("hobbies")),
            "vision_goals": clean(data.get("vision_goals")),
            "vision_insurance": clean(data.get("vision_insurance")),
            "medical_insurance": clean(data.get("medical_insurance")),
            "medical_insurance_accepted": clean(data.get("medical_insurance_accepted")),
            "vsp_essential_eye_care": clean(data.get("vsp_essential_eye_care")),
            "reason": clean(data.get("reason")),
            "date": clean(data.get("date"))
        }

        with open(filepath, "w") as f:
            json.dump(payload, f)

        print("Saved JSON:", filepath)

    except Exception as e:
        print("Error saving JSON:", e)

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            return redirect("/visitdetails")

        return "Invalid login"

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- ROOT ----------------
@app.route('/')
def root():
    return redirect('/login')

# ---------------- FORM ----------------
@app.route('/form')
@login_required
def form():
    return render_template("form.html")

# ---------------- VISIT DETAILS ----------------
@app.route('/visitdetails')
@login_required
def visitdetails():
    db = get_db()
    data = db.execute("SELECT * FROM visits ORDER BY date DESC").fetchall()
    return render_template("visitdetails.html", data=data)

# ---------------- ADD (FIXED) ----------------
@app.route('/add', methods=['POST'])
@login_required
def add():
    db = get_db()

    db.execute("""
        INSERT INTO visits (
            patient, reason, date,
            status, patient_type,
            dob, work_type, hobbies,
            vision_goals, vision_insurance,
            medical_insurance, medical_insurance_accepted,
            vsp_essential_eye_care
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clean(request.form.get('patient')),
        clean(request.form.get('reason')),
        clean(request.form.get('date')),
        clean(request.form.get('status')),
        clean(request.form.get('patient_type', 'Existing')),
        clean(request.form.get('dob')),
        clean(request.form.get('work_type')),
        clean(request.form.get('hobbies')),
        clean(request.form.get('vision_goals')),
        clean(request.form.get('vision_insurance')),
        clean(request.form.get('medical_insurance')),
        clean(request.form.get('medical_insurance_accepted')),
        clean(request.form.get('vsp_essential_eye_care'))
    ))

    db.commit()

    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    save_to_sharepoint_folder(request.form, new_id)

    return redirect('/visitdetails')

# ---------------- UPDATE (FIXED) ----------------
@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update(id):
    data = request.get_json() or {}
    db = get_db()

    db.execute("""
        UPDATE visits
        SET patient=?, reason=?, date=?, status=?, dob=?,
            work_type=?, hobbies=?, vision_goals=?, vision_insurance=?,
            medical_insurance=?, medical_insurance_accepted=?, vsp_essential_eye_care=?
        WHERE id=?
    """, (
        clean(data.get('patient')),
        clean(data.get('reason')),
        clean(data.get('date')),
        clean(data.get('status')),
        clean(data.get('dob')),
        clean(data.get('work_type')),
        clean(data.get('hobbies')),
        clean(data.get('vision_goals')),
        clean(data.get('vision_insurance')),
        clean(data.get('medical_insurance')),
        clean(data.get('medical_insurance_accepted')),
        clean(data.get('vsp_essential_eye_care')),
        id
    ))

    db.commit()

    save_to_sharepoint_folder(data, id)

    return jsonify({"status": "success"})

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    db = get_db()
    db.execute("DELETE FROM visits WHERE id=?", (id,))
    db.commit()
    return jsonify({"status": "deleted"})

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    visits = db.execute("SELECT * FROM visits").fetchall()

    today = datetime.now().date()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    def safe_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except:
            return None

    def count(start_date):
        new = 0
        existing = 0

        for v in visits:
            d = safe_date(v["date"])
            if not d:
                continue

            if d >= start_date:
                if v["patient_type"] == "New":
                    new += 1
                else:
                    existing += 1

        return new, existing

    day_new, day_existing = count(today)
    week_new, week_existing = count(week_start)
    month_new, month_existing = count(month_start)
    year_new, year_existing = count(year_start)

    return render_template("dashboard.html",
        day_new=day_new,
        day_existing=day_existing,
        week_new=week_new,
        week_existing=week_existing,
        month_new=month_new,
        month_existing=month_existing,
        year_new=year_new,
        year_existing=year_existing
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
