"""Selenium UI tests. Run with the app already running:
    BASE_URL=http://localhost:5000 pytest selenium_tests -v
"""
import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("BASE_URL", "http://localhost:5000")
USER = "faculty%d" % int(time.time())
ROLL = "R%d" % int(time.time())


@pytest.fixture(scope="module")
def driver():
    o = Options()
    if os.environ.get("HEADLESS", "1") == "1":
        o.add_argument("--headless=new")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--window-size=1200,900")
    d = webdriver.Chrome(options=o)
    d.get(BASE)
    yield d
    d.quit()


def fill(d, field_id, value):
    e = d.find_element(By.ID, field_id)
    e.clear()
    e.send_keys(value)


def click_and_expect(d, label, text):
    d.find_element(By.XPATH, "//button[normalize-space()='%s']" % label).click()
    WebDriverWait(d, 10).until(lambda x: text in x.find_element(By.ID, "o").text)


def test_TC00_page_loads(driver):
    assert "Student Attendance" in driver.title


def test_TC01_faculty_login(driver):
    fill(driver, "u", USER)
    fill(driver, "p", "secret123")
    click_and_expect(driver, "Register", "Faculty registered")
    click_and_expect(driver, "Login", "Login successful")


def test_TC02_add_student(driver):
    fill(driver, "r", ROLL)
    fill(driver, "n", "Asha")
    fill(driver, "d", "CSE")
    click_and_expect(driver, "Add", "Student added")


def test_TC03_mark_attendance(driver):
    driver.execute_script("document.getElementById('ad').value='2026-01-01'")
    click_and_expect(driver, "Mark/Update", "Attendance recorded")


def test_TC04_update_attendance(driver):
    driver.execute_script("document.getElementById('as').value='A'")
    click_and_expect(driver, "Mark/Update", "Attendance updated")


def test_TC05_attendance_percentage(driver):
    click_and_expect(driver, "View %", "attendance_percentage")
    assert "0" in driver.find_element(By.ID, "o").text


def test_TC06_enter_marks(driver):
    fill(driver, "s", "Maths")
    fill(driver, "m", "80")
    click_and_expect(driver, "Save", "Marks saved")


def test_TC07_generate_report(driver):
    click_and_expect(driver, "Report", "marks_percentage")
    assert "Asha" in driver.find_element(By.ID, "o").text
