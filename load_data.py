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
def load_data() -> pd.DataFrame:
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

# =========================
# 2. DỮ LIỆU ĐANG DÙNG CHUNG CHO TOÀN APP
# =========================
def get_active_data():
    """
    Trả về DataFrame đang được dùng cho MỌI TRANG.
    - Nếu chưa có trong session_state -> load từ Parquet mặc định.
    - Nếu đã upload từ General Report -> lấy bản đã upload.
    """
    if "active_df" not in st.session_state:
        return st.session_state["active_df"]
    
    df = load_data()
    st.session_state["active_df"] = df
    st.session_state["active_source"] = "default"
    return df

def set_active_data(df: pd.DataFrame, source: str = "upload"):
    """
    Cập nhật DataFrame dùng chung cho toàn app.
    (Gọi khi user upload file parquet mới ở General Report)
    """
    if df is None or df.empty:
        return
    
    df = df.copy()

    # Chuẩn hoá ngày
    if "Ngày" in df.columns:
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
        df = df.dropna(subset=["Ngày"])

    # Chuẩn hoá số
    for c in ["Tổng_Gross", "Tổng_Net"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    st.session_state["active_df"] = df
    st.session_state["active_source"] = source


# =========================
# 3. FIRST PURCHASE (KH mới / KH quay lại)
# =========================
def first_purchase(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Trả về bảng:
        Số_điện_thoại | First_Date

    - Nếu không truyền df -> tự lấy từ get_active_data()
    - KHÔNG dùng cache_data ở đây để khi upload parquet mới,
      kết quả First_Date cũng thay đổi theo.
    """
    if df is None:
        df = get_active_data()

    if "Số_điện_thoại" not in df.columns or "Ngày" not in df.columns:
        # Tránh crash nếu thiếu cột
        return pd.DataFrame(columns=["Số_điện_thoại", "First_Date"])

    fp = (
        df.groupby("Số_điện_thoại", as_index=False)["Ngày"]
        .min()
        .rename(columns={"Ngày": "First_Date"})
    )
    return fp
