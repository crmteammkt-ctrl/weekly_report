import os
import sqlite3
import duckdb
import pandas as pd
import streamlit as st
import gdown

GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
SQLITE_DB = "thiensondb.db"
DUCKDB_DB = "marketing.duckdb"
TABLE_NAME = "tinhhinhbanhang"


# =========================
# HÀM REBUILD DUCKDB TỪ GOOGLE DRIVE
# (CHỈ GỌI KHI BẠN MUỐN CẬP NHẬT)
# =========================
def rebuild_duckdb_from_drive():
    """Tải SQLite từ Drive và convert sang DuckDB."""
    with st.spinner("⬇️ Đang tải database mới từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, SQLITE_DB, quiet=False)

    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)
        sqlite_conn.close()

        duck = duckdb.connect(DUCKDB_DB)
        duck.execute(f"""
            CREATE OR REPLACE TABLE {TABLE_NAME} AS
            SELECT * FROM df
        """)
        duck.close()


# =========================
# GET CONNECTION (DUCKDB)
# =========================
@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    # Lần đầu mà chưa có DuckDB thì tự tạo
    if not os.path.exists(DUCKDB_DB):
        rebuild_duckdb_from_drive()

    return duckdb.connect(DUCKDB_DB, read_only=True)



# =========================
# GET CONNECTION (DUCKDB)
# =========================
@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    ensure_duckdb_exists()
    # read_only cho an toàn
    return duckdb.connect(DUCKDB_DB, read_only=True)


# =========================
# LOAD MAIN DATA
# =========================
@st.cache_data(show_spinner="📦 Loading data...")
def load_data():
    con = get_connection()

    df = con.execute(f"""
        SELECT
            Ngày,
            LoaiCT,
            Brand,
            Region,
            Tỉnh_TP,
            Điểm_mua_hàng,
            Nhóm_hàng,
            Tên_hàng,
            Số_CT,
            tên_KH,
            Kiểm_tra_tên,
            Số_điện_thoại,
            Trạng_thái_số_điện_thoại,
            Tổng_Gross,
            Tổng_Net
        FROM {TABLE_NAME}
    """).df()

    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")

    num_cols = ["Tổng_Gross", "Tổng_Net"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["Ngày"])
    return df


# =========================
# FIRST PURCHASE
# =========================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    con = get_connection()

    df = con.execute(f"""
        SELECT
            Số_điện_thoại,
            MIN(Ngày) AS First_Date
        FROM {TABLE_NAME}
        GROUP BY Số_điện_thoại
    """).df()

    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
