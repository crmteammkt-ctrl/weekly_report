import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import plotly.express as px
import requests


# https://drive.google.com/file/d/1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH/view?usp=sharing
# 1. ID file Google Drive bạn đã lấy ở bước trước
# Ví dụ: link là https://drive.google.com/file/d/1abc123.../view -> ID là 1abc123...
GOOGLE_DRIVE_FILE_ID = '1ETbZl4gU4uqneZ8sJKtXbS80gMgRcuzH'
DB_PATH = "thiensondb.db" # Chỉ để tên file, không để ổ đĩa D:/

@st.cache_resource
def download_database():
    """Hàm này giúp tải file từ Google Drive về server Streamlit"""
    if not os.path.exists(DB_PATH):
        with st.spinner('Đang tải dữ liệu từ Google Drive (500MB)... Vui lòng đợi trong giây lát.'):
            url = f'https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}'
            response = requests.get(url, stream=True)
            with open(DB_PATH, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


st.set_page_config(page_title="Báo cáo Doanh thu", layout="wide")
st.title("Báo cáo Doanh thu")


# Lấy dữ liệu 1 lần
conn = download_database()
df = pd.read_sql("""
   SELECT Ngày, Brand, Region, Điểm_mua_hàng, LoaiCT, Tổng_Gross, Tổng_Net, Số_điện_thoại
   FROM tinhhinhbanhang
""", conn)
conn.close()

df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")

# Lấy danh sách cho bộ lọc
brands  = sorted(df["Brand"].dropna().unique().tolist())
regions = sorted(df["Region"].dropna().unique().tolist())
stores  = sorted(df["Điểm_mua_hàng"].dropna().unique().tolist())
loaicts = sorted(df["LoaiCT"].dropna().unique().tolist()) 
# =====================
# Bộ lọc sidebar
# =====================
with st.sidebar:
    st.header("Bộ lọc dữ liệu")
    analysis_type = st.selectbox(
        "Chọn kiểu phân tích", 
        ["Ngày", "Tuần", "Tháng", "Khoảng thời gian"]
    )

    if analysis_type == "Khoảng thời gian":
        start_date = st.date_input("Từ ngày", pd.to_datetime("2025-05-01"))
        end_date   = st.date_input("Đến ngày", pd.to_datetime("2025-08-31"))
    else:
        start_date = st.date_input("Từ ngày", pd.to_datetime("2025-05-01"))
        end_date   = st.date_input("Đến ngày", pd.to_datetime("2025-08-31"))


    # Bộ lọc nhiều lựa chọn
    brand_filter = st.multiselect("Chọn Brand", ["Tất cả"] + brands, default=["Tất cả"])
    region_filter = st.multiselect("Chọn Region", ["Tất cả"] + regions, default=["Tất cả"])
    store_filter  = st.multiselect("Chọn Điểm mua hàng", ["Tất cả"] + stores, default=["Tất cả"])
    loaiCT_filter = st.multiselect("Chọn Loại CT", ["Tất cả"] + loaicts, default=["Tất cả"])

# Xử lý giá trị "Tất cả"
if "Tất cả" in brand_filter:
    brand_filter = brands
if "Tất cả" in region_filter:
    region_filter = regions
if "Tất cả" in store_filter:
    store_filter = stores

# Lọc dữ liệu
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))
mask &= df["Brand"].isin(brand_filter)
mask &= df["Region"].isin(region_filter)
mask &= df["Điểm_mua_hàng"].isin(store_filter)

df_filtered = df[mask]


st.subheader("📑 Dữ liệu đã lọc")
st.dataframe(df_filtered)

# =====================
# Gom dữ liệu theo tuần & tháng
# =====================
def summary_with_discount(df, freq, label):
    df_group = df.set_index("Ngày").resample(freq)[["Tổng_Gross", "Tổng_Net"]].sum().reset_index()
    df_group["Tỷ_lệ_CK (%)"] = (1 - df_group["Tổng_Net"] / df_group["Tổng_Gross"]) * 100
    df_group["%_change_truoc"] = df_group["Tổng_Gross"].pct_change() * 100
    df_group["%_change_sau"]   = df_group["Tổng_Net"].pct_change() * 100
    st.markdown(f"### 📊 Doanh thu theo {label}")
    st.dataframe(df_group)

    fig = px.line(
        df_group,
        x="Ngày",
        y=["Tổng_Gross", "Tổng_Net"],
        markers=True,
        title=f"Doanh thu theo {label}",
        color_discrete_sequence=["blue","red"]
    )
    fig.update_layout(yaxis_title="VNĐ")
    st.plotly_chart(fig, use_container_width=True)


    return df_group

col1, col2 = st.columns(2)
with col1:
    df_week = summary_with_discount(df_filtered, "W", "Tuần")
with col2:
    df_month = summary_with_discount(df_filtered, "M", "Tháng")

# =====================
# Báo cáo theo Region
# =====================
st.subheader("🌍 Doanh thu theo Region")

# Tạo Year/Period giống Top/Bottom 10
if analysis_type == "Tuần":
    df_region = df_filtered.copy()
    df_region["Year"] = df_region["Ngày"].dt.year
    df_region["Period"] = df_region["Ngày"].dt.isocalendar().week
elif analysis_type == "Tháng":
    df_region = df_filtered.copy()
    df_region["Year"] = df_region["Ngày"].dt.year
    df_region["Period"] = df_region["Ngày"].dt.month
else:
    df_region = df_filtered.copy()
    df_region["Year"] = df_region["Ngày"].dt.year
    df_region["Period"] = df_region["Ngày"].dt.month   # mặc định gom theo tháng

# Gom nhóm theo Region + kỳ
grouped_region = df_region.groupby(["Year","Period","Region"], as_index=False)[
    ["Tổng_Gross","Tổng_Net"]
].sum()

grouped_region["Tỷ_lệ_CK (%)"] = (1 - grouped_region["Tổng_Gross"]/grouped_region["Tổng_Net"]) * 100

# Tính kỳ trước
grouped_region = grouped_region.sort_values(["Region","Year","Period"])
grouped_region["Prev"] = grouped_region.groupby("Region")["Tổng_Net"].shift(1)
grouped_region["Change%"] = ((grouped_region["Tổng_Net"] - grouped_region["Prev"]) / grouped_region["Prev"] * 100).round(2)

# Lấy kỳ mới nhất
latest_year = grouped_region["Year"].max()
latest_period = grouped_region.loc[grouped_region["Year"]==latest_year, "Period"].max()
df_region_latest = grouped_region[(grouped_region["Year"]==latest_year) & (grouped_region["Period"]==latest_period)]

# Hiển thị bảng với cột màu xanh/đỏ
def style_change(val):
    if pd.isna(val):
        return ""
    arrow = "↑" if val > 0 else "↓" if val < 0 else "-"
    color = "green" if val > 0 else "red" if val < 0 else "gray"
    return f"{arrow} {val:.2f}%"  # chỉ hiển thị text, màu để style sau

styled_df = df_region_latest[["Region","Tổng_Gross","Tổng_Net","Tỷ_lệ_CK (%)","Prev","Change%"]].copy()
styled_df["Change%"] = df_region_latest["Change%"].apply(style_change)

st.data_editor(
    styled_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Tổng_Gross": st.column_config.NumberColumn("Doanh thu trước CK", format="%.0f"),
        "Tổng_Net": st.column_config.NumberColumn("Doanh thu sau CK", format="%.0f"),
        "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f %%"),
        "Prev": st.column_config.NumberColumn("Doanh thu kỳ trước", format="%.0f"),
        "Change%": st.column_config.TextColumn("Tăng/giảm (%)"),  # text có mũi tên
    }
)

# Biểu đồ vẫn giữ nguyên
df_region_melt = df_region_latest.melt(
    id_vars="Region",
    value_vars=["Tổng_Gross", "Tổng_Net"],
    var_name="Loại doanh thu",
    value_name="Doanh thu"
)

fig_r = px.bar(
    df_region_melt,
    x="Region",
    y="Doanh thu",
    color="Loại doanh thu",
    barmode="group",
    title="Doanh thu theo Region"
)
st.plotly_chart(fig_r, use_container_width=True)



# =====================# Báo cáo theo Điểm mua hàng
# =====================
st.subheader("🏪 Doanh thu theo Điểm mua hàng")

if analysis_type == "Ngày":
    df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.date
elif analysis_type == "Tuần":
    df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.strftime("%G-W%V")
elif analysis_type == "Tháng":
    df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.to_period("M").astype(str)
else:
    df_filtered["Thời_gian"] = "Tất cả"

df_store = df_filtered.groupby(["Thời_gian", "Điểm_mua_hàng"])[["Tổng_Gross", "Tổng_Net"]].sum().reset_index()
df_store["Tỷ_lệ_CK (%)"] = (1 - df_store["Tổng_Net"] / df_store["Tổng_Gross"]) * 100
df_store = df_store.sort_values(by="Tổng_Net", ascending=False)

st.data_editor(
    df_store,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Tổng_Gross": st.column_config.NumberColumn(format="%.0f"),
        "Tổng_Net": st.column_config.NumberColumn(format="%.0f"),
        "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(format="%.2f %%"),
    }
)

df_store_melt = df_store.melt(
    id_vars=["Thời_gian", "Điểm_mua_hàng"],
    value_vars=["Tổng_Gross", "Tổng_Net"],
    var_name="Loại doanh thu",
    value_name="Doanh thu"
)

fig_store = px.bar(
    df_store_melt,
    x="Doanh thu",
    y="Điểm_mua_hàng",
    color="Loại doanh thu",
    orientation="h",
    barmode="group",
    title="Doanh thu theo Điểm mua hàng (sắp xếp giảm dần)",
    height=900
)
fig_store.update_layout(yaxis=dict(autorange="reversed"))
st.plotly_chart(fig_store, use_container_width=True)

# =====================
# Top 10 điểm mua hàng
# =====================
st.subheader("🏆 Top 10 Điểm mua hàng có Doanh thu cao nhất")

if analysis_type == "Tuần":
    df_group = df_filtered.copy()
    df_group["Year"] = df_group["Ngày"].dt.year
    df_group["Period"] = df_group["Ngày"].dt.isocalendar().week
elif analysis_type == "Tháng":
    df_group = df_filtered.copy()
    df_group["Year"] = df_group["Ngày"].dt.year
    df_group["Period"] = df_group["Ngày"].dt.month
else:
    # Nếu là Ngày hoặc Khoảng TG thì mặc định gom theo tháng
    df_group = df_filtered.copy()
    df_group["Year"] = df_group["Ngày"].dt.year
    df_group["Period"] = df_group["Ngày"].dt.month

# Gom nhóm đầy đủ
grouped = df_group.groupby(["Year","Period","Điểm_mua_hàng"], as_index=False)[
    ["Tổng_Gross","Tổng_Net"]
].sum()

# Tính tỷ lệ CK
grouped["Tỷ_lệ_CK (%)"] = (1 - grouped["Tổng_Net"]/grouped["Tổng_Gross"]) * 100

# Sắp xếp và tính kỳ trước
grouped = grouped.sort_values(["Điểm_mua_hàng","Year","Period"])
grouped["Prev"] = grouped.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
grouped["Change%"] = ((grouped["Tổng_Net"] - grouped["Prev"]) / grouped["Prev"] * 100).round(2)

# Lấy kỳ mới nhất
latest_year = grouped["Year"].max()
latest_period = grouped.loc[grouped["Year"]==latest_year, "Period"].max()
df_latest = grouped[(grouped["Year"]==latest_year) & (grouped["Period"]==latest_period)]

# Top 10
df_top10 = df_latest.sort_values(by="Tổng_Net", ascending=False).head(10)

# Hiển thị
st.data_editor(
    df_top10,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Tổng_Gross": st.column_config.NumberColumn("Doanh thu trước CK", format="%.0f"),
        "Tổng_Net": st.column_config.NumberColumn("Doanh thu sau CK", format="%.0f"),
        "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f %%"),
        "Prev": st.column_config.NumberColumn("Doanh thu kỳ trước", format="%.0f"),
        "Change%": st.column_config.NumberColumn("Tăng/giảm (%)", format="%.2f %%"),
    }
)

# =====================
# Bottom 10 điểm mua hàng
# =====================
st.subheader("📉 Top 10 Điểm mua hàng có Doanh thu thấp nhất")

# Gom nhóm giống Top 10
grouped = df_group.groupby(["Year","Period","Điểm_mua_hàng"], as_index=False)[
    ["Tổng_Gross","Tổng_Net"]
].sum()

grouped["Tỷ_lệ_CK (%)"] = (1 - grouped["Tổng_Net"]/grouped["Tổng_Gross"]) * 100

grouped = grouped.sort_values(["Điểm_mua_hàng","Year","Period"])
grouped["Prev"] = grouped.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
grouped["Change%"] = ((grouped["Tổng_Net"] - grouped["Prev"]) / grouped["Prev"] * 100).round(2)

latest_year = grouped["Year"].max()
latest_period = grouped.loc[grouped["Year"]==latest_year, "Period"].max()
df_latest = grouped[(grouped["Year"]==latest_year) & (grouped["Period"]==latest_period)]

df_bottom10 = df_latest.sort_values(by="Tổng_Net", ascending=True).head(10)

st.data_editor(
    df_bottom10,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Tổng_Gross": st.column_config.NumberColumn("Doanh thu trước CK", format="%.0f"),
        "Tổng_Net": st.column_config.NumberColumn("Doanh thu sau CK", format="%.0f"),
        "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f %%"),
        "Prev": st.column_config.NumberColumn("Doanh thu kỳ trước", format="%.0f"),
        "Change%": st.column_config.NumberColumn("Tăng/giảm (%)", format="%.2f %%"),
    }
)

# =====================
# Xuất Excel
# =====================
def to_excel(df_dict):
    import io
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows

    output = io.BytesIO()
    wb = Workbook()

    for i, (sheet_name, df) in enumerate(df_dict.items()):
        if i == 0:
            ws = wb.active
            ws.title = sheet_name
        else:
            ws = wb.create_sheet(sheet_name)

        # Ghi DataFrame vào sheet
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)

    wb.save(output)
    return output.getvalue()

# gọi:
excel_file = to_excel({
    "Du_lieu_loc": df_filtered,
    "Theo_Tuan": df_week,
    "Theo_Thang": df_month,
    "Theo_Region": df_region,
    "Theo_Store": df_store,
    "Top10": df_top10,
    "Bottom10": df_bottom10
})

with st.sidebar:
    st.markdown("---")
    st.header("Top khách hàng")

    top_percent_option = st.number_input(
        "Nhập % Top khách hàng theo doanh thu",
        min_value=1,
        max_value=100,
        value=20,
        step=1,
        format="%d"
    )

    doanh_thu_type = st.selectbox(
        "Loại doanh thu để xét Top", 
        options=["Tổng_Net", "Tổng_Gross"], 
        format_func=lambda x: "Doanh thu sau CK" if x == "Tong_sau_CK" else "Doanh thu trước CK"
    )
# =====================
# 💎 Top % khách hàng theo doanh thu
# =====================
st.subheader(f"💎 Top {top_percent_option}% Khách hàng theo {'Doanh thu sau CK' if doanh_thu_type == 'Tổng_Net' else 'Doanh thu trước CK'}")

# 🔁 Gộp theo khách hàng
if "Khach_hang" not in df_filtered.columns:
    st.warning("⚠️ Không tìm thấy cột 'Số_điện_thoại' trong dữ liệu. Vui lòng kiểm tra tên cột.")
else:
    df_top_customers = df_filtered.groupby("Số_điện_thoại", as_index=False)[["Tổng_Gross", "Tổng_Net"]].sum()

    # Tính tỷ lệ chiết khấu
    df_top_customers["Tỷ_lệ_CK (%)"] = (1 - df_top_customers["Tổng_Net"] / df_top_customers["Tổng_Gross"]) * 100

    # Sắp xếp theo loại doanh thu
    df_top_customers = df_top_customers.sort_values(by=doanh_thu_type, ascending=False)

    # Lấy top %
    top_n = max(1, int(len(df_top_customers) * top_percent_option / 100))
    df_top_customers_percent = df_top_customers.head(top_n)

    # Hiển thị bảng
    st.data_editor(
        df_top_customers_percent,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn("Doanh thu trước CK", format="%.0f"),
            "Tổng_Net": st.column_config.NumberColumn("Doanh thu sau CK", format="%.0f"),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f %%"),
        }
    )

# Nút tải Excel
st.download_button(
    label="📥 Xuất dữ liệu ra Excel",
    data=excel_file,
    file_name="bao_cao.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

)
