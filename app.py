import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)

# ---------------- SECRET ----------------
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

DB_NAME = "database.db"

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

    # CREATE TABLE (base structure)
    db.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient TEXT,
        reason TEXT,
        date TEXT,
        status TEXT
    )
    """)

    # ADD MISSING COLUMNS (AUTO FIX)
    columns = [col["name"] for col in db.execute("PRAGMA table_info(visits)")]

    def add_column(name):
        if name not in columns:
            db.execute(f"ALTER TABLE visits ADD COLUMN {name} TEXT")

    add_column("patient_type")
    add_column("dob")
    add_column("work_type")
    add_column("hobbies")
    add_column("vision_goals")
    add_column("vision_insurance")
    add_column("medical_insurance")
    add_column("medical_insurance_accepted")
    add_column("vsp_essential_eye_care")

    # USERS TABLE
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
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
    data = db.execute("SELECT * FROM visits ORDER BY id DESC").fetchall()
    return render_template("visitdetails.html", data=data)

# ---------------- ADD (SAFE) ----------------
@app.route('/add', methods=['POST'])
@login_required
def add():
    try:
        db = get_db()

        # SAFE VALUES (BLANK IF EMPTY)
        patient = request.form.get('patient') or ''
        reason = request.form.get('reason') or ''
        date = request.form.get('date') or ''
        status = request.form.get('status') or ''
        patient_type = request.form.get('patient_type') or 'Existing'
        dob = request.form.get('dob') or ''
        work_type = request.form.get('work_type') or ''
        hobbies = request.form.get('hobbies') or ''
        vision_goals = request.form.get('vision_goals') or ''
        vision_insurance = request.form.get('vision_insurance') or ''
        medical_insurance = request.form.get('medical_insurance') or ''
        medical_insurance_accepted = request.form.get('medical_insurance_accepted') or ''
        vsp = request.form.get('vsp_essential_eye_care') or ''

        db.execute("""
            INSERT INTO visits (
                patient, reason, date, status, patient_type,
                dob, work_type, hobbies, vision_goals, vision_insurance,
                medical_insurance, medical_insurance_accepted, vsp_essential_eye_care
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient, reason, date, status, patient_type,
            dob, work_type, hobbies, vision_goals, vision_insurance,
            medical_insurance, medical_insance_accepted if 'medical_insance_accepted' in locals() else medical_insurance_accepted,
            vsp
        ))

        db.commit()
        return redirect('/visitdetails')

    except Exception as e:
        print("ERROR:", e)
        return f"Error saving patient: {str(e)}"

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

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    db = get_db()
    db.execute("DELETE FROM visits WHERE id=?", (id,))
    db.commit()
    return jsonify({"status": "deleted"})

# ---------------- SEARCH ----------------
@app.route('/search')
@login_required
def search():
    return render_template("search.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
