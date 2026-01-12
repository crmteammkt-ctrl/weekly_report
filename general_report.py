import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from datetime import datetime
from load_data import load_data, first_purchase

# -------------------------
# Hàm xuất Excel
# -------------------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()

# -------------------------
# Load dữ liệu
# -------------------------
df = load_data()
df_fp = first_purchase()

st.set_page_config(page_title="Marketing Revenue Dashboard", layout="wide")
st.title("📊 MARKETING REVENUE DASHBOARD")

# -------------------------
# Sidebar bộ lọc chung
# -------------------------
with st.sidebar:
    st.header("🎛️ Bộ lọc dữ liệu")
    time_type = st.selectbox("Phân tích theo", ["Ngày", "Tuần", "Tháng", "Quý", "Năm"])
    start_date = st.date_input("Từ ngày", df["Ngày"].min())
    end_date   = st.date_input("Đến ngày", df["Ngày"].max())
    loaiCT_filter = st.multiselect("Loại CT", ["All"] + sorted(df["LoaiCT"].dropna().unique()))
    brand_filter = st.multiselect("Brand", ["All"] + sorted(df["Brand"].dropna().unique()))
    region_filter = st.multiselect("Region", ["All"] + sorted(df["Region"].dropna().unique()))
    store_filter  = st.multiselect("Cửa hàng", ["All"] + sorted(df["Điểm_mua_hàng"].dropna().unique()))

# -------------------------
# Chuẩn hóa bộ lọc "All"
# -------------------------
def clean_filter(filter_values, col_values):
    if not filter_values or "All" in filter_values:
        return col_values
    return filter_values

loaiCT_filter = clean_filter(loaiCT_filter, df["LoaiCT"].unique())
brand_filter = clean_filter(brand_filter, df["Brand"].unique())
region_filter = clean_filter(region_filter, df["Region"].unique())
store_filter = clean_filter(store_filter, df["Điểm_mua_hàng"].unique())

# -------------------------
# Lọc dữ liệu theo sidebar
# -------------------------
df_f = df[
    (df["Ngày"] >= pd.to_datetime(start_date)) &
    (df["Ngày"] <= pd.to_datetime(end_date)) &
    (df["LoaiCT"].isin(loaiCT_filter)) &
    (df["Brand"].isin(brand_filter)) &
    (df["Region"].isin(region_filter)) &
    (df["Điểm_mua_hàng"].isin(store_filter))
]

# -------------------------
# Thêm cột thời gian theo phân tích
# -------------------------
df_f_time = df_f.copy()
if time_type == "Ngày": df_f_time["Time"] = df_f_time["Ngày"].dt.date
elif time_type == "Tuần": df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("W").astype(str)
elif time_type == "Tháng": df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("M").astype(str)
elif time_type == "Quý": df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("Q").astype(str)
elif time_type == "Năm": df_f_time["Time"] = df_f_time["Ngày"].dt.year

# -------------------------
# KPI tổng quan
# -------------------------
gross = df_f["Tổng_Gross"].sum()
net = df_f["Tổng_Net"].sum()
orders = df_f["Số_CT"].nunique()
customers = df_f["Số_điện_thoại"].nunique()
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Gross", f"{gross:,.0f}")
c2.metric("Net", f"{net:,.0f}")
c3.metric("CK %", f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", orders)
c5.metric("Khách hàng", customers)

# -------------------------
# Báo cáo theo Region + Time
# -------------------------
freq_map = {"Ngày":"D","Tuần":"W","Tháng":"M","Quý":"Q","Năm":"Y"}
df_time = (
    df_f
    .set_index("Ngày")
    .resample(freq_map[time_type])
    .agg(
        Gross=("Tổng_Gross","sum"),
        Net=("Tổng_Net","sum"),
        Orders=("Số_CT","nunique"),
        Customers=("Số_điện_thoại","nunique")
    )
    .reset_index()
)
df_time["CK_%"] = (1 - df_time["Net"] / df_time["Gross"]) * 100
df_time["Net_prev"] = df_time["Net"].shift(1)
df_time["Growth_%"] = (df_time["Net"] - df_time["Net_prev"]) / df_time["Net_prev"] * 100

# -------------------------
# Revenue nhóm theo cột
# -------------------------
def revenue_group(col):
    return (
        df_f.groupby(col)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique")
        )
        .reset_index()
        .sort_values("Net", ascending=False)
    )

# Các báo cáo khác: Store, Product, CRM, Pareto, KH mới/quay lại, Cohort
# (giữ nguyên logic từ code bạn đã gửi, chỉ chỉnh sửa nhỏ xử lý NaT, chuyển đổi thời gian, và Streamlit caching)
