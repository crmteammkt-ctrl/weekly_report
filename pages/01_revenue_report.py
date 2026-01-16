import streamlit as st
import pandas as pd
import plotly.express as px

from load_data import load_data  # dùng chung dữ liệu Parquet

# KHÔNG set_page_config ở đây, chỉ để ở general_report.py là đủ
st.title("📈 Báo cáo Doanh thu")

# =====================
# Load dữ liệu
# =====================
df = load_data()  # load_data bên trong đã chuẩn hoá Ngày
df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")

# =====================
# Sidebar: bộ lọc
# =====================
st.sidebar.header("Bộ lọc dữ liệu (Doanh thu)")

analysis_type = st.sidebar.selectbox(
    "Chọn kiểu phân tích",
    ["Ngày", "Tuần", "Tháng", "Khoảng thời gian"],
    key="rev_analysis_type"
)

start_date = st.sidebar.date_input(
    "Từ ngày",
    df["Ngày"].min(),
    key="rev_start_date"
)
end_date = st.sidebar.date_input(
    "Đến ngày",
    df["Ngày"].max(),
    key="rev_end_date"
)

brands  = sorted(df["Brand"].dropna().unique())
regions = sorted(df["Region"].dropna().unique())
stores  = sorted(df["Điểm_mua_hàng"].dropna().unique())
loaicts = sorted(df["LoaiCT"].dropna().unique())

brand_filter  = st.sidebar.multiselect(
    "Chọn Brand",
    ["Tất cả"] + brands,
    default=["Tất cả"],
    key="rev_brand_filter"
)
region_filter = st.sidebar.multiselect(
    "Chọn Region",
    ["Tất cả"] + regions,
    default=["Tất cả"],
    key="rev_region_filter"
)
store_filter  = st.sidebar.multiselect(
    "Chọn Điểm mua hàng",
    ["Tất cả"] + stores,
    default=["Tất cả"],
    key="rev_store_filter"
)
loaiCT_filter = st.sidebar.multiselect(
    "Chọn Loại CT",
    ["Tất cả"] + loaicts,
    default=["Tất cả"],
    key="rev_loaiCT_filter"
)

# =====================
# Xử lý "Tất cả"
# =====================
if "Tất cả" in brand_filter:
    brand_filter = brands
if "Tất cả" in region_filter:
    region_filter = regions
if "Tất cả" in store_filter:
    store_filter = stores
if "Tất cả" in loaiCT_filter:
    loaiCT_filter = loaicts

# =====================
# Lọc dữ liệu
# =====================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))
mask &= df["Brand"].isin(brand_filter)
mask &= df["Region"].isin(region_filter)
mask &= df["Điểm_mua_hàng"].isin(store_filter)
mask &= df["LoaiCT"].isin(loaiCT_filter)

df_filtered = df[mask].copy()

# =====================
# Tuỳ kiểu phân tích thời gian
# =====================
if analysis_type == "Ngày":
    df_filtered["Time"] = df_filtered["Ngày"].dt.date
elif analysis_type == "Tuần":
    df_filtered["Time"] = df_filtered["Ngày"].dt.to_period("W").astype(str)
elif analysis_type == "Tháng":
    df_filtered["Time"] = df_filtered["Ngày"].dt.to_period("M").astype(str)
elif analysis_type == "Khoảng thời gian":
    # giữ nguyên Ngày, không gom nhóm
    df_filtered["Time"] = df_filtered["Ngày"].dt.date

# =====================
# KPI tổng
# =====================
gross_total = df_filtered["Tổng_Gross"].sum()
net_total   = df_filtered["Tổng_Net"].sum()
orders      = df_filtered["Số_CT"].nunique()
customers   = df_filtered["Số_điện_thoại"].nunique()
ck_rate     = (1 - net_total / gross_total) * 100 if gross_total > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gross", f"{gross_total:,.0f}")
c2.metric("Net", f"{net_total:,.0f}")
c3.metric("CK %", f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", orders)
c5.metric("Khách hàng", customers)

# =====================
# Biểu đồ doanh thu theo thời gian
# =====================
st.subheader(f"📊 Doanh thu theo {analysis_type}")

df_time = (
    df_filtered
    .groupby("Time", as_index=False)
    .agg(Net=("Tổng_Net", "sum"), Gross=("Tổng_Gross", "sum"))
    .sort_values("Time")
)

if not df_time.empty:
    fig = px.line(
        df_time,
        x="Time",
        y="Net",
        title="Doanh thu Net theo thời gian"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Không có dữ liệu sau khi lọc.")

# =====================
# Bảng dữ liệu chi tiết
# =====================
st.subheader("📑 Dữ liệu đã lọc")
st.dataframe(df_filtered, use_container_width=True)
