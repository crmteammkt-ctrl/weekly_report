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

st.set_page_config(page_title="Marketing Revenue Dashboard", layout="wide")
st.title("📊 MARKETING REVENUE DASHBOARD")

# -------------------------
# Load dữ liệu
# -------------------------

df = load_data()

# -------------------------
# Sidebar bộ lọc chung
# -------------------------
with st.sidebar:
    st.markdown("---")
    if st.button("🔄 Cập nhật dữ liệu từ Google Drive"):
        # Tải DB mới + convert lại DuckDB
        rebuild_duckdb_from_drive()

        # Xoá cache để lần sau đọc lại dữ liệu mới
        st.cache_data.clear()
        st.cache_resource.clear()

        st.success("✅ Đã cập nhật dữ liệu mới. App sẽ dùng data mới ở lần load tiếp theo.")
    st.header("🎛️ Bộ lọc dữ liệu")

    time_type = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý", "Năm"]
    )

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

@st.cache_data(show_spinner=False)
def apply_filters(
    df,
    start_date,
    end_date,
    loaiCT_filter,
    brand_filter,
    region_filter,
    store_filter
):
    return df[
        (df["Ngày"] >= start_date) &
        (df["Ngày"] <= end_date) &
        (df["LoaiCT"].isin(loaiCT_filter)) &
        (df["Brand"].isin(brand_filter)) &
        (df["Region"].isin(region_filter)) &
        (df["Điểm_mua_hàng"].isin(store_filter))
    ]
loaiCT_filter = clean_filter(loaiCT_filter, df["LoaiCT"].unique())
brand_filter  = clean_filter(brand_filter, df["Brand"].unique())
region_filter = clean_filter(region_filter, df["Region"].unique())
store_filter  = clean_filter(store_filter, df["Điểm_mua_hàng"].unique())

df_f = apply_filters(
    df,
    pd.to_datetime(start_date),
    pd.to_datetime(end_date),
    loaiCT_filter,
    brand_filter,
    region_filter,
    store_filter
)


# -------------------------
# Thêm cột thời gian theo phân tích
# -------------------------
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
@st.cache_data(show_spinner=False)
def group_time(df_f, time_type):
    freq_map = {"Ngày":"D","Tuần":"W","Tháng":"M","Quý":"Q","Năm":"Y"}

    d = (
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

    d["CK_%"] = (1 - d["Net"] / d["Gross"]) * 100
    d["Net_prev"] = d["Net"].shift(1)
    d["Growth_%"] = (d["Net"] - d["Net_prev"]) / d["Net_prev"] * 100
    return d
df_time = group_time(df_f, time_type)
df_time["CK_%"] = (1 - df_time["Net"] / df_time["Gross"]) * 100
df_time["Net_prev"] = df_time["Net"].shift(1)
df_time["Growth_%"] = (df_time["Net"] - df_time["Net_prev"]) / df_time["Net_prev"] * 100

# -------------------------
# Hàm nhóm theo cột
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

# -------------------------
# Region Time
# -------------------------
@st.cache_data(show_spinner=False)
def group_region_time(df_f_time):
    d = (
        df_f_time
        .groupby(["Time","Region"])
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique")
        )
        .reset_index()
    )

    d["CK_%"] = np.where(
        d["Gross"] > 0,
        (d["Gross"] - d["Net"]) / d["Gross"] * 100,
        0
    ).round(2)

    return d.sort_values(["Time","Net"], ascending=[True, False])
df_region_time = group_region_time(df_f_time)


st.subheader(f"🌍 Theo Region + {time_type}")
st.dataframe(df_region_time)

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

# --- lọc thời gian riêng cho cửa hàng ---
if time_type == "Ngày":
    min_day = df_store["Day"].min()
    max_day = df_store["Day"].max()
    date_range = st.date_input(
        "📅 Chọn khoảng ngày (riêng cho bảng Cửa hàng)",
        value=(min_day,max_day),
        min_value=min_day,
        max_value=max_day
    )
    if len(date_range)==2:
        start_d, end_d = date_range
        df_store = df_store[(df_store["Day"]>=start_d)&(df_store["Day"]<=end_d)]
elif time_type == "Tuần":
    week_selected = st.selectbox("📅 Chọn tuần", sorted(df_store["Week"].unique()))
    df_store = df_store[df_store["Week"]==week_selected]
elif time_type == "Tháng":
    month_selected = st.selectbox("📅 Chọn tháng", sorted(df_store["Month"].unique()))
    df_store = df_store[df_store["Month"]==month_selected]
elif time_type == "Quý":
    quarter_selected = st.selectbox("📅 Chọn quý", sorted(df_store["Quarter"].unique()))
    df_store = df_store[df_store["Quarter"]==quarter_selected]
elif time_type == "Năm":
    year_selected = st.selectbox("📅 Chọn năm", sorted(df_store["Year"].unique()))
    df_store = df_store[df_store["Year"]==year_selected]

@st.cache_data(show_spinner=False)
def group_store(df_store):
    d = (
        df_store
        .groupby("Điểm_mua_hàng")
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique")
        )
        .reset_index()
    )

    d["CK_%"] = np.where(
        d["Gross"] > 0,
        (d["Gross"] - d["Net"]) / d["Gross"] * 100,
        0
    ).round(2)

    return d.sort_values("Net", ascending=False)
df_store_group = group_store(df_store)

st.dataframe(df_store_group)

# -------------------------
# Báo cáo nhóm sản phẩm
# -------------------------
df_product = df_f.copy()
st.subheader("📦 Theo Nhóm SP / Tên hàng")

col1,col2 = st.columns(2)
with col1:
    nhom_sp_selected = st.multiselect("📦 Chọn Nhóm SP", sorted(df_product["Nhóm_hàng"].dropna().unique()))
with col2:
    ten_sp_selected = st.multiselect("🏷️ Chọn Tên hàng", sorted(df_product["Tên_hàng"].dropna().unique()))

if nhom_sp_selected:
    df_product = df_product[df_product["Nhóm_hàng"].isin(nhom_sp_selected)]
if ten_sp_selected:
    df_product = df_product[df_product["Tên_hàng"].isin(ten_sp_selected)]

@st.cache_data(show_spinner=False)
def group_product(df):
    return (
        df.groupby("Tên_hàng")
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique")
        )
        .reset_index()
        .sort_values("Net", ascending=False)
    )
df_product_group = group_product(df_product)


st.dataframe(df_product_group)

# -------------------------
# Các phần khác (Pareto, Cohort, Xuất CRM) 
# -------------------------
# =========================
# PARAMETER XUẤT CRM & PHÂN LOẠI KH
# =========================
st.sidebar.header("📤 Xuất KH")

INACTIVE_DAYS = st.sidebar.slider(
    "Inactive ≥ bao nhiêu ngày",
    min_value=30,
    max_value=365,
    value=90,
    step=15
)

VIP_NET_THRESHOLD = st.sidebar.number_input(
    "Net tối thiểu để vào VIP",
    min_value=0,
    value=300_000_000,
    step=10_000_000
)

GROUP_BY_CUSTOMER = st.sidebar.checkbox(
    "Gộp tất cả giao dịch của 1 KH",
    value=False
)

min_net = st.sidebar.number_input("Net tối thiểu (lọc)", 0, value=0)
today = df_f["Ngày"].max()

group_cols = ["Số_điện_thoại"]
if not GROUP_BY_CUSTOMER:
    group_cols.append("Điểm_mua_hàng")

@st.cache_data(show_spinner="📦 Tổng hợp CRM...")
def build_crm(df_f, group_cols):
    d = (
        df_f
        .groupby(group_cols)
        .agg(
            Name=("tên_KH","first"),
            Name_Check=("Kiểm_tra_tên","first"),
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            First_Order=("Ngày","min"),
            Last_Order=("Ngày","max"),
            Check_SDT=("Trạng_thái_số_điện_thoại","first")
        )
        .reset_index()
    )
    return d
df_export = build_crm(df_f, group_cols)


df_export["CK_%"] = np.where(
    df_export["Gross"]>0,
    (df_export["Gross"] - df_export["Net"]) / df_export["Gross"] * 100,
    0
).round(2)

df_export["Days_Inactive"] = (today - df_export["Last_Order"]).dt.days

df_export["KH_tag"] = np.select(
    [
        df_export["Days_Inactive"] >= INACTIVE_DAYS,
        df_export["Net"] >= VIP_NET_THRESHOLD
    ],
    [
        "KH Inactive",
        "KH VIP"
    ],
    default="Khách hàng"
)

df_export["Bao_lâu_không_mua"] = np.where(
    df_export["KH_tag"] == "KH Inactive",
    df_export["Days_Inactive"],
    np.nan
)

df_export = df_export[df_export["Net"] >= min_net]

display_cols = [
    "Số_điện_thoại",
    "Name",
    "KH_tag",
    "Gross",
    "Net",
    "CK_%",
    "Orders",
    "Bao_lâu_không_mua",
    "Last_Order"
]
if not GROUP_BY_CUSTOMER:
    display_cols.insert(1, "Điểm_mua_hàng")

# =========================
# FILTER BẢNG CRM
# =========================
st.subheader("📄 Danh sách KH xuất CRM")
st.markdown("### 🔎 Lọc nhanh trên bảng")

col1,col2,col3,col4,col5 = st.columns(5)

with col1:
    show_inactive = st.checkbox("Chỉ KH Inactive", value=False)
with col2:
    show_vip = st.checkbox("Chỉ KH VIP", value=False)
with col3:
    show_customer = st.checkbox("Khách hàng thường", value=True)

if "kiem_tra_ten_filter" not in st.session_state:
    st.session_state.kiem_tra_ten_filter = df_f["Kiểm_tra_tên"].dropna().unique().tolist()

with col4:
    kiem_tra_ten_filter = st.multiselect(
        "Kiểm tra tên KH",
        options=df_f["Kiểm_tra_tên"].dropna().unique(),
        default = st.session_state.kiem_tra_ten_filter
    )
    st.session_state.kiem_tra_ten_filter = kiem_tra_ten_filter
with col5:
    check_sdt_filter = st.multiselect(
        "Check SĐT",
        options=df_export["Check_SDT"].dropna().unique(),
        default=df_export["Check_SDT"].dropna().unique()
    )

# Lọc KH_tag
selected_tags = []
if show_inactive: selected_tags.append("KH Inactive")
if show_vip: selected_tags.append("KH VIP")
if show_customer: selected_tags.append("Khách hàng")
if selected_tags:
    df_export = df_export[df_export["KH_tag"].isin(selected_tags)]

# Lọc Check_SDT
if check_sdt_filter:
    df_export = df_export[df_export["Check_SDT"].isin(check_sdt_filter)]

# Lọc Name_Check
if kiem_tra_ten_filter:
    df_export = df_export[df_export["Name_Check"].isin(kiem_tra_ten_filter)]

# Sắp xếp
sort_col = st.selectbox(
    "Sắp xếp theo",
    options=df_export.columns,
    index=list(df_export.columns).index("Net")
)
sort_order = st.radio("Thứ tự", ["Giảm dần","Tăng dần"], horizontal=True)
df_export = df_export.sort_values(sort_col, ascending=(sort_order=="Tăng dần"))

total_kh_filtered = df_export["Số_điện_thoại"].nunique()
st.info(f"👥 Tổng số KH theo bộ lọc hiện tại: **{total_kh_filtered:,}** khách hàng")

# Tạo row tổng
total_row = {}
for col in df_export.columns:
    if col in ["Gross","Net","Orders"]:
        total_row[col] = df_export[col].sum()
    elif col=="Số_điện_thoại":
        total_row[col] = "TỔNG"
    else:
        total_row[col] = ""
df_export_with_total = pd.concat([df_export, pd.DataFrame([total_row])], ignore_index=True)

# Chỉ hiển thị các cột cần thiết
df_export_display = df_export_with_total[display_cols]
st.dataframe(df_export_display, use_container_width=True)

# Xuất Excel
st.download_button(
    "📥 Tải danh sách KH (Excel)",
    data=to_excel(df_export_display),
    file_name="customer_marketing.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================
# PARETO KH THEO CỬA HÀNG
# =========================
st.sidebar.header("🏆 Pareto KH theo Cửa hàng")

pareto_percent = st.sidebar.slider("Chọn % KH Pareto",5,50,20)
pareto_type = st.sidebar.radio("Loại Pareto",["Top","Bottom"])
store_filter_pareto = st.sidebar.multiselect(
    "Chọn Cửa hàng (Pareto)",
    sorted(df_f["Điểm_mua_hàng"].dropna().unique()),
    default=sorted(df_f["Điểm_mua_hàng"].dropna().unique())
)

df_pareto_base = df_f.copy()
if store_filter_pareto:
    df_pareto_base = df_pareto_base[df_pareto_base["Điểm_mua_hàng"].isin(store_filter_pareto)]

def pareto_customer_by_store(df, percent=20, top=True):
    rows=[]
    for store, d in df.groupby("Điểm_mua_hàng"):
        g = d.groupby("Số_điện_thoại").agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique")
        ).reset_index().sort_values("Net",ascending=False)
        if g.empty: continue
        g["CK_%"] = ((g["Gross"]-g["Net"])/g["Gross"]*100).round(2)
        total_net = g["Net"].sum()
        g["Contribution_%"] = (g["Net"]/total_net*100).round(2)
        g["Cum_%"] = g["Contribution_%"].cumsum().round(2)
        n = max(1,int(len(g)*percent/100))
        g_sel = g.head(n) if top else g.tail(n)
        g_sel["Điểm_mua_hàng"] = store
        rows.append(g_sel)
    return pd.concat(rows, ignore_index=True)

df_pareto = pareto_customer_by_store(
    df_pareto_base,
    percent=pareto_percent,
    top=(pareto_type=="Top")
)

st.subheader(f"🏆 {pareto_type} {pareto_percent}% KH theo từng Cửa hàng (Pareto)")
st.dataframe(
    df_pareto[["Điểm_mua_hàng","Số_điện_thoại","Gross","Net","CK_%","Orders","Contribution_%","Cum_%"]]
)
st.download_button(
    "📥 Tải KH Pareto theo Cửa hàng (Excel)",
    data=to_excel(df_pareto),
    file_name="pareto_kh_theo_cua_hang.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================
# KH MỚI VS KH QUAY LẠI
# =========================


df_fp = first_purchase()
df_kh = df_f.merge(df_fp, on="Số_điện_thoại", how="left")
df_kh["KH_type"] = np.where(df_kh["First_Date"]>=pd.to_datetime(start_date),"KH mới","KH quay lại")

st.subheader("👥 KH mới vs KH quay lại")
st.dataframe(
    df_kh.groupby("KH_type")["Số_điện_thoại"].nunique().reset_index(name="Số KH")
)

# =========================
# COHORT RETENTION – CỘNG DỒN (%)
# =========================
st.sidebar.subheader("⚙️ Cohort Retention")

MAX_MONTH = st.sidebar.slider(
    "Giới hạn số tháng retention",
    min_value=3,
    max_value=12,
    value=7
)

df_cohort = df_f.copy()

# --- Bổ sung xử lý NaT để tránh lỗi TypeError ---
df_cohort["Ngày"] = pd.to_datetime(df_cohort["Ngày"], errors="coerce")
df_cohort = df_cohort.dropna(subset=["Ngày"])

# 1. Order month
df_cohort["Order_Month"] = df_cohort["Ngày"].dt.to_period("M")

# 2. First month per customer
df_cohort["First_Month"] = df_cohort.groupby("Số_điện_thoại")["Order_Month"].transform("min")

# 3. Tính Cohort_Index (số tháng kể từ first month)
df_cohort["Cohort_Index"] = (
    (df_cohort["Order_Month"].dt.year - df_cohort["First_Month"].dt.year) * 12 +
    (df_cohort["Order_Month"].dt.month - df_cohort["First_Month"].dt.month)
)

# 4. Loại bỏ Cohort_Index < 0 (nếu có)
df_cohort = df_cohort[df_cohort["Cohort_Index"] >= 0]

# =========================
# Tính retention (%)
# =========================
cohort_size = df_cohort[df_cohort["Cohort_Index"] == 0].groupby("First_Month")["Số_điện_thoại"].nunique()
rows = []

for cohort, size in cohort_size.items():
    d = df_cohort[df_cohort["First_Month"] == cohort]
    row = {"First_Month": str(cohort), "Tổng KH": size}
    
    for m in range(1, MAX_MONTH + 1):
        kh_quay_lai = d[(d["Cohort_Index"] >= 1) & (d["Cohort_Index"] <= m)]["Số_điện_thoại"].nunique()
        row[f"Sau {m} tháng"] = round(kh_quay_lai / size * 100, 2)
    
    rows.append(row)

retention = pd.DataFrame(rows)

# =========================
# GRAND TOTAL
# =========================
total_kh = retention["Tổng KH"].sum()
grand = {"First_Month": "Grand Total", "Tổng KH": total_kh}

for c in retention.columns:
    if c.startswith("Sau"):
        grand[c] = round((retention[c] * retention["Tổng KH"]).sum() / total_kh, 2)

retention = pd.concat([retention, pd.DataFrame([grand])], ignore_index=True)

st.subheader("🏅 Cohort Retention – Cộng dồn (%)")
st.dataframe(retention)


