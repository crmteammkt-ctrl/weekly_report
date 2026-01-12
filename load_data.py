import sqlite3
import pandas as pd
import os
import gdown
import streamlit as st

GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
DB_PATH = "thiensondb.db"

@st.cache_resource(show_spinner="⬇️ Downloading database (~500MB)...")
def get_connection():
    if not os.path.exists(DB_PATH):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, DB_PATH, quiet=False)

    # ⚠️ verify DB header (chống file html)
    with open(DB_PATH, "rb") as f:
        header = f.read(16)
        if header != b"SQLite format 3\x00":
            raise ValueError("Downloaded file is NOT a valid SQLite database")

    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(show_spinner="📦 Loading data...")
def load_data():
    conn = get_connection()
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
    return df


@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    conn = get_connection()
    df_fp = pd.read_sql("""
        SELECT Số_điện_thoại, MIN(Ngày) AS First_Date
        FROM tinhhinhbanhang
        GROUP BY Số_điện_thoại
    """, conn)
    df_fp["First_Date"] = pd.to_datetime(df_fp["First_Date"], errors="coerce")
    return df_fp
