import os
import json
import mysql.connector
from dotenv import load_dotenv

load_dotenv()
# ==========================
# CONFIGURATION
# ==========================

SOURCE_DB = {
    "host": os.getenv("SOURCE_DB_HOST"),
    "user": os.getenv("SOURCE_DB_USER"),
    "password": os.getenv("SOURCE_DB_PASSWORD"),
    "database": os.getenv("SOURCE_DB_NAME"),
    "port": int(os.getenv("SOURCE_DB_PORT", 3306)),
}

TARGET_DB = {
    "host": os.getenv("TARGET_DB_HOST"),
    "user": os.getenv("TARGET_DB_USER"),
    "password": os.getenv("TARGET_DB_PASSWORD"),
    "database": os.getenv("TARGET_DB_NAME"),
    "port": int(os.getenv("TARGET_DB_PORT", 3306)),
}

TABLE = "ais_empmas"


def normalize_value(column, value):
    # Kolom yang tidak boleh NULL
    NOT_NULL_TEXT_COLUMNS = ["remark"]

    if column in NOT_NULL_TEXT_COLUMNS and value is None:
        return ""

    return value

# ==========================
# MYSQL CONNECTION
# ==========================
src_conn = mysql.connector.connect(**SOURCE_DB)
dst_conn = mysql.connector.connect(**TARGET_DB)

src = src_conn.cursor(dictionary=True)
dst = dst_conn.cursor(dictionary=True)

print("Connected.")

# ==========================
# READ ALL SOURCE DATA
# ==========================

src.execute(f"SELECT * FROM {TABLE}")
source_rows = src.fetchall()

print(f"Source rows : {len(source_rows)}")

if not source_rows:
    print("No data.")
    exit()
    
    
# ==========================
# SAVE SOURCE TO JSON
# ==========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, f"{TABLE}.json")

with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(
        source_rows,
        f,
        ensure_ascii=False,
        indent=4,
        default=str  # Handles datetime/date objects if any
    )

print(f"JSON exported: {JSON_FILE}")

# ==========================
# GET COLUMNS
# ==========================

columns = list(source_rows[0].keys())

# columns except key
update_columns = [
    c for c in columns
    if c not in ("empno", "compy")
]

# ==========================
# BUILD SQL
# ==========================

insert_sql = f"""
INSERT INTO `{TABLE}`
({','.join(f'`{c}`' for c in columns)})
VALUES
({','.join(['%s'] * len(columns))})
"""

update_sql = f"""
UPDATE `{TABLE}`
SET
{','.join([f"`{c}`=%s" for c in update_columns])}
WHERE `empno`=%s
AND `compy`=%s
"""

exist_sql = f"""
SELECT 1
FROM `{TABLE}`
WHERE `empno`=%s
AND `compy`=%s
LIMIT 1
"""

delete_sql = f"""
DELETE FROM `{TABLE}`
WHERE `empno`=%s
AND `compy`=%s
"""

# ==========================
# UPSERT
# ==========================

source_keys = set()

inserted = 0
updated = 0

for row in source_rows:

    key = (row["empno"], row["compy"])
    source_keys.add(key)

    dst.execute(exist_sql, key)

    exists = dst.fetchone()

    if exists:

        values = [
            normalize_value(c, row[c])
            for c in update_columns
        ]

        values.extend(key)

        dst.execute(update_sql, values)
        updated += 1

    else:

        values = tuple(
            normalize_value(c, row[c])
            for c in columns
        )

        dst.execute(insert_sql, values)
        inserted += 1

# ==========================
# DELETE REMOVED ROWS
# ==========================

dst.execute(f"SELECT empno, compy FROM {TABLE}")
target_rows = dst.fetchall()

deleted = 0

for r in target_rows:

    key = (r["empno"], r["compy"])

    if key not in source_keys:

        dst.execute(delete_sql, key)
        deleted += 1

# ==========================
# COMMIT
# ==========================

dst_conn.commit()

print("==========================")
print("Synchronization Complete")
print("==========================")
print(f"Inserted : {inserted}")
print(f"Updated  : {updated}")
print(f"Deleted  : {deleted}")

src.close()
dst.close()

src_conn.close()
dst_conn.close()