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

#Connection dùng chung
_CONN = None

#Đóng connection
def close_connection():
    """Đóng connection DuckDB hiện tại (nếu có)"""
    global _CONN
    if _CONN is not None:
        try:
            _CONN.close()
        except Exception:
            pass
        _CONN = None


# =========================
# HÀM TẢI + CONVERT DB
# =========================
def rebuild_duckdb_from_drive():
#Đảm bảo không có connection nào đang mở trong DuckDB
    close_connection()


    with st.spinner("⬇️ Đang tải DB từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, SQLITE_DB, quiet=False)

    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)
        sqlite_conn.close()

        #Ép kiểu số an toàn trước khi vào DuckDB
        numeric_cols = [
            "Tổng_Gross",
            "Tổng_Net",
            "CK_%",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        #Ghi sang DuckDB
        duck = duckdb.connect(DUCKDB_DB)
        duck.execute(f"""
            CREATE OR REPLACE TABLE {TABLE_NAME} AS
            SELECT * FROM df
        """)
        duck.close()


# =========================
# GET CONNECTION
# =========================
@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    """
    Trả về 1 connection DuckDB dùng chung, read_only.
    Lần đầu nếu chưa có file DuckDB thì tự động build từ Drive
    """
    global _CONN

    
    if not os.path.exists(DUCKDB_DB):
        rebuild_duckdb_from_drive()
    
    if _CONN is None:
        _CONN = duckdb.connect(DUCKDB_DB, read_only=True)
    return _CONN



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
    df = df.dropna(subset=["Ngày"])

    for c in ["Tổng_Gross", "Tổng_Net"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# =========================
# FIRST PURCHASE
# =========================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    con = get_connection()
    df = con.execute(f"""
        SELECT Số_điện_thoại, MIN(Ngày) AS First_Date
        FROM {TABLE_NAME}
        GROUP BY Số_điện_thoại
    """).df()

    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
