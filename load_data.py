import sqlite3
import pandas as pd
import streamlit as st
import os
import gdown

GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
DB_PATH = "thiensondb.db"

# ==================================================
# DB CONNECTION (KHÔNG BAO GIỜ CLOSE)
# ==================================================
@st.cache_resource(show_spinner="⬇️ Downloading database (~500MB)...")
def get_connection():
    if not os.path.exists(DB_PATH):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, DB_PATH, quiet=False)

    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ==================================================
# LOAD MAIN DATA
# ==================================================
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

# ==================================================
# FIRST PURCHASE
# ==================================================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT
            Số_điện_thoại,
            MIN(Ngày) AS First_Date
        FROM tinhhinhbanhang
        GROUP BY Số_điện_thoại
    """, conn)

    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
