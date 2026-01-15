import os
import sqlite3
import duckdb
import pandas as pd
import numpy as np
import streamlit as st
import gdown

# =========================
# CẤU HÌNH
# =========================
GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
SQLITE_DB = "thiensondb.db"      # file tải từ Drive về
DUCKDB_DB = "marketing.duckdb"   # file DuckDB dùng cho báo cáo
TABLE_NAME = "tinhhinhbanhang"   # tên bảng trong DB


# =========================
# HÀM TẢI + CONVERT DB
# =========================
def rebuild_duckdb_from_drive():
    """
    Download SQLite từ Google Drive (~500MB) và convert sang DuckDB.
    Gọi lại nhiều lần cũng không sao (dùng cho nút 'Cập nhật dữ liệu').
    """
    # 1. Tải SQLite từ Google Drive
    with st.spinner("⬇️ Đang tải DB từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"

        # Nếu đã có file cũ thì xóa để đảm bảo không lỗi
        if os.path.exists(SQLITE_DB):
            os.remove(SQLITE_DB)

        # Tải về
        gdown.download(url, SQLITE_DB, quiet=False)

    # 2. Đọc từ SQLite và ghi sang DuckDB
    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        # Đọc SQLite
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)
        sqlite_conn.close()

        # Làm sạch các cột số / % có thể bị để dạng text
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
# GET / CLOSE CONNECTION
# =========================
@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    """
    Trả về 1 connection DuckDB được cache.
    Nếu file DuckDB chưa tồn tại thì tự động build từ Google Drive.
    """
    if not os.path.exists(DUCKDB_DB):
        rebuild_duckdb_from_drive()

    con = duckdb.connect(DUCKDB_DB)  # mặc định read_write
    return con


def close_connection():
    """
    Đóng connection DuckDB đang được cache.
    Dùng khi bấm nút 'Cập nhật dữ liệu' rồi sau đó clear cache.
    """
    try:
        con = get_connection()
        con.close()
    except Exception:
        # Nếu vì lý do gì đó không close được thì bỏ qua, không để app crash
        pass


# =========================
# LOAD MAIN DATA
# =========================
@st.cache_data(show_spinner="📦 Loading data...")
def load_data():
    """
    Đọc dữ liệu chính từ DuckDB, chuẩn hóa kiểu dữ liệu.
    """
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

    # Chuẩn hoá kiểu dữ liệu Ngày
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    df = df.dropna(subset=["Ngày"])

    # Chuẩn hoá Gross/Net
    for c in ["Tổng_Gross", "Tổng_Net"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# =========================
# FIRST PURCHASE
# =========================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    """
    Lấy ngày mua đầu tiên của từng SĐT từ toàn bộ bảng.
    """
    con = get_connection()
    df = con.execute(f"""
        SELECT Số_điện_thoại, MIN(Ngày) AS First_Date
        FROM {TABLE_NAME}
        GROUP BY Số_điện_thoại
    """).df()

    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
