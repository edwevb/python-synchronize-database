import os
import json
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

JSON_FILE = os.path.join(
    BASE_DIR,
    "..",
    "members_to_json",
    "all_user.json"
)

TARGET_DB = {
    "host": os.getenv("TARGET_DB_HOST"),
    "user": os.getenv("TARGET_DB_USER"),
    "password": os.getenv("TARGET_DB_PASSWORD"),
    "database": os.getenv("TARGET_DB_NAME"),
    "port": int(os.getenv("TARGET_DB_PORT", 5432)),
}

with open(JSON_FILE, "r", encoding="utf-8") as f:
    users = json.load(f)

# PostgreSQL connection
conn = psycopg2.connect(**TARGET_DB)

cur = conn.cursor()

cur.execute("""
    SELECT setval(
        pg_get_serial_sequence('pricelist.trading.users', 'id'),
        COALESCE((SELECT MAX(id) FROM pricelist.trading.users), 0) + 1,
        false
    )
""")

update_sql = """
UPDATE pricelist.trading.users
SET
    member_id = %s,
    employee_id = %s,
    username = %s,
    email = %s,
    full_name = %s,
    password = %s,
    position_code = %s,
    dept_code = %s,
    brc_code = %s,
    client_token = %s,
    company = %s,
    user_type = %s,
    is_user_ais = %s,
    active = %s,
    created_by = %s,
    last_login_at = %s,
    last_logout_at = %s,
    email_verified_at = %s,
    remember_token = %s,
    created_at = %s,
    updated_at = %s
WHERE company = %s
  AND email = %s
"""

insert_sql = """
INSERT INTO pricelist.trading.users (
    member_id,
    employee_id,
    username,
    email,
    full_name,
    password,
    position_code,
    dept_code,
    brc_code,
    client_token,
    company,
    user_type,
    is_user_ais,
    active,
    created_by,
    last_login_at,
    last_logout_at,
    email_verified_at,
    remember_token,
    created_at,
    updated_at
)
VALUES (
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s
)
"""

updated = 0
inserted = 0

for user in users:
    params = (
        user.get("member_id"),
        user.get("employee_id"),
        user.get("username"),
        user.get("email"),
        user.get("full_name"),
        user.get("password"),
        user.get("position_code"),
        user.get("dept_code"),
        user.get("brc_code"),
        user.get("client_token"),
        user.get("company"),
        user.get("user_type"),
        int(user.get("is_user_ais", 0)),
        bool(int(user.get("active", 0))),
        user.get("created_by"),
        user.get("last_login_at"),
        user.get("last_logout_at"),
        user.get("email_verified_at"),
        user.get("remember_token"),
        user.get("created_at"),
        user.get("updated_at"),
        user.get("company"),
        user.get("email"),
    )

    cur.execute(update_sql, params)

    if cur.rowcount == 0:
        cur.execute(
            insert_sql,
            (
                user.get("member_id"),
                user.get("employee_id"),
                user.get("username"),
                user.get("email"),
                user.get("full_name"),
                user.get("password"),
                user.get("position_code"),
                user.get("dept_code"),
                user.get("brc_code"),
                user.get("client_token"),
                user.get("company"),
                user.get("user_type"),
                int(user.get("is_user_ais", 0)),
                bool(int(user.get("active", 0))),
                user.get("created_by"),
                user.get("last_login_at"),
                user.get("last_logout_at"),
                user.get("email_verified_at"),
                user.get("remember_token"),
                user.get("created_at"),
                user.get("updated_at"),
            ),
        )
        inserted += 1
    else:
        updated += 1

conn.commit()
print(f"Users in JSON: {len(users)}")
print(f"Updated : {updated}")
print(f"Inserted: {inserted}")

cur.close()
conn.close()