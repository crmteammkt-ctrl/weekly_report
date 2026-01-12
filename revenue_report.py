import streamlit as st
import pandas as pd
import plotly.express as px
from load_data import load_data, first_purchase

st.set_page_config(page_title="Báo cáo Doanh thu", layout="wide")
st.title("Báo cáo Doanh thu")

# =====================
# Load dữ liệu
# =====================
df = load_data()
df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")

# =====================
# Sidebar: bộ lọc
# =====================
st.sidebar.header("Bộ lọc dữ liệu")
analysis_type = st.sidebar.selectbox("Chọn kiểu phân tích", ["Ngày", "Tuần", "Tháng", "Khoảng thời gian"])

start_date = st.sidebar.date_input("Từ ngày", df["Ngày"].min())
end_date = st.sidebar.date_input("Đến ngày", df["Ngày"].max())

brands  = sorted(df["Brand"].dropna().unique())
regions = sorted(df["Region"].dropna().unique())
stores  = sorted(df["Điểm_mua_hàng"].dropna().unique())
loaicts = sorted(df["LoaiCT"].dropna().unique()) 

brand_filter  = st.sidebar.multiselect("Chọn Brand", ["Tất cả"] + brands, default=["Tất cả"])
region_filter = st.sidebar.multiselect("Chọn Region", ["Tất cả"] + regions, default=["Tất cả"])
store_filter  = st.sidebar.multiselect("Chọn Điểm mua hàng", ["Tất cả"] + stores, default=["Tất cả"])
loaiCT_filter = st.sidebar.multiselect("Chọn Loại CT", ["Tất cả"] + loaicts, default=["Tất cả"])

# =====================
# Xử lý "Tất cả"
# =====================
if "Tất cả" in brand_filter: brand_filter = brands
if "Tất cả" in region_filter: region_filter = regions
if "Tất cả" in store_filter: store_filter = stores
if "Tất cả" in loaiCT_filter: loaiCT_filter = loaicts

# =====================
# Lọc dữ liệu
# =====================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))
mask &= df["Brand"].isin(brand_filter)
mask &= df["Region"].isin(region_filter)
mask &= df["Điểm_mua_hàng"].isin(store_filter)
mask &= df["LoaiCT"].isin(loaiCT_filter)
df_filtered = df[mask]

st.subheader("📑 Dữ liệu đã lọc")
st.dataframe(df_filtered)
