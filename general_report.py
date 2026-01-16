import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

from load_data import load_data  # đọc Parquet


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
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Marketing Revenue Dashboard", layout="wide")
st.title("📊 MARKETING REVENUE DASHBOARD – OVERVIEW")


# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data(show_spinner="📦 Đang load dữ liệu...")
def _load_df():
    return load_data()

try:
    df = _load_df()
except Exception as e:
    st.error("❌ Lỗi khi load dữ liệu. Kiểm tra lại file Parquet / load_data.py")
    st.exception(e)
    st.stop()

# =====================================================
# SIDEBAR – BỘ LỌC CHUNG
# =====================================================
with st.sidebar:
    st.header("🗂 Thông tin dữ liệu")

    st.caption(
        f"📆 Từ: **{df['Ngày'].min().date()}**  →  Đến: **{df['Ngày'].max().date()}**"
    )
    st.caption(f"👥 Khách hàng: **{df['Số_điện_thoại'].nunique():,}**")
    st.caption(f"🧾 Đơn hàng: **{df['Số_CT'].nunique():,}**")
    st.caption(f"📦 Dòng dữ liệu: **{len(df):,}**")

    st.markdown("---")
    st.header("🎛️ Bộ lọc dữ liệu")

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
brand_filter  = clean_filter(brand_filter, df["Brand"].unique())
region_filter = clean_filter(region_filter, df["Region"].unique())
store_filter  = clean_filter(store_filter, df["Điểm_mua_hàng"].unique())


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
if time_type == "Ngày":
    df_f_time["Time"] = df_f_time["Ngày"].dt.date
elif time_type == "Tuần":
    df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("W").astype(str)
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
net   = df_f["Tổng_Net"].sum()
orders = df_f["Số_CT"].nunique()
customers = df_f["Số_điện_thoại"].nunique()
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
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
    freq_map = {"Ngày": "D", "Tuần": "W", "Tháng": "M", "Quý": "Q", "Năm": "Y"}
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


df_time = fix_float(group_time(df_f, time_type), ["CK_%", "Growth_%"])

st.subheader(f"⏱ Hiệu quả theo {time_type}")
st.dataframe(df_time, width="stretch")


# =====================================================
# REGION + TIME
# =====================================================
@st.cache_data(show_spinner=False)
def group_region_time(df):
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
    d["CK_%"] = np.where(d["Gross"] > 0, (d["Gross"] - d["Net"]) / d["Gross"] * 100, 0)
    return d.sort_values(["Time", "Net"], ascending=[True, False])


df_region_time = fix_float(group_region_time(df_f_time), ["CK_%"])
st.subheader(f"🌍 Theo Region + {time_type}")
st.dataframe(df_region_time, width="stretch")


# -------------------------
# Báo cáo cửa hàng
# -------------------------
st.subheader("🏪 Theo Cửa hàng")
st.markdown("### ⏱️ Bộ lọc thời gian (riêng cho bảng Cửa hàng)")

df_store = df_f.copy()
df_store["Day"] = df_store["Ngày"].dt.date
df_store["Week"] = df_store["Ngày"].dt.to_period("W").astype(str)
df_store["Month"] = df_store["Ngày"].dt.to_period("M").astype(str)
df_store["Quarter"] = df_store["Ngày"].dt.to_period("Q").astype(str)
df_store["Year"] = df_store["Ngày"].dt.year

if time_type == "Ngày":
    min_day = df_store["Day"].min()
    max_day = df_store["Day"].max()
    date_range = st.date_input(
        "📅 Chọn khoảng ngày (riêng cho bảng Cửa hàng)",
        value=(min_day, max_day),
        min_value=min_day,
        max_value=max_day,
    )
    if len(date_range) == 2:
        start_d, end_d = date_range
        df_store = df_store[(df_store["Day"] >= start_d) & (df_store["Day"] <= end_d)]
elif time_type == "Tuần":
    week_selected = st.selectbox("📅 Chọn tuần", sorted(df_store["Week"].unique()))
    df_store = df_store[df_store["Week"] == week_selected]
elif time_type == "Tháng":
    month_selected = st.selectbox("📅 Chọn tháng", sorted(df_store["Month"].unique()))
    df_store = df_store[df_store["Month"] == month_selected]
elif time_type == "Quý":
    quarter_selected = st.selectbox("📅 Chọn quý", sorted(df_store["Quarter"].unique()))
    df_store = df_store[df_store["Quarter"] == quarter_selected]
elif time_type == "Năm":
    year_selected = st.selectbox("📅 Chọn năm", sorted(df_store["Year"].unique()))
    df_store = df_store[df_store["Year"] == year_selected]


@st.cache_data(show_spinner=False)
def group_store(df_store):
    d = (
        df_store.groupby("Điểm_mua_hàng")
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
    ).round(2)

    return d.sort_values("Net", ascending=False)


df_store_group = group_store(df_store)
st.dataframe(df_store_group, width="stretch")


# -------------------------
# Báo cáo nhóm sản phẩm
# -------------------------
df_product = df_f.copy()
st.subheader("📦 Theo Nhóm SP / Tên hàng")

col1, col2 = st.columns(2)
with col1:
    nhom_sp_selected = st.multiselect(
        "📦 Chọn Nhóm SP", sorted(df_product["Nhóm_hàng"].dropna().unique())
    )
with col2:
    ten_sp_selected = st.multiselect(
        "🏷️ Chọn Tên hàng", sorted(df_product["Tên_hàng"].dropna().unique())
    )

if nhom_sp_selected:
    df_product = df_product[df_product["Nhóm_hàng"].isin(nhom_sp_selected)]
if ten_sp_selected:
    df_product = df_product[df_product["Tên_hàng"].isin(ten_sp_selected)]


@st.cache_data(show_spinner=False)
def group_product(df):
    return (
        df.groupby("Tên_hàng")
        .agg(
            Gross=("Tổng_Gross", "sum"),
            Net=("Tổng_Net", "sum"),
            Orders=("Số_CT", "nunique"),
            Customers=("Số_điện_thoại", "nunique"),
        )
        .reset_index()
        .sort_values("Net", ascending=False)
    )


df_product_group = group_product(df_product)
st.dataframe(df_product_group, width="stretch")

st.info("👉 Các báo cáo CRM, Pareto, Cohort nằm ở trang **CRM & Cohort** trong sidebar (pages).")
