# report.py
import streamlit as st
import pandas as pd
import plotly.express as px
from load_data import load_data, first_purchase  # <-- import từ load_data.py

st.set_page_config(page_title="Báo cáo Doanh thu", layout="wide")
st.title("Báo cáo Doanh thu")

# =====================
# Load dữ liệu
# =====================
df = load_data()  # <-- lấy df trực tiếp từ load_data.py
df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")

# =====================
# Sidebar: bộ lọc
# =====================
st.sidebar.header("Bộ lọc dữ liệu")
analysis_type = st.sidebar.selectbox("Chọn kiểu phân tích", ["Ngày", "Tuần", "Tháng", "Khoảng thời gian"])

start_date = st.sidebar.date_input("Từ ngày", pd.to_datetime("2025-05-01"))
end_date = st.sidebar.date_input("Đến ngày", pd.to_datetime("2025-08-31"))

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

# =====================
# Hàm gom nhóm + CK + Change%
# =====================
def grouped_summary(df, group_cols):
    df_grouped = df.groupby(group_cols, as_index=False)[["Tổng_Gross","Tổng_Net"]].sum()
    df_grouped["Tỷ_lệ_CK (%)"] = (1 - df_grouped["Tổng_Net"]/df_grouped["Tổng_Gross"])*100

    key_col = None
    if "Region" in group_cols: key_col = "Region"
    elif "Điểm_mua_hàng" in group_cols: key_col = "Điểm_mua_hàng"

    if key_col:
        df_grouped = df_grouped.sort_values([key_col] + [c for c in group_cols if c != key_col])
        df_grouped["Prev"] = df_grouped.groupby(key_col)["Tổng_Net"].shift(1)
        df_grouped["Change%"] = ((df_grouped["Tổng_Net"] - df_grouped["Prev"])/df_grouped["Prev"]*100).round(2)

    return df_grouped

def style_change(val):
    if pd.isna(val): return "-"
    arrow = "↑" if val > 0 else "↓" if val < 0 else "-"
    return f"{arrow} {abs(val):.2f}%"

# =====================
# Doanh thu theo Tuần / Tháng
# =====================
def summary_plot(df, freq, label):
    df_grouped = df.set_index("Ngày").resample(freq)[["Tổng_Gross","Tổng_Net"]].sum().reset_index()
    df_grouped["Tỷ_lệ_CK (%)"] = (1 - df_grouped["Tổng_Net"]/df_grouped["Tổng_Gross"])*100
    df_grouped["%_change_truoc"] = df_grouped["Tổng_Gross"].pct_change()*100
    df_grouped["%_change_sau"] = df_grouped["Tổng_Net"].pct_change()*100

    st.markdown(f"### 📊 Doanh thu theo {label}")
    st.dataframe(df_grouped)

    fig = px.line(df_grouped, x="Ngày", y=["Tổng_Gross","Tổng_Net"], markers=True,
                  title=f"Doanh thu theo {label}", color_discrete_sequence=["blue","red"])
    fig.update_layout(yaxis_title="VNĐ")
    st.plotly_chart(fig, use_container_width=True)
    return df_grouped

col1, col2 = st.columns(2)
with col1: df_week = summary_plot(df_filtered, "W", "Tuần")
with col2: df_month = summary_plot(df_filtered, "M", "Tháng")

# =====================
# Báo cáo Region
# =====================
st.subheader("🌍 Doanh thu theo Region")
if analysis_type == "Tuần":
    df_region = df_filtered.copy()
    df_region["Year"] = df_region["Ngày"].dt.year
    df_region["Period"] = df_region["Ngày"].dt.isocalendar().week
else:
    df_region = df_filtered.copy()
    df_region["Year"] = df_region["Ngày"].dt.year
    df_region["Period"] = df_region["Ngày"].dt.month

grouped_region = grouped_summary(df_region, ["Year","Period","Region"])
latest_year = grouped_region["Year"].max()
latest_period = grouped_region.loc[grouped_region["Year"]==latest_year,"Period"].max()
df_region_latest = grouped_region[(grouped_region["Year"]==latest_year) & (grouped_region["Period"]==latest_period)]
df_region_latest["Change%"] = df_region_latest["Change%"].apply(style_change)
st.data_editor(df_region_latest, use_container_width=True, hide_index=True)

df_region_melt = df_region_latest.melt(id_vars="Region", value_vars=["Tổng_Gross","Tổng_Net"],
                                       var_name="Loại doanh thu", value_name="Doanh thu")
fig_r = px.bar(df_region_melt, x="Region", y="Doanh thu", color="Loại doanh thu",
               barmode="group", title="Doanh thu theo Region")
st.plotly_chart(fig_r, use_container_width=True)

# =====================
# Báo cáo Điểm mua hàng
# =====================
st.subheader("🏪 Doanh thu theo Điểm mua hàng")
if analysis_type == "Ngày": df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.date
elif analysis_type == "Tuần": df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.strftime("%G-W%V")
else: df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.to_period("M").astype(str)

df_store = grouped_summary(df_filtered, ["Thời_gian","Điểm_mua_hàng"])
df_store = df_store.sort_values("Tổng_Net", ascending=False)
df_store["Change%"] = df_store["Change%"].apply(style_change)
st.data_editor(df_store, use_container_width=True, hide_index=True)

# =====================
# Top / Bottom 10 Store
# =====================
st.subheader("🏆 Top 10 Store")
st.data_editor(df_store.head(10), use_container_width=True, hide_index=True)
st.subheader("📉 Bottom 10 Store")
st.data_editor(df_store.tail(10), use_container_width=True, hide_index=True)

# =====================
# Top % Khách hàng
# =====================
st.sidebar.header("Top khách hàng")
top_percent_option = st.sidebar.number_input("Nhập % Top khách hàng", min_value=1, max_value=100, value=20, step=1)
doanh_thu_type = st.sidebar.selectbox("Loại doanh thu", ["Tổng_Net", "Tổng_Gross"])

st.subheader(f"💎 Top {top_percent_option}% Khách hàng theo {'Doanh thu sau CK' if doanh_thu_type=='Tổng_Net' else 'Doanh thu trước CK'}")
if "Số_điện_thoại" in df_filtered.columns:
    df_top_cust = df_filtered.groupby("Số_điện_thoại", as_index=False)[["Tổng_Gross","Tổng_Net"]].sum()
    df_top_cust["Tỷ_lệ_CK (%)"] = (1 - df_top_cust["Tổng_Net"]/df_top_cust["Tổng_Gross"])*100
    df_top_cust = df_top_cust.sort_values(doanh_thu_type, ascending=False)
    top_n = max(1,int(len(df_top_cust)*top_percent_option/100))
    st.data_editor(df_top_cust.head(top_n), use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ Không tìm thấy cột 'Số_điện_thoại' trong dữ liệu.")
