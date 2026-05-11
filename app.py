import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, jsonify, g, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# 🔐 Secret key (SET THIS IN RENDER ENV)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# 🔐 Secure cookies
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

DB_NAME = "database.db"

# ---------------- DATABASE ----------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()

    # USERS TABLE (for login)
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # VISITS TABLE (your existing)
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

    db.commit()

with app.app_context():
    init_db()

# ---------------- AUTH DECORATOR ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

# ---------------- AUTH ROUTES ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = generate_password_hash(request.form.get('password'))

        try:
            db = get_db()
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
        except:
            return "User already exists"

        return redirect('/login')

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            return redirect('/dashboard')

        return "Invalid login"

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- HOME ----------------
@app.route('/')
def form():
    if "user" not in session:
        return redirect("/login")
    return render_template("form.html")

# ---------------- ADD PATIENT ----------------
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

# ---------------- CALENDAR ----------------
@app.route('/calendar')
@login_required
def calendar():
    db = get_db()
    data = db.execute("SELECT * FROM visits ORDER BY date ASC").fetchall()
    return render_template("calendar.html", data=data)

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

# ---------------- OTHER PAGES ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/search')
@login_required
def search():
    return render_template("search.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
