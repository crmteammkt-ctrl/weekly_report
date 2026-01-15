import os
import sqlite3   # vẫn được giữ, nhưng thực ra không còn dùng nhiều
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
# HÀM TẢI + CONVERT DB (NEW)
# =========================
def rebuild_duckdb_from_drive():
    """
    Download SQLite từ Drive và convert sang DuckDB mà KHÔNG dùng pandas,
    để tránh tốn RAM trên Streamlit Cloud.
    """
    # 1. Tải SQLite
    with st.spinner("⬇️ Đang tải DB từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"

        if os.path.exists(SQLITE_DB):
            os.remove(SQLITE_DB)

        gdown.download(url, SQLITE_DB, quiet=False)

    # 2. Convert SQLite -> DuckDB bằng ATTACH, không qua pandas
    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        # nếu có file DuckDB cũ thì xóa
        if os.path.exists(DUCKDB_DB):
            os.remove(DUCKDB_DB)

        duck = duckdb.connect(DUCKDB_DB)

        # ATTACH SQLite DB vào DuckDB
        duck.execute(f"ATTACH '{SQLITE_DB}' AS sqlite_db (TYPE sqlite)")

        # Tạo bảng trong DuckDB từ bảng SQLite
        duck.execute(f"""
            CREATE TABLE {TABLE_NAME} AS
            SELECT * FROM sqlite_db.{TABLE_NAME};
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
