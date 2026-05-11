from flask import Flask, render_template, request, redirect, jsonify
import sqlite3

app = Flask(__name__)

DB_NAME = "database.db"

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # SAFE TABLE CREATION (expanded for your form)
    cur.execute("""
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

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route('/')
def form():
    return render_template("form.html")


# ---------------- ADD PATIENT ----------------
@app.route('/add', methods=['POST'])
def add():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
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

    conn.commit()
    conn.close()

    return redirect('/calendar')


# ---------------- CALENDAR ----------------
@app.route('/calendar')
def calendar():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM visits ORDER BY date ASC")
    data = cur.fetchall()

    conn.close()

    return render_template("calendar.html", data=data)


# ---------------- UPDATE (INLINE EDIT) ----------------
@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    data = request.get_json()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE visits
        SET
            patient=?,
            reason=?,
            date=?,
            status=?,
            dob=?,
            work_type=?,
            hobbies=?,
            vision_goals=?,
            vision_insurance=?,
            medical_insurance=?,
            medical_insurance_accepted=?,
            vsp_essential_eye_care=?
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

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})


# ---------------- DELETE ----------------
@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM visits WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "deleted"})


# ---------------- OTHER PAGES ----------------
@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")


@app.route('/search')
def search():
    return render_template("search.html")


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)