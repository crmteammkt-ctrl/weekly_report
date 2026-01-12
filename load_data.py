import sqlite3
import pandas as pd
import os
import gdown
import streamlit as st

# ==================================================
# CONFIG
# ==================================================
GOOGLE_DRIVE_FILE_ID = "1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH"
DB_PATH = "thiensondb.db"

# ==================================================
# INTERNAL UTILS
# ==================================================
def _download_db_if_needed():
    """Download SQLite DB from Google Drive if not exists"""
    if os.path.exists(DB_PATH):
        return

    url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
    gdown.download(url, DB_PATH, quiet=False)

    # Validate SQLite header
    with open(DB_PATH, "rb") as f:
        header = f.read(16)
        if header != b"SQLite format 3\x00":
            raise RuntimeError(
                "❌ File tải về không phải SQLite database. "
                "Kiểm tra lại Google Drive link hoặc quyền truy cập."
            )

# ==================================================
# DATABASE CONNECTION (SINGLETON)
# ==================================================
@st.cache_resource(show_spinner="⬇️ Preparing database...")
def get_connection() -> sqlite3.Connection:
    _download_db_if_needed()

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=30
    )

    return conn


# ==================================================
# LOAD MAIN DATA
# ==================================================
@st.cache_data(show_spinner="📦 Loading sales data...")
def load_data() -> pd.DataFrame:
    conn = get_connection()

    df = pd.read_sql(
        """
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
        """,
        conn,
    )

    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    return df


# ==================================================
# FIRST PURCHASE DATE
# ==================================================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase() -> pd.DataFrame:
    conn = get_connection()

    df_fp = pd.read_sql(
        """
        SELECT
            Số_điện_thoại,
            MIN(Ngày) AS First_Date
        FROM tinhhinhbanhang
        GROUP BY Số_điện_thoại
        """,
        conn,
    )

    df_fp["First_Date"] = pd.to_datetime(df_fp["First_Date"], errors="coerce")
    return df_fp
