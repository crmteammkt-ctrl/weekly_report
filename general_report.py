import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from load_data import load_data, first_purchase

# ==================================================
# PAGE CONFIG (PHẢI ĐẶT ĐẦU FILE)
# ==================================================
st.set_page_config(
    page_title="Marketing Revenue Dashboard",
    layout="wide"
)

st.title("📊 MARKETING REVENUE DASHBOARD")

# ==================================================
# UTILS
# ==================================================
@st.cache_data
def to_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()


def clean_filter(values, all_values):
    if not values or "All" in values:
        return all_values
    return values


# ==================================================
# LOAD DATA (CACHED)
# ==================================================
df = load_data()
df_fp = first_purchase()

# Fix NaT
df = df.dropna(subset=["Ngày"])
df["Ngày"] = pd.to_datetime(df["Ngày"])

# ==================================================
# SIDEBAR FILTERS
# ==================================================
with st.sidebar:
    st.header("🎛️ Bộ lọc dữ liệu")

    time_type = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý", "Năm"]
    )

    min_date = df["Ngày"].min().date()
    max_date = df["Ngày"].max().date()

    start_date = st.date_input("Từ ngày", min_date)
    end_date   = st.date_input("Đến ngày", max_date)

    loaiCT_filter = st.multiselect(
        "Loại CT",
        ["All"] + sorted(df["LoaiCT"].dropna().unique())
    )

    brand_filter = st.multiselect(
        "Brand",
        ["All"] + sorted(df["Brand"].dropna().unique())
    )

    region_filter = st.multiselect(
        "Region",
        ["All"] + sorted(df["Region"].dropna().unique())
    )

    store_filter = st.multiselect(
        "Cửa hàng",
        ["All"] + sorted(df["Điểm_mua_hàng"].dropna().unique())
    )


# ==================================================
# APPLY FILTERS
# ==================================================
df_f = df[
    (df["Ngày"] >= pd.to_datetime(start_date)) &
    (df["Ngày"] <= pd.to_datetime(end_date)) &
    (df["LoaiCT"].isin(clean_filter(loaiCT_filter, df["LoaiCT"].unique()))) &
    (df["Brand"].isin(clean_filter(brand_filter, df["Brand"].unique()))) &
    (df["Region"].isin(clean_filter(region_filter, df["Region"].unique()))) &
    (df["Điểm_mua_hàng"].isin(clean_filter(store_filter, df["Điểm_mua_hàng"].unique())))
].copy()

# ==================================================
# KPI SUMMARY
# ==================================================
gross = df_f["Tổng_Gross"].sum()
net = df_f["Tổng_Net"].sum()
orders = df_f["Số_CT"].nunique()
customers = df_f["Số_điện_thoại"].nunique()
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gross", f"{gross:,.0f}")
c2.metric("Net", f"{net:,.0f}")
c3.metric("CK %", f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", orders)
c5.metric("Khách hàng", customers)

st.divider()

# ==================================================
# TIME SERIES REPORT
# ==================================================
freq_map = {
    "Ngày": "D",
    "Tuần": "W",
    "Tháng": "M",
    "Quý": "Q",
    "Năm": "Y"
}

df_time = (
    df_f
    .set_index("Ngày")
    .resample(freq_map[time_type])
    .agg(
        Gross=("Tổng_Gross", "sum"),
        Net=("Tổng_Net", "sum"),
        Orders=("Số_CT", "nunique"),
        Customers=("Số_điện_thoại", "nunique")
    )
    .reset_index()
)

df_time["CK_%"] = (1 - df_time["Net"] / df_time["Gross"]) * 100
df_time["Growth_%"] = df_time["Net"].pct_change() * 100

st.subheader("📈 Doanh thu theo thời gian")
st.dataframe(df_time, use_container_width=True)

st.download_button(
    "⬇️ Tải Excel",
    to_excel(df_time),
    file_name="revenue_time.xlsx"
)

st.divider()

# ==================================================
# GROUP REPORTS
# ==================================================
@st.cache_data
def revenue_group(df, col):
    return (
        df.groupby(col, dropna=False)
        .agg(
            Gross=("Tổng_Gross", "sum"),
            Net=("Tổng_Net", "sum"),
            Orders=("Số_CT", "nunique"),
            Customers=("Số_điện_thoại", "nunique")
        )
        .reset_index()
        .sort_values("Net", ascending=False)
    )

col1, col2 = st.columns(2)

with col1:
    st.subheader("🏷️ Theo Brand")
    df_brand = revenue_group(df_f, "Brand")
    st.dataframe(df_brand, use_container_width=True)

with col2:
    st.subheader("📍 Theo Region")
    df_region = revenue_group(df_f, "Region")
    st.dataframe(df_region, use_container_width=True)

st.divider()

# ==================================================
# FIRST PURCHASE / NEW vs RETURNING
# ==================================================
df_merge = df_f.merge(
    df_fp,
    on="Số_điện_thoại",
    how="left"
)

df_merge["Customer_Type"] = np.where(
    df_merge["Ngày"] == df_merge["First_Date"],
    "Khách mới",
    "Khách quay lại"
)

st.subheader("👥 Khách mới vs Khách quay lại")
df_customer_type = revenue_group(df_merge, "Customer_Type")
st.dataframe(df_customer_type, use_container_width=True)
