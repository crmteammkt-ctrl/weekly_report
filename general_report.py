import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from datetime import datetime

from load_data import load_data  # dùng chung parquet
# =====================================================
# Helper: Đọc & gộp nhiều file parquet upload
# =====================================================
@st.cache_data(show_spinner="📦 Đang đọc file parquet upload...")
def load_parquet_from_upload(files):
    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        d = pd.read_parquet(f)
        dfs.append(d)

    df = pd.concat(dfs, ignore_index=True)

    # Chuẩn hoá cột Ngày
    if "Ngày" in df.columns:
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
        df = df.dropna(subset=["Ngày"])

    return df
# =====================================================
# Utils
# =====================================================
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()

def fix_float(df, cols):
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
# LOAD DATA (có cache ở load_data.py)
# =====================================================
# =====================================================
# LOAD DATA (mặc định + upload linh hoạt)
# =====================================================
with st.sidebar:
    st.markdown("### 🗂 Chọn nguồn dữ liệu")

    data_source = st.radio(
        "Nguồn dữ liệu",
        ["Dùng dữ liệu mặc định trên server", "Upload file parquet từ máy"],
        index=0,
        key="data_source_main"
    )

    uploaded_files = None
    if data_source == "Upload file parquet từ máy":
        uploaded_files = st.file_uploader(
            "📁 Chọn 1 hoặc nhiều file .parquet",
            type=["parquet"],
            accept_multiple_files=True,
            key="parquet_uploader_main"
        )

# Quyết định dùng dữ liệu nào
if data_source == "Upload file parquet từ máy" and uploaded_files:
    df = load_parquet_from_upload(uploaded_files)
    if df.empty:
        st.warning("⚠ File parquet upload không có dữ liệu hợp lệ. Đang dùng DataFrame rỗng.")
    else:
        st.success(f"✅ Đang dùng dữ liệu từ {len(uploaded_files)} file parquet upload")
else:
    df = load_data()
    st.sidebar.info("📦 Đang dùng dữ liệu parquet mặc định trên server (load_data).")

df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
df = df.dropna(subset=["Ngày"])

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.header("🎛️ Bộ lọc dữ liệu (Tổng quan)")

    time_type = st.selectbox("Phân tích theo", ["Ngày", "Tuần", "Tháng", "Quý", "Năm"])

    start_date = st.date_input("Từ ngày", df["Ngày"].min())
    end_date   = st.date_input("Đến ngày", df["Ngày"].max())

    loaiCT_filter = st.multiselect("Loại CT", ["All"] + sorted(df["LoaiCT"].dropna().unique()))
    brand_filter  = st.multiselect("Brand", ["All"] + sorted(df["Brand"].dropna().unique()))
    region_filter = st.multiselect("Region", ["All"] + sorted(df["Region"].dropna().unique()))
    store_filter  = st.multiselect("Cửa hàng", ["All"] + sorted(df["Điểm_mua_hàng"].dropna().unique()))

# =====================================================
# CLEAN FILTER
# =====================================================
def clean_filter(values, all_values):
    if not values or "All" in values:
        return all_values
    return values

loaiCT_filter = clean_filter(loaiCT_filter, df["LoaiCT"].unique())
brand_filter  = clean_filter(brand_filter,  df["Brand"].unique())
region_filter = clean_filter(region_filter, df["Region"].unique())
store_filter  = clean_filter(store_filter,  df["Điểm_mua_hàng"].unique())

# =====================================================
# APPLY FILTER
# =====================================================
@st.cache_data(show_spinner=False)
def apply_filters(df, start_date, end_date, loaiCT, brand, region, store):
    return df[
        (df["Ngày"] >= start_date) &
        (df["Ngày"] <= end_date) &
        (df["LoaiCT"].isin(loaiCT)) &
        (df["Brand"].isin(brand)) &
        (df["Region"].isin(region)) &
        (df["Điểm_mua_hàng"].isin(store))
    ]

df_f = apply_filters(
    df,
    pd.to_datetime(start_date),
    pd.to_datetime(end_date),
    loaiCT_filter,
    brand_filter,
    region_filter,
    store_filter
)

# =====================================================
# TIME COLUMN
# =====================================================
df_f_time = df_f.copy()
if time_type == "Ngày":   df_f_time["Time"] = df_f_time["Ngày"].dt.date
elif time_type == "Tuần": df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("W").astype(str)
elif time_type == "Tháng": df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("M").astype(str)
elif time_type == "Quý":  df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("Q").astype(str)
elif time_type == "Năm":  df_f_time["Time"] = df_f_time["Ngày"].dt.year

# =====================================================
# KPI
# =====================================================
gross = df_f["Tổng_Gross"].sum()
net   = df_f["Tổng_Net"].sum()
orders = df_f["Số_CT"].nunique()
customers = df_f["Số_điện_thoại"].nunique()
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Gross", f"{gross:,.0f}")
c2.metric("Net", f"{net:,.0f}")
c3.metric("CK %", f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", orders)
c5.metric("Khách hàng", customers)

# =====================================================
# TIME GROUP
# =====================================================
@st.cache_data(show_spinner=False)
def group_time(df_f, time_type):
    freq_map = {"Ngày":"D","Tuần":"W","Tháng":"ME","Quý":"Q","Năm":"Y"}
    d = (
        df_f.set_index("Ngày")
        .resample(freq_map[time_type])
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique")
        )
        .reset_index()
    )
    d["CK_%"] = np.where(d["Gross"]>0, (1-d["Net"]/d["Gross"])*100, 0)
    d["Net_prev"] = d["Net"].shift(1)
    d["Growth_%"] = np.where(d["Net_prev"]>0, (d["Net"]-d["Net_prev"])/d["Net_prev"]*100, 0)
    return d

df_time = fix_float(group_time(df_f, time_type), ["CK_%", "Growth_%"])

st.subheader(f"⏱ Theo thời gian ({time_type})")
st.dataframe(df_time, width="stretch")

# =====================================================
# REGION + TIME
# =====================================================
@st.cache_data(show_spinner=False)
def group_region_time(df):
    d = (
        df.groupby(["Time","Region"])
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique")
        )
        .reset_index()
    )
    d["CK_%"] = np.where(d["Gross"]>0, (d["Gross"]-d["Net"])/d["Gross"]*100, 0)
    return d.sort_values(["Time","Net"], ascending=[True, False])

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
        Gross=("Tổng_Gross","sum"),
        Net=("Tổng_Net","sum"),
        Orders=("Số_CT","nunique"),
        Customers=("Số_điện_thoại","nunique")
    )
    .reset_index()
)
df_store["CK_%"] = np.where(
    df_store["Gross"]>0,
    (df_store["Gross"] - df_store["Net"]) / df_store["Gross"] * 100,
    0
).round(2)

st.dataframe(df_store.sort_values("Net", ascending=False), width="stretch")

# -------------------------
# Báo cáo nhóm sản phẩm
# -------------------------
df_product = df_f.copy()
st.subheader("📦 Theo Nhóm SP / Tên hàng")

col1,col2 = st.columns(2)
with col1:
    nhom_sp_selected = st.multiselect("📦 Chọn Nhóm SP", sorted(df_product["Nhóm_hàng"].dropna().unique()))
with col2:
    ten_sp_selected = st.multiselect("🏷️ Chọn Tên hàng", sorted(df_product["Mã_NB"].dropna().unique()))

if nhom_sp_selected:
    df_product = df_product[df_product["Nhóm_hàng"].isin(nhom_sp_selected)]
if ten_sp_selected:
    df_product = df_product[df_product["Mã_NB"].isin(ten_sp_selected)]

df_product_group = (
    df_product.groupby("Mã_NB")
    .agg(
        Gross=("Tổng_Gross","sum"),
        Net=("Tổng_Net","sum"),
        Orders=("Số_CT","nunique"),
        Customers=("Số_điện_thoại","nunique")
    )
    .reset_index()
    .sort_values("Net", ascending=False)
)

st.dataframe(df_product_group, width="stretch")
