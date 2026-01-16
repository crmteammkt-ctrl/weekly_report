import os
import pandas as pd
import numpy as np
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_FILE = os.path.join(BASE_DIR, "data", "report_last_90_days.parquet")


def rebuild_duckdb_from_drive():
    st.warning("App đang sử dụng file Parquet commit trong repo. Muốn cập nhật dữ liệu thì cập nhật file Parquet rồi push GitHub.")


def close_connection():
    pass


@st.cache_data(show_spinner="📦 Loading data từ Parquet...")
def load_data():
    if not os.path.exists(PARQUET_FILE):
        st.error(f"Không thấy file dữ liệu: {PARQUET_FILE}")
        st.stop()

    df = pd.read_parquet(PARQUET_FILE)

    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    df = df.dropna(subset=["Ngày"])

    for c in ["Tổng_Gross", "Tổng_Net"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


@st.cache_data(show_spinner="📅 Calculating first purchase...")
def first_purchase():
    df = load_data()
    fp = (
        df.groupby("Số_điện_thoại", as_index=False)["Ngày"]
        .min()
        .rename(columns={"Ngày": "First_Date"})
    )
    return fp
