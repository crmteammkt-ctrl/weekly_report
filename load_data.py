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

# =====================================================
# Helper: DB version (để cache tự invalid khi DB đổi)
# =====================================================
def db_version() -> float:
    return os.path.getmtime(DUCKDB_DB) if os.path.exists(DUCKDB_DB) else 0.0


# =====================================================
# Close connection + clear cache_resource
# =====================================================
def close_connection():
    try:
        con = get_connection()
        try:
            con.close()
        except Exception:
            pass
    except Exception:
        pass

    # clear cache_resource để lần sau get_connection tạo connection mới
    try:
        st.cache_resource.clear()
    except Exception:
        pass


# =====================================================
# Rebuild DuckDB from Drive (tải + convert)
# =====================================================
def rebuild_duckdb_from_drive():
    # 1) đóng connection trước để tránh lock
    close_connection()

    # 2) download sqlite tmp
    sqlite_tmp = SQLITE_DB + ".tmp"
    if os.path.exists(sqlite_tmp):
        try:
            os.remove(sqlite_tmp)
        except Exception:
            pass

    with st.spinner("⬇️ Đang tải DB từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, sqlite_tmp, quiet=False)

    # replace sqlite chính
    if os.path.exists(SQLITE_DB):
        try:
            os.remove(SQLITE_DB)
        except Exception:
            pass
    os.replace(sqlite_tmp, SQLITE_DB)

    # 3) convert sqlite -> duckdb tmp
    duck_tmp = DUCKDB_DB + ".tmp"
    if os.path.exists(duck_tmp):
        try:
            os.remove(duck_tmp)
        except Exception:
            pass

    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)
        sqlite_conn.close()

        # làm sạch numeric hay bị rác
        numeric_cols = ["Tổng_Gross", "Tổng_Net", "CK_%"]
        for col in numeric_cols:
            if col in df.columns:
                s = df[col].astype(str)
                s = s.str.replace("%", "", regex=False).str.replace(",", "", regex=False)
                s = s.replace("", np.nan)
                df[col] = pd.to_numeric(s, errors="coerce")

        duck = duckdb.connect(duck_tmp)
        duck.execute(f"CREATE OR REPLACE TABLE {TABLE_NAME} AS SELECT * FROM df")
        duck.close()

    # replace duckdb chính
    if os.path.exists(DUCKDB_DB):
        try:
            os.remove(DUCKDB_DB)
        except Exception:
            pass
    os.replace(duck_tmp, DUCKDB_DB)

    # 4) clear cache_data để load_data/first_purchase chạy lại với db mới
    try:
        st.cache_data.clear()
    except Exception:
        pass


# =====================================================
# DuckDB connection (cached)
# =====================================================
@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    if not os.path.exists(DUCKDB_DB):
        rebuild_duckdb_from_drive()
    return duckdb.connect(DUCKDB_DB, read_only=True)


# =====================================================
# Load main data (cached by db_version)
# =====================================================
@st.cache_data(show_spinner="📦 Loading data...")
def load_data(_db_ver: float):
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


# =====================================================
# First purchase (cached by db_version)
# =====================================================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase(_db_ver: float):
    con = get_connection()
    df = con.execute(f"""
        SELECT Số_điện_thoại, MIN(Ngày) AS First_Date
        FROM {TABLE_NAME}
        GROUP BY Số_điện_thoại
    """).df()

    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
