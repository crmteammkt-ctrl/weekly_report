# load_data.py
import sqlite3
import pandas as pd
import os
import requests
import streamlit as st

# -------------------------
# Cấu hình file DB
# -------------------------
GOOGLE_DRIVE_FILE_ID = '1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH'
DB_PATH = "thiensondb.db"

# -------------------------
# Tải file từ Google Drive (nếu chưa có)
# -------------------------
@st.cache_resource
def download_database():
    if not os.path.exists(DB_PATH):
        with st.spinner('Đang tải dữ liệu từ Google Drive (500MB)... Vui lòng đợi trong giây lát.'):
            session = requests.Session()
            url = "https://docs.google.com/uc?export=download"
            response = session.get(url, params={'id': GOOGLE_DRIVE_FILE_ID}, stream=True)

            token = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    token = value
                    break

            if token:
                response = session.get(url, params={'id': GOOGLE_DRIVE_FILE_ID, 'confirm': token}, stream=True)

            with open(DB_PATH, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:
                        f.write(chunk)

    return sqlite3.connect(DB_PATH, check_same_thread=False)

# -------------------------
# Load dữ liệu chính
# -------------------------
@st.cache_data
def load_data():
    conn = download_database()
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
    
    df["Ngày"] = pd.to_datetime(df["Ngày"])
    return df

# -------------------------
# Lấy ngày mua đầu tiên của mỗi khách
# -------------------------
@st.cache_data
def first_purchase():
    df = load_data()
    df_fp = (
        df.groupby("Số_điện_thoại")["Ngày"]
        .min()
        .reset_index(name="First_Date")
    )
    return df_fp

