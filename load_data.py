import os
import duckdb
import pandas as pd
import streamlit as st

# =========================
# CONFIG
# =========================
DUCKDB_DB = "marketing.duckdb"
TABLE_NAME = "tinhhinhbanhang"


# =========================
# GET CONNECTION (DUCKDB)
# =========================
@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    if not os.path.exists(DUCKDB_DB):
        st.error(
            "❌ Không tìm thấy file DuckDB "
            f"'{DUCKDB_DB}'. Hãy chạy `python convert_sqlite_duckdb.py` "
            "trong terminal để tạo file trước."
        )
        st.stop()

    # read_only cho an toàn
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

    # Chuẩn hoá kiểu dữ liệu
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")

    num_cols = ["Tổng_Gross", "Tổng_Net"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Bỏ dòng không có ngày để tránh lỗi
    df = df.dropna(subset=["Ngày"])

    return df


# =========================
# FIRST PURCHASE
# =========================
@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    con = get_connection()

    df = con.execute(f"""
        SELECT
            Số_điện_thoại,
            MIN(Ngày) AS First_Date
        FROM {TABLE_NAME}
        GROUP BY Số_điện_thoại
    """).df()

    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
