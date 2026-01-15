import os
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import gdown

# =========================
# CẤU HÌNH
# =========================
# DB gốc 512MB trên Google Drive
GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"

# Tên file trên server Streamlit
SQLITE_DB = "thiensondb.db"

# Bảng dùng cho báo cáo
TABLE_NAME = "tinhhinhbanhang"


# =========================
# TẢI DB TỪ GOOGLE DRIVE
# =========================
def rebuild_duckdb_from_drive():
    """
    (Giữ tên hàm cũ cho hợp với general_report.py)
    Thực tế: chỉ tải file SQLite 512MB từ Google Drive về.
    KHÔNG dùng DuckDB, KHÔNG convert nặng.
    """
    with st.spinner("⬇️ Đang tải DB SQLite (thiensondb.db) từ Google Drive (~512MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"

        # Xoá file cũ nếu có
        if os.path.exists(SQLITE_DB):
            os.remove(SQLITE_DB)

        # Tải DB mới
        gdown.download(url, SQLITE_DB, quiet=False)


def ensure_sqlite_exists():
    """
    Đảm bảo file SQLite tồn tại trước khi đọc.
    Lần đầu (hoặc sau khi bấm 'Cập nhật dữ liệu') sẽ tự tải từ Drive.
    """
    if not os.path.exists(SQLITE_DB):
        rebuild_duckdb_from_drive()


def close_connection():
    """
    Dummy để tương thích với general_report.py.
    Không giữ connection global nên không cần làm gì cả.
    """
    pass


# =========================
# LOAD MAIN DATA
# =========================
@st.cache_data(show_spinner="📦 Loading data từ thiensondb.db...")
def load_data():
    """
    Đọc dữ liệu chính từ bảng tinhhinhbanhang trong thiensondb.db.
    """
    ensure_sqlite_exists()

    conn = sqlite3.connect(SQLITE_DB)
    df = pd.read_sql(f"""
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
    """, conn)
    conn.close()

    # Chuẩn hoá ngày
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    df = df.dropna(subset=["Ngày"])

    # Chuẩn hoá số
    for c in ["Tổng_Gross", "Tổng_Net"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# =========================
# FIRST PURCHASE
# =========================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    """
    Lấy ngày mua đầu tiên của từng SĐT từ bảng tinhhinhbanhang.
    """
    ensure_sqlite_exists()

    conn = sqlite3.connect(SQLITE_DB)
    df = pd.read_sql(f"""
        SELECT Số_điện_thoại, MIN(Ngày) AS First_Date
        FROM {TABLE_NAME}
        GROUP BY Số_điện_thoại
    """, conn)
    conn.close()

    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
