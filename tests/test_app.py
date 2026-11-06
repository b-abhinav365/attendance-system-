import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from app import create_app

@pytest.fixture
def c(tmp_path):
    app = create_app(str(tmp_path / "t.db"))
    cl = app.test_client()
    cl.post("/api/faculty/register", json={"username": "f1", "password": "pw"})
    return cl

def login(c):
    return c.post("/api/login", json={"username": "f1", "password": "pw"})

def setup_student(c):
    login(c)
    c.post("/api/students", json={"roll_no": "S1", "name": "Asha", "department": "CSE"})

def test_TC01_faculty_login(c):
    r = login(c)
    assert r.status_code == 200 and r.json["message"] == "Login successful"

def test_TC01b_bad_login(c):
    assert c.post("/api/login", json={"username": "f1", "password": "x"}).status_code == 401

def test_TC02_add_student(c):
    login(c)
    r = c.post("/api/students", json={"roll_no": "S1", "name": "Asha"})
    assert r.status_code == 201 and r.json["message"] == "Student added"

def test_TC03_mark_attendance(c):
    setup_student(c)
    r = c.post("/api/attendance", json={"roll_no": "S1", "date": "2026-01-01", "status": "P"})
    assert r.json["message"] == "Attendance recorded"

def test_TC04_update_attendance(c):
    setup_student(c)
    c.post("/api/attendance", json={"roll_no": "S1", "date": "2026-01-01", "status": "A"})
    r = c.post("/api/attendance", json={"roll_no": "S1", "date": "2026-01-01", "status": "P"})
    assert r.json["message"] == "Attendance updated"

def test_TC05_attendance_percentage(c):
    setup_student(c)
    for d, s in [("2026-01-01", "P"), ("2026-01-02", "P"), ("2026-01-03", "P"), ("2026-01-04", "A")]:
        c.post("/api/attendance", json={"roll_no": "S1", "date": d, "status": s})
    assert c.get("/api/attendance/S1").json["attendance_percentage"] == 75.0

def test_TC06_enter_marks(c):
    setup_student(c)
    r = c.post("/api/marks", json={"roll_no": "S1", "subject": "Maths", "marks": 45, "max_marks": 50})
    assert r.json["message"] == "Marks saved"

def test_TC07_generate_report(c):
    setup_student(c)
    c.post("/api/attendance", json={"roll_no": "S1", "date": "2026-01-01", "status": "P"})
    c.post("/api/marks", json={"roll_no": "S1", "subject": "Maths", "marks": 80})
    r = c.get("/api/report/S1")
    assert r.status_code == 200 and r.json["marks_percentage"] == 80.0 and r.json["remark"] == "Good"

def test_unauthenticated_blocked(c):
    assert c.get("/api/students").status_code == 401
