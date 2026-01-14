import os
import sqlite3
import duckdb
import pandas as pd
import numpy as np
import streamlit as st
import gdown

GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
SQLITE_DB = "thiensondb.db"
DUCKDB_DB = "marketing.duckdb"
TABLE_NAME = "tinhhinhbanhang"


# =========================
# HÀM TẢI + CONVERT DB
# =========================
def rebuild_duckdb_from_drive():
    """Download SQLite từ Drive và convert sang DuckDB. 
    Gọi được nhiều lần, kể cả khi file không đổi cũng không sao.
    """
    with st.spinner("⬇️ Đang tải DB từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        # Luôn tải đè, cho chắc
        if os.path.exists(SQLITE_DB):
            os.remove(SQLITE_DB)
        gdown.download(url, SQLITE_DB, quiet=False)

    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        # Đọc SQLite
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)
        sqlite_conn.close()

        # ---- Làm sạch các cột số / % có thể bị '' ----
        numeric_cols = ["Tổng_Gross", "Tổng_Net", "CK_%"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace("%", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .replace("", np.nan)
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ghi sang DuckDB
        duck = duckdb.connect(DUCKDB_DB)  # KHÔNG dùng read_only
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
    # Lần đầu chưa có DuckDB → build từ Drive
    if not os.path.exists(DUCKDB_DB):
        rebuild_duckdb_from_drive()

    # Không dùng read_only để cấu hình tất cả connection giống nhau
    return duckdb.connect(DUCKDB_DB)


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

    # Chuẩn hoá kiểu dữ liệu
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    df = df.dropna(subset=["Ngày"])

    for c in ["Tổng_Gross", "Tổng_Net"]:
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
