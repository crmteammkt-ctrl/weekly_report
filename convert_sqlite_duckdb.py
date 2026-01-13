import os
import sqlite3
import duckdb
import pandas as pd
import gdown

# =========================
# CONFIG
# =========================
GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
SQLITE_DB = "thiensondb.db"
DUCKDB_DB = "marketing.duckdb"
TABLE_NAME = "tinhhinhbanhang"

# =========================
# STEP 1: DOWNLOAD SQLITE (1 LẦN)
# =========================
if not os.path.exists(SQLITE_DB):
    print("⬇️ Downloading SQLite DB from Google Drive...")
    url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
    gdown.download(url, SQLITE_DB, quiet=False)

# =========================
# STEP 2: CONVERT SQLITE → DUCKDB
# =========================
print("🔄 Connecting SQLite...")
sqlite_conn = sqlite3.connect(SQLITE_DB)

print("🦆 Creating DuckDB...")
duck = duckdb.connect(DUCKDB_DB)

print("📥 Reading data from SQLite...")
df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)

print("📤 Writing to DuckDB...")
duck.execute(f"""
    CREATE OR REPLACE TABLE {TABLE_NAME} AS
    SELECT * FROM df
""")

sqlite_conn.close()
duck.close()

print("✅ CONVERT DONE: marketing.duckdb created")
