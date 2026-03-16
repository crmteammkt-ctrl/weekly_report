import os
import hashlib
from typing import Iterable, Optional, Sequence

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_FILE = os.path.join(BASE_DIR, "data", "data.parquet")

# =========================================================
# COLUMN SETS THEO PAGE
# =========================================================
COMMON_COLS = [
    "Ngày",
    "LoaiCT",
    "Brand",
    "Region",
    "Điểm_mua_hàng",
    "Trạng_thái_số_điện_thoại",
    "Kiểm_tra_tên",
    "Số_điện_thoại",
    "Số_CT",
    "Tổng_Gross",
    "Tổng_Net",
]

GENERAL_COLS = COMMON_COLS + [
    "Nhóm_hàng",
    "Mã_NB",
    "Số_lượng",
]

REVENUE_COLS = COMMON_COLS

CRM_COLS = COMMON_COLS + [
    "tên_KH",
]

CATEGORY_CANDIDATES = [
    "LoaiCT",
    "Brand",
    "Region",
    "Điểm_mua_hàng",
    "Trạng_thái_số_điện_thoại",
    "Kiểm_tra_tên",
    "Nhóm_hàng",
    "Mã_NB",
    "tên_KH",
]

# =========================================================
# LOW-LEVEL HELPERS
# =========================================================
def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    if "Ngày" in df.columns:
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
        df = df.dropna(subset=["Ngày"])

    for c in ["Tổng_Gross", "Tổng_Net", "Số_lượng"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def _fingerprint_df(df: pd.DataFrame) -> str:
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


def _optimize_df(
    df: pd.DataFrame,
    keep_cols: Optional[Sequence[str]] = None,
    category_cols: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df

    if keep_cols:
        keep_cols = [c for c in keep_cols if c in out.columns]
        out = out[keep_cols].copy()
    else:
        out = out.copy()

    if category_cols:
        for c in category_cols:
            if c in out.columns:
                try:
                    # chỉ convert khi có giá trị lặp nhiều, tránh phản tác dụng
                    nunique = out[c].nunique(dropna=True)
                    nrows = len(out)
                    if nrows > 0 and nunique / max(nrows, 1) < 0.5:
                        out[c] = out[c].astype("category")
                except Exception:
                    pass

    return out


def _files_signature(uploaded_files: Iterable) -> str:
    parts = []
    for f in uploaded_files:
        name = getattr(f, "name", "unknown")
        size = getattr(f, "size", None)
        parts.append(f"{name}:{size}")
    s = "|".join(parts)
    return hashlib.md5(s.encode()).hexdigest()

# =========================================================
# DEFAULT PARQUET
# =========================================================
@st.cache_data(show_spinner=False)
def _load_default_parquet(path: str, mtime: float) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return _normalize_df(df)


def get_default_data() -> pd.DataFrame:
    if not os.path.exists(PARQUET_FILE):
        st.error(f"Không thấy file dữ liệu: {PARQUET_FILE}")
        st.stop()

    mtime = os.path.getmtime(PARQUET_FILE)
    return _load_default_parquet(PARQUET_FILE, mtime)

# =========================================================
# ACTIVE DATA (FULL DATASET CHO SESSION)
# =========================================================
def get_active_data() -> pd.DataFrame:
    """
    Trả full active dataset của session.
    Chỉ dùng khi thật sự cần full data.
    """
    if isinstance(st.session_state.get("active_df"), pd.DataFrame) and not st.session_state["active_df"].empty:
        return st.session_state["active_df"]

    df = get_default_data()
    st.session_state["active_df"] = df
    st.session_state["active_source"] = "default"
    st.session_state["active_fp"] = _fingerprint_df(df)
    return df


def reset_to_default():
    df = get_default_data()
    st.session_state["active_df"] = df
    st.session_state["active_source"] = "default"
    st.session_state["active_fp"] = _fingerprint_df(df)


def set_active_data(df: pd.DataFrame, source: str = "upload"):
    df = _normalize_df(df)
    if df.empty:
        return

    st.session_state["active_df"] = df
    st.session_state["active_source"] = source
    st.session_state["active_fp"] = _fingerprint_df(df)


@st.cache_data(show_spinner=False)
def load_uploaded_parquets(signature: str, uploaded_files: tuple) -> pd.DataFrame:
    dfs = []
    for f in uploaded_files:
        dfs.append(pd.read_parquet(f))
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return _normalize_df(df)


def set_active_from_upload(uploaded_files: list, source: str = "upload"):
    if not uploaded_files:
        return

    sig = _files_signature(uploaded_files)
    df_up = load_uploaded_parquets(sig, tuple(uploaded_files))
    if df_up.empty:
        st.warning("⚠ File parquet upload không có dữ liệu hợp lệ.")
        return

    set_active_data(df_up, source=source)

# =========================================================
# PAGE-SPECIFIC DATA GETTERS
# =========================================================
@st.cache_data(show_spinner=False)
def _project_data_for_page(
    fp_key: str,
    df: pd.DataFrame,
    keep_cols: tuple,
    category_cols: tuple,
) -> pd.DataFrame:
    d = _optimize_df(df, keep_cols=list(keep_cols), category_cols=list(category_cols))
    return d


def _get_page_data(keep_cols: Sequence[str]) -> pd.DataFrame:
    df = get_active_data()
    fp_key = st.session_state.get("active_fp") or _fingerprint_df(df)

    out = _project_data_for_page(
        fp_key=fp_key,
        df=df,
        keep_cols=tuple(keep_cols),
        category_cols=tuple(CATEGORY_CANDIDATES),
    )
    return out


def get_general_data() -> pd.DataFrame:
    return _get_page_data(GENERAL_COLS)


def get_revenue_data() -> pd.DataFrame:
    return _get_page_data(REVENUE_COLS)


def get_crm_data() -> pd.DataFrame:
    return _get_page_data(CRM_COLS)

# =========================================================
# FIRST PURCHASE
# =========================================================
@st.cache_data(show_spinner=False)
def first_purchase(fp_key: str, df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Số_điện_thoại", "First_Date"])

    if "Số_điện_thoại" not in df.columns or "Ngày" not in df.columns:
        return pd.DataFrame(columns=["Số_điện_thoại", "First_Date"])

    d = df[["Số_điện_thoại", "Ngày"]].copy()
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
        # CRM cần First Purchase nên mặc định dùng crm data là đủ
        df = get_crm_data()

    fp_key = st.session_state.get("active_fp") or _fingerprint_df(df)
    return first_purchase(fp_key, df)