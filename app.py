import os, sqlite3
from functools import wraps
from flask import Flask, g, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS faculty(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS students(roll_no TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT, email TEXT);
CREATE TABLE IF NOT EXISTS attendance(roll_no TEXT, date TEXT, status TEXT CHECK(status IN ('P','A')), PRIMARY KEY(roll_no,date));
CREATE TABLE IF NOT EXISTS marks(roll_no TEXT, subject TEXT, marks REAL, max_marks REAL DEFAULT 100, PRIMARY KEY(roll_no,subject));
"""

def create_app(db_path=None):
    app = Flask(__name__, static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["DB"] = db_path or os.environ.get("DB_PATH", "attendance.db")

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close(_):
        d = g.pop("db", None)
        if d:
            d.close()

    with app.app_context():
        db().executescript(SCHEMA)

    def login_required(f):
        @wraps(f)
        def wrap(*a, **k):
            if "faculty" not in session:
                return jsonify(error="Login required"), 401
            return f(*a, **k)
        return wrap

    def student_or_404(roll):
        return db().execute("SELECT * FROM students WHERE roll_no=?", (roll,)).fetchone()

    @app.get("/")
    def index():
        return send_from_directory("static", "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    # --- Faculty ---
    @app.post("/api/faculty/register")
    def faculty_register():
        d = request.get_json(force=True)
        try:
            db().execute("INSERT INTO faculty(username,password) VALUES(?,?)",
                         (d["username"], generate_password_hash(d["password"])))
            db().commit()
        except sqlite3.IntegrityError:
            return jsonify(error="Username exists"), 409
        return jsonify(message="Faculty registered"), 201

    @app.post("/api/login")
    def login():
        d = request.get_json(force=True)
        row = db().execute("SELECT * FROM faculty WHERE username=?", (d.get("username"),)).fetchone()
        if row and check_password_hash(row["password"], d.get("password", "")):
            session["faculty"] = row["username"]
            return jsonify(message="Login successful")
        return jsonify(error="Invalid credentials"), 401

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(message="Logged out")

    # --- Students ---
    @app.post("/api/students")
    @login_required
    def add_student():
        d = request.get_json(force=True)
        try:
            db().execute("INSERT INTO students VALUES(?,?,?,?)",
                         (d["roll_no"], d["name"], d.get("department"), d.get("email")))
            db().commit()
        except sqlite3.IntegrityError:
            return jsonify(error="Student already exists"), 409
        return jsonify(message="Student added"), 201

    @app.put("/api/students/<roll>")
    @login_required
    def update_student(roll):
        if not student_or_404(roll):
            return jsonify(error="Not found"), 404
        d = request.get_json(force=True)
        db().execute("UPDATE students SET name=COALESCE(?,name), department=COALESCE(?,department), email=COALESCE(?,email) WHERE roll_no=?",
                     (d.get("name"), d.get("department"), d.get("email"), roll))
        db().commit()
        return jsonify(message="Student details updated")

    @app.get("/api/students")
    @login_required
    def list_students():
        return jsonify([dict(r) for r in db().execute("SELECT * FROM students")])

    # --- Attendance (mark + update = upsert) ---
    @app.post("/api/attendance")
    @login_required
    def mark_attendance():
        d = request.get_json(force=True)
        if d.get("status") not in ("P", "A"):
            return jsonify(error="status must be P or A"), 400
        if not student_or_404(d["roll_no"]):
            return jsonify(error="Student not found"), 404
        existed = db().execute("SELECT 1 FROM attendance WHERE roll_no=? AND date=?",
                               (d["roll_no"], d["date"])).fetchone()
        db().execute("INSERT OR REPLACE INTO attendance VALUES(?,?,?)", (d["roll_no"], d["date"], d["status"]))
        db().commit()
        return jsonify(message="Attendance updated" if existed else "Attendance recorded")

    def percentage(roll):
        r = db().execute("SELECT COUNT(*) t, SUM(status='P') p FROM attendance WHERE roll_no=?", (roll,)).fetchone()
        return round((r["p"] or 0) * 100 / r["t"], 2) if r["t"] else 0.0

    @app.get("/api/attendance/<roll>")
    @login_required
    def attendance_pct(roll):
        if not student_or_404(roll):
            return jsonify(error="Student not found"), 404
        return jsonify(roll_no=roll, attendance_percentage=percentage(roll))

    # --- Marks ---
    @app.post("/api/marks")
    @login_required
    def enter_marks():
        d = request.get_json(force=True)
        if not student_or_404(d["roll_no"]):
            return jsonify(error="Student not found"), 404
        mx = d.get("max_marks", 100)
        if not 0 <= d["marks"] <= mx:
            return jsonify(error="Invalid marks"), 400
        db().execute("INSERT OR REPLACE INTO marks VALUES(?,?,?,?)", (d["roll_no"], d["subject"], d["marks"], mx))
        db().commit()
        return jsonify(message="Marks saved")

    # --- Report ---
    @app.get("/api/report/<roll>")
    @login_required
    def report(roll):
        s = student_or_404(roll)
        if not s:
            return jsonify(error="Student not found"), 404
        m = [dict(r) for r in db().execute("SELECT subject,marks,max_marks FROM marks WHERE roll_no=?", (roll,))]
        tot, mx = sum(x["marks"] for x in m), sum(x["max_marks"] for x in m)
        pct = round(tot * 100 / mx, 2) if mx else 0.0
        att = percentage(roll)
        remark = "Good" if pct >= 60 and att >= 75 else "Needs improvement"
        if att < 75:
            remark += " - attendance shortage"
        return jsonify(student=dict(s), attendance_percentage=att, marks=m,
                       total=tot, max_total=mx, marks_percentage=pct, remark=remark)

    return app

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
