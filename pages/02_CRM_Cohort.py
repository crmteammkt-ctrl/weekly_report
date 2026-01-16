import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

from load_data import load_data, first_purchase


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


st.title("👥 CRM, Pareto & Cohort Retention")

# -------- LOAD DATA ----------
@st.cache_data(show_spinner="📦 Đang load dữ liệu...")
def _load_df():
    return load_data()

try:
    df = _load_df()
except Exception as e:
    st.error("❌ Lỗi khi load dữ liệu. Kiểm tra lại file Parquet / load_data.py")
    st.exception(e)
    st.stop()

# -------- SIDEBAR FILTER ----------
with st.sidebar:
    st.header("🎛️ Bộ lọc CRM")

    start_date = st.date_input("Từ ngày", df["Ngày"].min(), key="crm_start")
    end_date   = st.date_input("Đến ngày", df["Ngày"].max(), key="crm_end")

    loaiCT_filter = st.multiselect("Loại CT", ["All"] + sorted(df["LoaiCT"].dropna().unique()), key="crm_loaiCT")
    brand_filter  = st.multiselect("Brand", ["All"] + sorted(df["Brand"].dropna().unique()), key="crm_brand")
    region_filter = st.multiselect("Region", ["All"] + sorted(df["Region"].dropna().unique()), key="crm_region")
    store_filter  = st.multiselect("Cửa hàng", ["All"] + sorted(df["Điểm_mua_hàng"].dropna().unique()), key="crm_store")

    st.markdown("---")
    st.header("📤 Xuất KH")

    INACTIVE_DAYS = st.slider(
        "Inactive ≥ bao nhiêu ngày",
        min_value=30,
        max_value=365,
        value=90,
        step=15,
        key="crm_inactive",
    )

    VIP_NET_THRESHOLD = st.number_input(
        "Net tối thiểu để vào VIP",
        min_value=0,
        value=300_000_000,
        step=10_000_000,
        key="crm_vip",
    )

    GROUP_BY_CUSTOMER = st.checkbox(
        "Gộp tất cả giao dịch của 1 KH",
        value=False,
        key="crm_group_by_cust",
    )

    min_net = st.number_input("Net tối thiểu (lọc)", 0, value=0, key="crm_min_net")

    st.markdown("---")
    st.subheader("⚙️ Cohort Retention")
    MAX_MONTH = st.slider(
        "Giới hạn số tháng retention",
        min_value=3,
        max_value=12,
        value=7,
        key="crm_max_month",
    )


def clean_filter(values, all_values):
    if not values or "All" in values:
        return all_values
    return values


loaiCT_filter = clean_filter(loaiCT_filter, df["LoaiCT"].unique())
brand_filter  = clean_filter(brand_filter, df["Brand"].unique())
region_filter = clean_filter(region_filter, df["Region"].unique())
store_filter  = clean_filter(store_filter, df["Điểm_mua_hàng"].unique())


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
    store_filter,
)

today = df_f["Ngày"].max()

# =========================
# CRM EXPORT
# =========================
st.subheader("📄 Danh sách KH xuất CRM")

group_cols = ["Số_điện_thoại"]
if not GROUP_BY_CUSTOMER:
    group_cols.append("Điểm_mua_hàng")


@st.cache_data(show_spinner="📦 Tổng hợp CRM...")
def build_crm(df_f, group_cols):
    d = (
        df_f.groupby(group_cols)
        .agg(
            Name=("tên_KH", "first"),
            Name_Check=("Kiểm_tra_tên", "first"),
            Gross=("Tổng_Gross", "sum"),
            Net=("Tổng_Net", "sum"),
            Orders=("Số_CT", "nunique"),
            First_Order=("Ngày", "min"),
            Last_Order=("Ngày", "max"),
            Check_SDT=("Trạng_thái_số_điện_thoại", "first"),
        )
        .reset_index()
    )
    return d


df_export = build_crm(df_f, group_cols)

df_export["CK_%"] = np.where(
    df_export["Gross"] > 0,
    (df_export["Gross"] - df_export["Net"]) / df_export["Gross"] * 100,
    0,
).round(2)

df_export["Days_Inactive"] = (today - df_export["Last_Order"]).dt.days

df_export["KH_tag"] = np.select(
    [
        df_export["Days_Inactive"] >= INACTIVE_DAYS,
        df_export["Net"] >= VIP_NET_THRESHOLD,
    ],
    ["KH Inactive", "KH VIP"],
    default="Khách hàng",
)

df_export["Bao_lâu_không_mua"] = np.where(
    df_export["KH_tag"] == "KH Inactive",
    df_export["Days_Inactive"],
    np.nan,
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
    "Last_Order",
]
if not GROUP_BY_CUSTOMER:
    display_cols.insert(1, "Điểm_mua_hàng")

# --- Filter trên bảng CRM ---
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    show_inactive = st.checkbox("Chỉ KH Inactive", value=False, key="crm_show_inactive")
with col2:
    show_vip = st.checkbox("Chỉ KH VIP", value=False, key="crm_show_vip")
with col3:
    show_customer = st.checkbox("Khách hàng thường", value=True, key="crm_show_normal")

if "kiem_tra_ten_filter" not in st.session_state:
    st.session_state.kiem_tra_ten_filter = df_f["Kiểm_tra_tên"].dropna().unique().tolist()

with col4:
    kiem_tra_ten_filter = st.multiselect(
        "Kiểm tra tên KH",
        options=df_f["Kiểm_tra_tên"].dropna().unique(),
        default=st.session_state.kiem_tra_ten_filter,
        key="crm_filter_namecheck",
    )
    st.session_state.kiem_tra_ten_filter = kiem_tra_ten_filter

with col5:
    check_sdt_filter = st.multiselect(
        "Check SĐT",
        options=df_export["Check_SDT"].dropna().unique(),
        default=df_export["Check_SDT"].dropna().unique(),
        key="crm_filter_check_sdt",
    )

selected_tags = []
if show_inactive:
    selected_tags.append("KH Inactive")
if show_vip:
    selected_tags.append("KH VIP")
if show_customer:
    selected_tags.append("Khách hàng")
if selected_tags:
    df_export = df_export[df_export["KH_tag"].isin(selected_tags)]

if check_sdt_filter:
    df_export = df_export[df_export["Check_SDT"].isin(check_sdt_filter)]

if kiem_tra_ten_filter:
    df_export = df_export[df_export["Name_Check"].isin(kiem_tra_ten_filter)]

sort_col = st.selectbox(
    "Sắp xếp theo",
    options=df_export.columns,
    index=list(df_export.columns).index("Net"),
    key="crm_sort_col",
)
sort_order = st.radio("Thứ tự", ["Giảm dần", "Tăng dần"], horizontal=True, key="crm_sort_order")
df_export = df_export.sort_values(sort_col, ascending=(sort_order == "Tăng dần"))

total_kh_filtered = df_export["Số_điện_thoại"].nunique()
st.info(f"👥 Tổng số KH theo bộ lọc hiện tại: **{total_kh_filtered:,}** khách hàng")

total_row = {}
for col in df_export.columns:
    if col in ["Gross", "Net", "Orders"]:
        total_row[col] = df_export[col].sum()
    elif col == "CK_%":
        total_row[col] = df_export[col].mean()
    elif col == "Last_Order":
        total_row[col] = pd.NaT
    elif col == "Số_điện_thoại":
        total_row[col] = "TỔNG"
    else:
        total_row[col] = ""

df_export_with_total = pd.concat(
    [df_export, pd.DataFrame([total_row])], ignore_index=True
)

df_export_display = df_export_with_total[display_cols]
st.dataframe(df_export_display, width="stretch")

st.download_button(
    "📥 Tải danh sách KH (Excel)",
    data=to_excel(df_export_display),
    file_name="customer_marketing.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# =========================
# PARETO KH THEO CỬA HÀNG
# =========================
st.subheader("🏆 Pareto KH theo Cửa hàng")

store_filter_pareto = st.multiselect(
    "Chọn Cửa hàng (Pareto)",
    sorted(df_f["Điểm_mua_hàng"].dropna().unique()),
    default=sorted(df_f["Điểm_mua_hàng"].dropna().unique()),
    key="crm_store_pareto",
)

pareto_percent = st.slider("Chọn % KH Pareto", 5, 50, 20, key="crm_pareto_percent")
pareto_type = st.radio("Loại Pareto", ["Top", "Bottom"], key="crm_pareto_type")

df_pareto_base = df_f.copy()
if store_filter_pareto:
    df_pareto_base = df_pareto_base[
        df_pareto_base["Điểm_mua_hàng"].isin(store_filter_pareto)
    ]


def pareto_customer_by_store(df, percent=20, top=True):
    rows = []
    for store, d in df.groupby("Điểm_mua_hàng"):
        g = (
            d.groupby("Số_điện_thoại")
            .agg(
                Gross=("Tổng_Gross", "sum"),
                Net=("Tổng_Net", "sum"),
                Orders=("Số_CT", "nunique"),
            )
            .reset_index()
            .sort_values("Net", ascending=False)
        )

        if g.empty:
            continue

        g["CK_%"] = ((g["Gross"] - g["Net"]) / g["Gross"] * 100).round(2)
        total_net = g["Net"].sum()
        g["Contribution_%"] = (g["Net"] / total_net * 100).round(2)
        g["Cum_%"] = g["Contribution_%"].cumsum().round(2)

        n = max(1, int(len(g) * percent / 100))
        g_sel = g.head(n) if top else g.tail(n)

        g_sel = g_sel.copy()
        g_sel.loc[:, "Điểm_mua_hàng"] = store

        rows.append(g_sel)

    return pd.concat(rows, ignore_index=True)


df_pareto = pareto_customer_by_store(
    df_pareto_base, percent=pareto_percent, top=(pareto_type == "Top")
)

st.dataframe(
    df_pareto[
        [
            "Điểm_mua_hàng",
            "Số_điện_thoại",
            "Gross",
            "Net",
            "CK_%",
            "Orders",
            "Contribution_%",
            "Cum_%",
        ]
    ],
    width="stretch",
)

st.download_button(
    "📥 Tải KH Pareto theo Cửa hàng (Excel)",
    data=to_excel(df_pareto),
    file_name="pareto_kh_theo_cua_hang.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# =========================
# KH MỚI VS KH QUAY LẠI
# =========================
st.subheader("👥 KH mới vs KH quay lại")

df_fp = first_purchase()
df_kh = df_f.merge(df_fp, on="Số_điện_thoại", how="left")
df_kh["KH_type"] = np.where(
    df_kh["First_Date"] >= pd.to_datetime(start_date), "KH mới", "KH quay lại"
)

st.dataframe(
    df_kh.groupby("KH_type")["Số_điện_thoại"]
    .nunique()
    .reset_index(name="Số KH"),
    width="stretch",
)

# =========================
# COHORT RETENTION – CỘNG DỒN (%)
# =========================
st.subheader("🏅 Cohort Retention – Cộng dồn (%)")

df_cohort = df_f.copy()

df_cohort["Ngày"] = pd.to_datetime(df_cohort["Ngày"], errors="coerce")
df_cohort = df_cohort.dropna(subset=["Ngày"])

df_cohort["Order_Month"] = df_cohort["Ngày"].dt.to_period("M")

df_cohort["First_Month"] = df_cohort.groupby("Số_điện_thoại")["Order_Month"].transform(
    "min"
)

df_cohort["Cohort_Index"] = (
    (df_cohort["Order_Month"].dt.year - df_cohort["First_Month"].dt.year) * 12
    + (df_cohort["Order_Month"].dt.month - df_cohort["First_Month"].dt.month)
)

df_cohort = df_cohort[df_cohort["Cohort_Index"] >= 0]

cohort_size = (
    df_cohort[df_cohort["Cohort_Index"] == 0]
    .groupby("First_Month")["Số_điện_thoại"]
    .nunique()
)
rows = []

for cohort, size in cohort_size.items():
    d = df_cohort[df_cohort["First_Month"] == cohort]
    row = {"First_Month": str(cohort), "Tổng KH": size}

    for m in range(1, MAX_MONTH + 1):
        kh_quay_lai = d[
            (d["Cohort_Index"] >= 1) & (d["Cohort_Index"] <= m)
        ]["Số_điện_thoại"].nunique()
        row[f"Sau {m} tháng"] = round(kh_quay_lai / size * 100, 2)

    rows.append(row)

retention = pd.DataFrame(rows)

total_kh = retention["Tổng KH"].sum()
grand = {"First_Month": "Grand Total", "Tổng KH": total_kh}

for c in retention.columns:
    if c.startswith("Sau"):
        grand[c] = round(
            (retention[c] * retention["Tổng KH"]).sum() / total_kh, 2
        )

retention = pd.concat([retention, pd.DataFrame([grand])], ignore_index=True)

st.dataframe(retention, width="stretch")
