# pages/00_general_report.py

import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from datetime import datetime

from load_data import get_active_data, set_active_data, first_purchase

# =====================================================
# Utils
# =====================================================
def to_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()


def fix_float(df: pd.DataFrame, cols) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


# =====================================================
# Page config
# =====================================================
st.set_page_config(page_title="Marketing Revenue Dashboard", layout="wide")
st.title("📊 MARKETING REVENUE DASHBOARD – Tổng quan")

# =====================================================
# CHỌN NGUỒN DỮ LIỆU CHO TOÀN APP
# =====================================================
with st.sidebar:
    st.markdown("### 🗂 Chọn nguồn dữ liệu")

    src_choice = st.radio(
        "Nguồn dữ liệu (áp dụng cho tất cả trang)",
        [
            "Dùng dữ liệu hiện tại",
            "Upload file parquet từ máy",
            "Quay lại dữ liệu mặc định",
        ],
        index=0,
        key="data_source_main",
    )

    uploaded_files = None
    if src_choice == "Upload file parquet từ máy":
        uploaded_files = st.file_uploader(
            "📁 Chọn 1 hoặc nhiều file .parquet",
            type=["parquet"],
            accept_multiple_files=True,
            key="parquet_uploader_main",
        )

# Xử lý lựa chọn nguồn
if src_choice == "Upload file parquet từ máy" and uploaded_files:
    # KHÔNG cache để tránh giữ nhiều bản copy
    dfs = [pd.read_parquet(f) for f in uploaded_files]
    df_up = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    if df_up.empty:
        st.warning("⚠ File parquet upload không có dữ liệu hợp lệ. Vẫn giữ dữ liệu cũ.")
    else:
        set_active_data(df_up, source="upload")
        st.success(
            f"✅ Đã cập nhật dữ liệu từ {len(uploaded_files)} file parquet upload"
        )

elif src_choice == "Quay lại dữ liệu mặc định":
    if "active_df" in st.session_state:
        del st.session_state["active_df"]
    _ = get_active_data()
    st.success("↩ Đã quay lại dùng dữ liệu mặc định trên server")

# Luôn lấy lại dữ liệu đang active
df = get_active_data()
st.sidebar.caption(
    "🔎 Đang dùng nguồn: **{}**".format(
        st.session_state.get("active_source", "default")
    )
)

# Bảo đảm cột Ngày chuẩn
if "Ngày" in df.columns:
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    df = df.dropna(subset=["Ngày"])

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích. Kiểm tra lại nguồn dữ liệu.")
    st.stop()

# =====================================================
# SIDEBAR FILTER (có liên kết Brand → Region → Cửa hàng)
# =====================================================
with st.sidebar:
    st.header("🎛️ Bộ lọc dữ liệu (Tổng quan)")

    time_type = st.selectbox(
        "Phân tích theo", ["Ngày", "Tuần", "Tháng", "Quý", "Năm"]
    )

    start_date = st.date_input("Từ ngày", df["Ngày"].min().date())
    end_date = st.date_input("Đến ngày", df["Ngày"].max().date())

    # Loại CT độc lập
    all_loaiCT = sorted(df["LoaiCT"].dropna().unique())
    loaiCT_filter = st.multiselect(
        "Loại CT", all_loaiCT, default=all_loaiCT
    )

    # Cascading Brand -> Region -> Cửa hàng
    all_brand = sorted(df["Brand"].dropna().unique())
    brand_filter = st.multiselect(
        "Brand", all_brand, default=all_brand
    )

    df_brand = df[df["Brand"].isin(brand_filter)]

    all_region = sorted(df_brand["Region"].dropna().unique())
    region_filter = st.multiselect(
        "Region", all_region, default=all_region
    )

    df_brand_region = df_brand[df_brand["Region"].isin(region_filter)]

    all_store = sorted(df_brand_region["Điểm_mua_hàng"].dropna().unique())
    store_filter = st.multiselect(
        "Cửa hàng", all_store, default=all_store
    )

# =====================================================
# APPLY FILTER
# =====================================================
def apply_filters(
    df: pd.DataFrame,
    start_date,
    end_date,
    loaiCT,
    brand,
    region,
    store,
) -> pd.DataFrame:
    mask = (
        (df["Ngày"] >= pd.to_datetime(start_date))
        & (df["Ngày"] <= pd.to_datetime(end_date))
        & (df["LoaiCT"].isin(loaiCT))
        & (df["Brand"].isin(brand))
        & (df["Region"].isin(region))
        & (df["Điểm_mua_hàng"].isin(store))
    )
    return df.loc[mask]


df_f = apply_filters(
    df,
    start_date,
    end_date,
    loaiCT_filter,
    brand_filter,
    region_filter,
    store_filter,
)

if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# TIME COLUMN
# =====================================================
df_f_time = df_f.copy()
if time_type == "Ngày":
    df_f_time["Time"] = df_f_time["Ngày"].dt.date
elif time_type == "Tuần":
    iso = df_f_time["Ngày"].dt.isocalendar()
    df_f_time["Time"] = (
        "Tuần " + iso["week"].astype(str).str.zfill(2) + "/" + iso["year"].astype(str)
    )
elif time_type == "Tháng":
    df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("M").astype(str)
elif time_type == "Quý":
    df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("Q").astype(str)
elif time_type == "Năm":
    df_f_time["Time"] = df_f_time["Ngày"].dt.year

# =====================================================
# KPI
# =====================================================
gross = df_f["Tổng_Gross"].sum()
net = df_f["Tổng_Net"].sum()
orders = df_f["Số_CT"].nunique()
customers = df_f["Số_điện_thoại"].nunique()
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gross", value=f"{gross:,.0f}")
c2.metric("Net", value=f"{net:,.0f}")
c3.metric("CK %", value=f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", orders)
c5.metric("Khách hàng", customers)

# =====================================================
# TIME GROUP
# =====================================================
def group_time(df_f: pd.DataFrame, time_type: str) -> pd.DataFrame:
    freq_map = {"Ngày": "D", "Tuần": "W", "Tháng": "ME", "Quý": "Q", "Năm": "Y"}
    d = (
        df_f.set_index("Ngày")
        .resample(freq_map[time_type])
        .agg(
            Gross=("Tổng_Gross", "sum"),
            Net=("Tổng_Net", "sum"),
            Orders=("Số_CT", "nunique"),
            Customers=("Số_điện_thoại", "nunique"),
        )
        .reset_index()
    )
    d["CK_%"] = np.where(d["Gross"] > 0, (1 - d["Net"] / d["Gross"]) * 100, 0)
    d["Net_prev"] = d["Net"].shift(1)
    d["Growth_%"] = np.where(
        d["Net_prev"] > 0, (d["Net"] - d["Net_prev"]) / d["Net_prev"] * 100, 0
    )
    return d


df_time = group_time(df_f, time_type)
df_time = fix_float(df_time, ["CK_%", "Growth_%"])

st.subheader(f"⏱ Theo thời gian ({time_type})")
st.dataframe(df_time, width="stretch")

# =====================================================
# REGION + TIME
# =====================================================
def group_region_time(df: pd.DataFrame) -> pd.DataFrame:
    d = (
        df.groupby(["Time", "Region"])
        .agg(
            Gross=("Tổng_Gross", "sum"),
            Net=("Tổng_Net", "sum"),
            Orders=("Số_CT", "nunique"),
            Customers=("Số_điện_thoại", "nunique"),
        )
        .reset_index()
    )
    d["CK_%"] = np.where(
        d["Gross"] > 0, (d["Gross"] - d["Net"]) / d["Gross"] * 100, 0
    )
    return d.sort_values(["Time", "Net"], ascending=[True, False])


df_region_time = fix_float(group_region_time(df_f_time), ["CK_%"])
st.subheader(f"🌍 Theo Region + {time_type}")
st.dataframe(df_region_time, width="stretch")

# -------------------------
# Báo cáo cửa hàng
# -------------------------
st.subheader("🏪 Tổng quan theo Cửa hàng")

df_store = (
    df_f.groupby("Điểm_mua_hàng")
    .agg(
        Gross=("Tổng_Gross", "sum"),
        Net=("Tổng_Net", "sum"),
        Orders=("Số_CT", "nunique"),
        Customers=("Số_điện_thoại", "nunique"),
    )
    .reset_index()
)
df_store["CK_%"] = np.where(
    df_store["Gross"] > 0,
    (df_store["Gross"] - df_store["Net"]) / df_store["Gross"] * 100,
    0,
).round(2)

st.dataframe(df_store.sort_values("Net", ascending=False), width="stretch")

# -------------------------
# Báo cáo nhóm sản phẩm
# -------------------------
df_product = df_f.copy()
st.subheader("📦 Theo Nhóm SP / Mã NB")

col1, col2 = st.columns(2)
with col1:
    nhom_sp_selected = st.multiselect(
        "📦 Chọn Nhóm SP", sorted(df_product["Nhóm_hàng"].dropna().unique())
    )
with col2:
    ten_sp_selected = st.multiselect(
        "🏷️ Chọn Mã NB", sorted(df_product["Mã_NB"].dropna().unique())
    )

if nhom_sp_selected:
    df_product = df_product[df_product["Nhóm_hàng"].isin(nhom_sp_selected)]
if ten_sp_selected:
    df_product = df_product[df_product["Mã_NB"].isin(ten_sp_selected)]

df_product_group = (
    df_product.groupby("Mã_NB")
    .agg(
        Gross=("Tổng_Gross", "sum"),
        Net=("Tổng_Net", "sum"),
        Orders=("Số_CT", "nunique"),
        Customers=("Số_điện_thoại", "nunique"),
    )
    .reset_index()
    .sort_values("Net", ascending=False)
)

st.dataframe(df_product_group, width="stretch")
