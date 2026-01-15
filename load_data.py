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


def close_connection():
    # đóng + clear cache_resource để tránh lock file
    try:
        con = get_connection()
        try:
            con.close()
        except Exception:
            pass
    except Exception:
        pass

    try:
        st.cache_resource.clear()
    except Exception:
        pass


def rebuild_duckdb_from_drive():
    close_connection()

    sqlite_tmp = SQLITE_DB + ".tmp"
    if os.path.exists(sqlite_tmp):
        try: os.remove(sqlite_tmp)
        except Exception: pass

    with st.spinner("⬇️ Đang tải DB từ Google Drive (~500MB)..."):
        url = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
        gdown.download(url, sqlite_tmp, quiet=False)

    if os.path.exists(SQLITE_DB):
        try: os.remove(SQLITE_DB)
        except Exception: pass
    os.replace(sqlite_tmp, SQLITE_DB)

    duck_tmp = DUCKDB_DB + ".tmp"
    if os.path.exists(duck_tmp):
        try: os.remove(duck_tmp)
        except Exception: pass

    with st.spinner("🦆 Đang convert SQLite → DuckDB..."):
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", sqlite_conn)
        sqlite_conn.close()

        # clean numeric
        numeric_cols = ["Tổng_Gross", "Tổng_Net", "CK_%"]
        for col in numeric_cols:
            if col in df.columns:
                s = df[col].astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False)
                s = s.replace("", np.nan)
                df[col] = pd.to_numeric(s, errors="coerce")

        duck = duckdb.connect(duck_tmp)
        duck.execute(f"CREATE OR REPLACE TABLE {TABLE_NAME} AS SELECT * FROM df")
        duck.close()

    if os.path.exists(DUCKDB_DB):
        try: os.remove(DUCKDB_DB)
        except Exception: pass
    os.replace(duck_tmp, DUCKDB_DB)

    # clear cache_data để đọc dữ liệu mới
    try:
        st.cache_data.clear()
    except Exception:
        pass


@st.cache_resource(show_spinner="🦆 Opening DuckDB...")
def get_connection():
    if not os.path.exists(DUCKDB_DB):
        rebuild_duckdb_from_drive()
    return duckdb.connect(DUCKDB_DB, read_only=True)


# ✅ chỉ lấy MIN/MAX ngày (nhanh)
@st.cache_data(show_spinner=False)
def get_date_bounds():
    con = get_connection()
    row = con.execute(f'SELECT MIN("Ngày") AS min_d, MAX("Ngày") AS max_d FROM {TABLE_NAME}').fetchone()
    return pd.to_datetime(row[0], errors="coerce"), pd.to_datetime(row[1], errors="coerce")


# ✅ lấy options filter (nhanh hơn load full)
@st.cache_data(show_spinner=False)
def get_filter_options():
    con = get_connection()
    # DISTINCT trên từng cột, tránh kéo full table
    loai = con.execute(f'SELECT DISTINCT "LoaiCT" FROM {TABLE_NAME} WHERE "LoaiCT" IS NOT NULL').df()["LoaiCT"].tolist()
    brand = con.execute(f'SELECT DISTINCT "Brand" FROM {TABLE_NAME} WHERE "Brand" IS NOT NULL').df()["Brand"].tolist()
    region = con.execute(f'SELECT DISTINCT "Region" FROM {TABLE_NAME} WHERE "Region" IS NOT NULL').df()["Region"].tolist()
    store = con.execute(f'SELECT DISTINCT "Điểm_mua_hàng" FROM {TABLE_NAME} WHERE "Điểm_mua_hàng" IS NOT NULL').df()["Điểm_mua_hàng"].tolist()
    return sorted(loai), sorted(brand), sorted(region), sorted(store)


# ✅ load dữ liệu theo filter (chỉ kéo phần cần)
@st.cache_data(show_spinner="📦 Loading filtered data...")
def load_data_filtered(start_date, end_date, loaiCT_list, brand_list, region_list, store_list):
    con = get_connection()

    sql = f"""
        SELECT
            "Ngày",
            "LoaiCT",
            "Brand",
            "Region",
            "Tỉnh_TP",
            "Điểm_mua_hàng",
            "Nhóm_hàng",
            "Tên_hàng",
            "Số_CT",
            "tên_KH",
            "Kiểm_tra_tên",
            "Số_điện_thoại",
            "Trạng_thái_số_điện_thoại",
            "Tổng_Gross",
            "Tổng_Net"
        FROM {TABLE_NAME}
        WHERE "Ngày" BETWEEN ? AND ?
          AND ("LoaiCT" IN (SELECT * FROM UNNEST(?)))
          AND ("Brand"  IN (SELECT * FROM UNNEST(?)))
          AND ("Region" IN (SELECT * FROM UNNEST(?)))
          AND ("Điểm_mua_hàng" IN (SELECT * FROM UNNEST(?)))
    """

    df = con.execute(
        sql,
        [pd.to_datetime(start_date), pd.to_datetime(end_date),
         loaiCT_list, brand_list, region_list, store_list]
    ).df()

    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    df = df.dropna(subset=["Ngày"])

    for c in ["Tổng_Gross", "Tổng_Net"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


@st.cache_data(show_spinner=False)
def first_purchase():
    con = get_connection()
    df = con.execute(f'''
        SELECT "Số_điện_thoại", MIN("Ngày") AS First_Date
        FROM {TABLE_NAME}
        GROUP BY "Số_điện_thoại"
    ''').df()
    df["First_Date"] = pd.to_datetime(df["First_Date"], errors="coerce")
    return df
