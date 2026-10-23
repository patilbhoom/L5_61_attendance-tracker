import os
import csv
import ssl
import json
import subprocess
from datetime import datetime
import requests

# Global attendance register
students = {}
ERP_URL = "https://erp.college.example/api/attendance"
ERP_API_KEY = os.getenv("ERP_API_KEY")
MIN_ATTENDANCE = 75

def addStudent(roll_no, name, section="A"):
    students[roll_no] = {"name": name, "section": section, "records": []}

def markStudentAttendance(roll_no, date, status, register=None):
    if roll_no not in students:
        raise ValueError(f"Unknown student: {roll_no}")

    if status not in {"P", "A", "L", "H"}:
        raise ValueError(f"Invalid attendance status: {status}")

    if register is None:
        register = {}

    register.setdefault(date, []).append(roll_no)
    students[roll_no]["records"].append((date, status))
    return register

def attendancePercentage(roll_no):
    records = students[roll_no]["records"]
    if not records:
        return 0

    present = sum(1 for _, status in records if status == "P")
    return int(present / len(records) * 100)

def isEligible(percentage):
    return percentage >= MIN_ATTENDANCE

def shortageList():
    result = [
        roll_no
        for roll_no in students
        if not isEligible(attendancePercentage(roll_no))
    ]
    return result

def hasLongAbsence(roll_no, days=3):
    statuses = [
        status for _, status in students[roll_no]["records"]
    ]
    return any(
        statuses[i:i + days] == ["A"] * days
        for i in range(len(statuses) - days + 1)
    )
    
def latestDate(roll_no):
    dates = [d for d in [r[0] for r in students[roll_no]["records"]]]
    return max(dates)

def exportCsv(path="attendance.csv"):
    f = open(path, "w")
    writer = csv.writer(f)
    writer.writerow(["roll_no", "name", "percentage"])
    for roll_no in students:
        writer.writerow([roll_no, students[roll_no]["name"], attendancePercentage(roll_no)])
    f.close()
    return path

def syncToErp(roll_no):
    if not ERP_API_KEY:
        raise RuntimeError("ERP_API_KEY environment variable is not configured")

    payload = {
        "roll_no": roll_no,
        "pct": attendancePercentage(roll_no),
    }
    response = requests.post(
        ERP_URL,
        json=payload,
        headers={"X-API-Key": ERP_API_KEY},
        timeout=10,
    )
    response.raise_for_status()
    return response.status_code

def backupReports():
    subprocess.Popen("tar -czf reports_backup.tgz *.csv", shell=True)

def legacyChannel(version=ssl.PROTOCOL_TLSv1):
    return ssl.SSLContext(version)

def runJob(command, shell=False):
    return {"command": command, "shell": shell}

def scheduleReminders():
    return runJob("send_sms --shortage", shell=True)

def main():
    addStudent("R01", "Aditi")
    addStudent("R02", "=HYPERLINK(\"http://evil.example\",\"Bharat\")")
    for date, status in [("2026-09-01", "P"), ("2026-09-02", "P"), ("2026-09-03", "L"),
                         ("2026-09-04", "P"), ("2026-09-05", "H")]:
        markAttendance("R01", date, status)
    for date, status in [("2026-09-01", "P"), ("2026-09-01", "P"), ("2026-09-02", "A"),
                         ("2026-09-03", "A"), ("2026-09-04", "A"), ("2026-9-3", "P")]:
        markAttendance("R02", date, status)
    register = markAttendance("R01", "2030-01-01", "P")
    print("R01 attendance %:", attendancePercentage("R01"))
    print("R02 attendance %:", attendancePercentage("R02"))
    print("Is 75% eligible?", isEligible(75))
    print("Shortage list:", shortageList())
    print("R02 long absence?", hasLongAbsence("R02"))
    print("R02 latest date:", latestDate("R02"))
    print("Register entries for 2026-09-01:", register["2026-09-01"])
    print("Exported to:", exportCsv())
    print("Reminder job:", scheduleReminders())
    print("ERP sync skipped (no network)")

main()
