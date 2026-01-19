import os
import pandas as pd
import numpy as np
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_FILE = os.path.join(BASE_DIR, "data", "data.parquet")


# =========================
# 1. HÀM CŨ – GIỮ CHO ĐỦ INTERFACE
# =========================
def rebuild_duckdb_from_drive():
    st.warning(
        "App đang sử dụng file Parquet commit trong repo. "
        "Muốn cập nhật dữ liệu thì cập nhật file Parquet rồi push GitHub."
    )


def close_connection():
    # Không dùng DB nữa, nên để pass cho các chỗ import cũ khỏi lỗi
    pass


# =========================
# 2. LOAD PARQUET MẶC ĐỊNH
# =========================
@st.cache_data(show_spinner="📦 Loading data từ Parquet...")
def load_data() -> pd.DataFrame:
    """
    Đọc file Parquet mặc định trong repo.
    Dùng làm nguồn dữ liệu 'default' khi chưa upload gì.
    """
    if not os.path.exists(PARQUET_FILE):
        st.error(f"Không thấy file dữ liệu: {PARQUET_FILE}")
        st.stop()

    df = pd.read_parquet(PARQUET_FILE)

    # Chuẩn hoá cột Ngày
    if "Ngày" in df.columns:
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
        df = df.dropna(subset=["Ngày"])

    # Chuẩn hoá số
    for c in ["Tổng_Gross", "Tổng_Net"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# =========================
# 3. DỮ LIỆU ĐANG DÙNG CHUNG CHO TOÀN APP
# =========================
def get_active_data() -> pd.DataFrame:
    """
    Trả về DataFrame đang được dùng cho MỌI TRANG.

    - Nếu user đã upload parquet (qua set_active_data) -> dùng bản đó.
    - Nếu chưa có trong session_state -> load từ Parquet mặc định.
    """
    # ✅ Nếu đã có trong session_state thì dùng luôn (thường là dữ liệu upload)
    if "active_df" in st.session_state:
        return st.session_state["active_df"]

    # ✅ Nếu chưa có thì load từ file mặc định
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
# 4. FIRST PURCHASE (KH mới / KH quay lại)
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

    if df.empty:
        return pd.DataFrame(columns=["Số_điện_thoại", "First_Date"])

    if "Số_điện_thoại" not in df.columns or "Ngày" not in df.columns:
        # Tránh crash nếu thiếu cột
        return pd.DataFrame(columns=["Số_điện_thoại", "First_Date"])

    # Đảm bảo Ngày là datetime (dù load_data đã làm rồi, thêm cho chắc)
    df = df.copy()
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    df = df.dropna(subset=["Ngày"])

    fp = (
        df.groupby("Số_điện_thoại", as_index=False)["Ngày"]
        .min()
        .rename(columns={"Ngày": "First_Date"})
    )
    return fp
