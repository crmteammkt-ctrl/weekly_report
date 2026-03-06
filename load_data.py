import os
import hashlib
from typing import Iterable, Optional

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_FILE = os.path.join(BASE_DIR, "data", "data.parquet")

# =========================
# NORMALIZE (CHỈ 1 CHỖ)
# =========================
def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Ngày
    if "Ngày" in df.columns:
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
        df = df.dropna(subset=["Ngày"])

    # Numeric
    for c in ["Tổng_Gross", "Tổng_Net"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def _fingerprint_df(df: pd.DataFrame) -> str:
    """
    Fingerprint nhẹ để cache theo dữ liệu active (tránh hash full df).
    """
    if df is None or df.empty:
        return "EMPTY"

    h = hashlib.md5()
    h.update(str(df.shape).encode())
    h.update((",".join(df.columns.astype(str))).encode())

    if "Ngày" in df.columns:
        dmin = str(pd.to_datetime(df["Ngày"], errors="coerce").min())
        dmax = str(pd.to_datetime(df["Ngày"], errors="coerce").max())
        h.update(dmin.encode())
        h.update(dmax.encode())

    return h.hexdigest()


# =========================
# LOAD DEFAULT PARQUET (CACHE THEO FILE MTIME)
# =========================
@st.cache_data(show_spinner=False)
def _load_default_parquet(path: str, mtime: float) -> pd.DataFrame:
    # mtime đưa vào để auto invalidate khi file thay đổi
    df = pd.read_parquet(path)
    return _normalize_df(df)


def get_default_data() -> pd.DataFrame:
    if not os.path.exists(PARQUET_FILE):
        st.error(f"Không thấy file dữ liệu: {PARQUET_FILE}")
        st.stop()
    mtime = os.path.getmtime(PARQUET_FILE)
    return _load_default_parquet(PARQUET_FILE, mtime)


# =========================
# ACTIVE DATA (DÙNG CHUNG TOÀN APP THEO SESSION)
# =========================
def get_active_data() -> pd.DataFrame:
    """
    - Nếu đã có st.session_state["active_df"] => trả luôn (NHANH)
    - Nếu chưa có => lấy default (cache_data) rồi gán session_state
    """
    if isinstance(st.session_state.get("active_df"), pd.DataFrame) and not st.session_state["active_df"].empty:
        return st.session_state["active_df"]

    df = get_default_data()
    st.session_state["active_df"] = df
    st.session_state["active_source"] = "default"
    st.session_state["active_fp"] = _fingerprint_df(df)
    return df


def reset_to_default():
    """
    Reset về default mà không bị “kẹt” state cũ.
    """
    df = get_default_data()
    st.session_state["active_df"] = df
    st.session_state["active_source"] = "default"
    st.session_state["active_fp"] = _fingerprint_df(df)


def set_active_data(df: pd.DataFrame, source: str = "upload"):
    """
    Khi upload parquet mới:
    - Normalize 1 lần
    - Gán vào session_state để toàn bộ pages dùng chung ngay
    """
    df = _normalize_df(df)
    if df.empty:
        return

    st.session_state["active_df"] = df
    st.session_state["active_source"] = source
    st.session_state["active_fp"] = _fingerprint_df(df)


# =========================
# UPLOAD MULTI PARQUET (OPTIONAL) – CACHE THEO SIGNATURE FILE
# =========================
def _files_signature(uploaded_files: Iterable) -> str:
    """
    Tạo signature ổn định để cache khi người dùng upload nhiều file.
    Streamlit UploadedFile có name + size.
    """
    parts = []
    for f in uploaded_files:
        name = getattr(f, "name", "unknown")
        size = getattr(f, "size", None)
        parts.append(f"{name}:{size}")
    s = "|".join(parts)
    return hashlib.md5(s.encode()).hexdigest()


@st.cache_data(show_spinner=False)
def load_uploaded_parquets(signature: str, uploaded_files: tuple) -> pd.DataFrame:
    """
    uploaded_files phải là tuple để cache ổn định.
    signature dùng làm key cache (nhanh).
    """
    dfs = []
    for f in uploaded_files:
        dfs.append(pd.read_parquet(f))
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return _normalize_df(df)


def set_active_from_upload(uploaded_files: list, source: str = "upload"):
    """
    Helper dùng trong pages: upload nhiều parquet -> concat -> set active
    """
    if not uploaded_files:
        return

    sig = _files_signature(uploaded_files)
    df_up = load_uploaded_parquets(sig, tuple(uploaded_files))
    if df_up.empty:
        st.warning("⚠ File parquet upload không có dữ liệu hợp lệ.")
        return

    set_active_data(df_up, source=source)


# =========================
# FIRST PURCHASE (CACHE THEO ACTIVE FP)
# =========================
@st.cache_data(show_spinner=False)
def first_purchase(fp_key: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    fp_key: fingerprint của active_df để cache đúng theo dataset.
    df: truyền vào để tính, nhưng cache theo fp_key.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Số_điện_thoại", "First_Date"])

    if "Số_điện_thoại" not in df.columns or "Ngày" not in df.columns:
        return pd.DataFrame(columns=["Số_điện_thoại", "First_Date"])

    d = df.copy()
    d["Ngày"] = pd.to_datetime(d["Ngày"], errors="coerce")
    d["Số_điện_thoại"] = d["Số_điện_thoại"].astype(str).str.strip()

    d = d.dropna(subset=["Ngày", "Số_điện_thoại"])
    d = d[d["Số_điện_thoại"] != ""]

    out = (
        d.groupby("Số_điện_thoại", as_index=False)["Ngày"]
        .min()
        .rename(columns={"Ngày": "First_Date"})
    )
    return out


def get_first_purchase(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    if df is None:
        df = get_active_data()
    fp_key = st.session_state.get("active_fp") or _fingerprint_df(df)
    return first_purchase(fp_key, df)