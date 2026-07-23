import os
import json
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ----------------------------
# Helper
# ----------------------------
def clean(value):
    if value is None or value == "":
        return None

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    return value


# ----------------------------
# Load AIS EMPMAS
# ../empmas_synchronize/ais_empmas.json
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EMPMAS_FILE = os.path.join(
    BASE_DIR,
    "..",
    "empmas_synchronize",
    "ais_empmas.json"
)

SOURCE_DB = {
    "host": os.getenv("SOURCE_DB_HOST"),
    "user": os.getenv("SOURCE_DB_USER"),
    "password": os.getenv("SOURCE_DB_PASSWORD"),
    "database": os.getenv("SOURCE_DB_NAME"),
    "port": int(os.getenv("SOURCE_DB_PORT", 3306)),
}


with open(EMPMAS_FILE, "r", encoding="utf-8") as f:
    empmas = json.load(f)

# key = (empno, compy)
# value = position
emp_map = {
    (
        clean(emp.get("empno")),
        clean(emp.get("compy"))
    ): clean(emp.get("position"))
    for emp in empmas
}

# ----------------------------
# MySQL connection
# ----------------------------
conn = mysql.connector.connect(**SOURCE_DB)

cursor = conn.cursor(dictionary=True)

cursor.execute("""
    SELECT *
    FROM members
    WHERE act = 1
""")

members = cursor.fetchall()

result = []

for member in members:
    email = clean(member.get("member_email"))

    # Skip if no email
    if not email:
        continue

    # Detect user type
    user_type = "dealer" if "dealer" in email.lower() else "user"

    # Clean escaped slash in password
    password = member.get("member_password")
    if password:
        password = password.replace("\\/", "/")

    # Default company = PTB if empty
    company = clean(member.get("compny")) or "PTB"

    employee_id = clean(member.get("empid"))

    # Lookup position from AIS EMPMAS
    position_code = emp_map.get((employee_id, company))

    transformed = {
        "member_id": clean(member.get("member_id")),
        "employee_id": employee_id,
        "username": clean(member.get("user_id")),
        "email": email,
        "full_name": clean(member.get("member_name")),
        "password": clean(password),
        "position_code": position_code,
        "dept_code": clean(member.get("dept")),
        "brc_code": clean(member.get("brc")),
        "client_token": None,
        "company": company,
        "user_type": user_type,
        "is_user_ais": "1",
        "active": clean(member.get("act")),
        "created_by": None,
        "last_login_at": None,
        "last_logout_at": None,
        "email_verified_at": None,
        "remember_token": None,
        "created_at": clean(member.get("date_create")),
        "updated_at": clean(member.get("date_modif")),
    }

    result.append(transformed)

with open("all_user.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4, ensure_ascii=False)

cursor.close()
conn.close()

print(f"Done! Exported {len(result)} users.")