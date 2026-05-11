import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# ---------------- SECRET ----------------
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

app.config.update(
    SESSION_COOKIE_SECURE=True,
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

    # AUTO ADMIN USER
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
            return redirect("/dashboard")   # ✅ FIXED ENTRY POINT

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

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

# ---------------- CALENDAR ----------------
@app.route('/calendar')
@login_required
def calendar():
    db = get_db()
    data = db.execute("SELECT * FROM visits ORDER BY date DESC").fetchall()
    return render_template("calendar.html", data=data)

# ---------------- ADD ----------------
@app.route('/add', methods=['POST'])
@login_required
def add():
    db = get_db()

    db.execute("""
        INSERT INTO visits (
            patient, reason, date,
            status, dob, work_type, hobbies,
            vision_goals, vision_insurance,
            medical_insurance, medical_insurance_accepted,
            vsp_essential_eye_care
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request.form.get('patient'),
        request.form.get('reason'),
        request.form.get('date'),
        request.form.get('status'),
        request.form.get('dob'),
        request.form.get('work_type'),
        request.form.get('hobbies'),
        request.form.get('vision_goals'),
        request.form.get('vision_insurance'),
        request.form.get('medical_insurance'),
        request.form.get('medical_insurance_accepted'),
        request.form.get('vsp_essential_eye_care')
    ))

    db.commit()
    return redirect('/calendar')

# ---------------- UPDATE ----------------
@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update(id):
    data = request.get_json()
    db = get_db()

    db.execute("""
        UPDATE visits
        SET patient=?, reason=?, date=?, status=?, dob=?,
            work_type=?, hobbies=?, vision_goals=?, vision_insurance=?,
            medical_insurance=?, medical_insurance_accepted=?, vsp_essential_eye_care=?
        WHERE id=?
    """, (
        data.get('patient'),
        data.get('reason'),
        data.get('date'),
        data.get('status'),
        data.get('dob'),
        data.get('work_type'),
        data.get('hobbies'),
        data.get('vision_goals'),
        data.get('vision_insurance'),
        data.get('medical_insurance'),
        data.get('medical_insurance_accepted'),
        data.get('vsp_essential_eye_care'),
        id
    ))

    db.commit()
    return jsonify({"status": "success"})

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
