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
# CLOSE CONNECTION + CLEAR CACHE (QUAN TRỌNG)
# =========================
def close_connection():
    """
    Đóng connection DuckDB đang được cache + clear cache_resource.
    """
    try:
        con = get_connection()
        try:
            con.close()
        except Exception:
            pass
    except Exception:
        pass

    # QUAN TRỌNG: clear cache_resource đúng cách
    try:
        st.cache_resource.clear()
    except Exception:
        pass



# =========================
# HÀM TẢI + CONVERT DB
# =========================
def rebuild_duckdb_from_drive():
    """
    Download SQLite từ Drive và convert sang DuckDB.
    Gọi được nhiều lần (kể cả file không đổi) và KHÔNG làm app lỗi.
    """

    # 1) ĐÓNG CONNECTION TRƯỚC (QUAN TRỌNG)
    close_connection()

    # 2) Download SQLite (download ra file tạm để an toàn)
    sqlite_tmp = SQLITE_DB + ".tmp"
    if os.path.exists(sqlite_tmp):
        try:
            os.remove(sqlite_tmp)
        except Exception:
            pass

    with st.spinner("⬇️ Đang tải DB từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, sqlite_tmp, quiet=False)

    # replace sqlite chính thức
    if os.path.exists(SQLITE_DB):
        try:
            os.remove(SQLITE_DB)
        except Exception:
            pass
    os.replace(sqlite_tmp, SQLITE_DB)

    # 3) Convert SQLite -> DuckDB (ghi ra duckdb tạm rồi replace)
    duck_tmp = DUCKDB_DB + ".tmp"
    if os.path.exists(duck_tmp):
        try:
            os.remove(duck_tmp)
        except Exception:
            pass

    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        # đọc SQLite
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)
        sqlite_conn.close()

        # làm sạch một số cột số hay bị rác ('' hoặc có dấu % ,)
        numeric_cols = ["Tổng_Gross", "Tổng_Net", "CK_%"]
        for col in numeric_cols:
            if col in df.columns:
                s = df[col].astype(str)
                s = s.str.replace("%", "", regex=False).str.replace(",", "", regex=False)
                s = s.replace("", np.nan)
                df[col] = pd.to_numeric(s, errors="coerce")

        # tạo duckdb tạm
        duck = duckdb.connect(duck_tmp)
        duck.execute(f"""
            CREATE OR REPLACE TABLE {TABLE_NAME} AS
            SELECT * FROM df
        """)
        duck.close()

    # replace duckdb chính thức (atomic)
    if os.path.exists(DUCKDB_DB):
        try:
            os.remove(DUCKDB_DB)
        except Exception:
            pass
    os.replace(duck_tmp, DUCKDB_DB)

    # 4) clear cache_data luôn để load_data/first_purchase đọc dữ liệu mới
    try:
        st.cache_data.clear()
    except Exception:
        pass


# =========================
# GET CONNECTION
# =========================
@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    # lần đầu chưa có DuckDB → build
    if not os.path.exists(DUCKDB_DB):
        rebuild_duckdb_from_drive()

    # dùng read_only=True để tránh vô tình ghi dữ liệu khi query
    return duckdb.connect(DUCKDB_DB, read_only=True)


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
