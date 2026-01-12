import sqlite3
import pandas as pd
import os
import gdown
import streamlit as st

# -------------------------------
# Cấu hình
# -------------------------------
GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
DB_PATH = "thiensondb.db"

# -------------------------------
# Tạo connection đến DB
# -------------------------------
@st.cache_resource(show_spinner="⬇️ Downloading database (~500MB)...")
def get_connection():
    # 1️⃣ Download DB nếu chưa có
    if not os.path.exists(DB_PATH):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, DB_PATH, quiet=False)

    # 2️⃣ Kiểm tra header DB (để tránh file html)
    with open(DB_PATH, "rb") as f:
        header = f.read(16)
        if header != b"SQLite format 3\x00":
            raise ValueError(
                f"File {DB_PATH} tải về không phải SQLite database. Có thể link Drive sai hoặc bị giới hạn tải về."
            )

    # 3️⃣ Tạo kết nối SQLite
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

# -------------------------------
# Load toàn bộ dữ liệu
# -------------------------------
@st.cache_data(show_spinner="📦 Loading data...")
def load_data():
    conn = get_connection()
    try:
        df = pd.read_sql("""
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
            FROM tinhhinhbanhang
        """, conn)
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    finally:
        conn.close()
    return df

# -------------------------------
# Tính ngày mua đầu tiên của mỗi khách hàng
# -------------------------------
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    conn = get_connection()
    try:
        df_fp = pd.read_sql("""
            SELECT Số_điện_thoại, MIN(Ngày) AS First_Date
            FROM tinhhinhbanhang
            GROUP BY Số_điện_thoại
        """, conn)
        df_fp["First_Date"] = pd.to_datetime(df_fp["First_Date"], errors="coerce")
    finally:
        conn.close()
    return df_fp
