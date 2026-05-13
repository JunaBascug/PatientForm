import os
import sqlite3
import traceback
from flask import Flask, render_template, request, redirect, session, jsonify, g
from functools import wraps

app = Flask(__name__)
app.secret_key = "dev-secret-key"

DB_NAME = "database.db"

# ---------------- CLEAN ----------------
def clean(v):
    return "" if v is None else str(v)

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

# ---------------- AUTO FIX SCHEMA ----------------
def migrate_db():
    db = get_db()

    db.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient TEXT,
        dob TEXT,
        status TEXT,
        work_type TEXT,
        hobbies TEXT,
        vision_goals TEXT,
        vision_insurance TEXT,
        medical_insurance TEXT,
        medical_insurance_accepted TEXT,
        vsp TEXT,
        reason TEXT,
        date TEXT
    )
    """)

    cols = [c[1] for c in db.execute("PRAGMA table_info(visits)")]

    # 🔥 ADD MISSING COLUMNS SAFELY
    required_columns = {
        "patient": "TEXT",
        "dob": "TEXT",
        "status": "TEXT",
        "work_type": "TEXT",
        "hobbies": "TEXT",
        "vision_goals": "TEXT",
        "vision_insurance": "TEXT",
        "medical_insurance": "TEXT",
        "medical_insurance_accepted": "TEXT",
        "vsp": "TEXT",
        "reason": "TEXT",
        "date": "TEXT"
    }

    for col, col_type in required_columns.items():
        if col not in cols:
            print(f"Adding missing column: {col}")
            db.execute(f"ALTER TABLE visits ADD COLUMN {col} {col_type}")

    db.commit()

with app.app_context():
    migrate_db()

# ---------------- ROUTES ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session["user"] = request.form.get("username")
        return redirect("/visitdetails")
    return render_template("login.html")

@app.route('/')
def root():
    return redirect('/login')

@app.route('/form')
@login_required
def form():
    return render_template("form.html")

@app.route('/visitdetails')
@login_required
def visitdetails():
    db = get_db()
    data = db.execute("SELECT * FROM visits ORDER BY id DESC").fetchall()
    return render_template("visitdetails.html", data=data)

# ---------------- ADD ----------------
@app.route('/add', methods=['POST'])
@login_required
def add():
    try:
        db = get_db()

        db.execute("""
            INSERT INTO visits (
                patient, dob, status,
                work_type, hobbies,
                vision_goals, vision_insurance,
                medical_insurance, medical_insurance_accepted,
                vsp, reason, date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            clean(request.form.get('patient')),
            clean(request.form.get('dob')),
            clean(request.form.get('status')),
            clean(request.form.get('work_type')),
            clean(request.form.get('hobbies')),
            clean(request.form.get('vision_goals')),
            clean(request.form.get('vision_insurance')),
            clean(request.form.get('medical_insurance')),
            clean(request.form.get('medical_insurance_accepted')),
            clean(request.form.get('vsp')),
            clean(request.form.get('reason')),
            clean(request.form.get('date'))
        ))

        db.commit()
        return redirect('/visitdetails')

    except Exception as e:
        print("ADD ERROR:")
        traceback.print_exc()
        return f"Server Error: {str(e)}", 500

# ---------------- UPDATE ----------------
@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update(id):
    try:
        data = request.get_json() or {}
        db = get_db()

        db.execute("""
            UPDATE visits
            SET patient=?, dob=?, status=?,
                work_type=?, hobbies=?,
                vision_goals=?, vision_insurance=?,
                medical_insurance=?, medical_insurance_accepted=?,
                vsp=?, reason=?, date=?
            WHERE id=?
        """, (
            clean(data.get('patient')),
            clean(data.get('dob')),
            clean(data.get('status')),
            clean(data.get('work_type')),
            clean(data.get('hobbies')),
            clean(data.get('vision_goals')),
            clean(data.get('vision_insurance')),
            clean(data.get('medical_insurance')),
            clean(data.get('medical_insurance_accepted')),
            clean(data.get('vsp')),
            clean(data.get('reason')),
            clean(data.get('date')),
            id
        ))

        db.commit()
        return jsonify({"status": "success"})

    except Exception as e:
        print("UPDATE ERROR:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    db = get_db()
    db.execute("DELETE FROM visits WHERE id=?", (id,))
    db.commit()
    return jsonify({"status": "deleted"})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
