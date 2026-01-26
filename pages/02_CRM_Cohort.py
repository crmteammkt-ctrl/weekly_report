# pages/02_CRM_Cohort.py

import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

from load_data import get_active_data, first_purchase

def safe_multiselect_all(
    key: str,
    label: str,
    options,
    all_label: str = "All",
    default_all: bool = True,
    normalize: bool = True,
):
    """
    Multiselect có 'All' an toàn:
    - All luôn hợp lệ
    - options đổi không bao giờ crash
    - nhớ selection cũ nếu còn tồn tại
    """
    # Chuẩn hoá options
    opts = pd.Series(list(options)).dropna().astype(str)
    if normalize:
        opts = opts.str.strip()
    opts = sorted(opts.unique().tolist())

    ui_opts = [all_label] + opts

    # Init session
    if key not in st.session_state:
        st.session_state[key] = [all_label] if default_all else opts[:1]

    # Lọc lại selection cũ
    current = st.session_state.get(key, [])
    current = [str(x).strip() for x in current if str(x).strip() in ui_opts]

    if not current:
        current = [all_label] if default_all else opts[:1]

    selected = st.multiselect(
        label,
        options=ui_opts,
        default=current,
        key=key,
    )

    # Normalize output
    if (not selected) or (all_label in selected):
        return opts   # trả về TOÀN BỘ option thật

    return [x for x in selected if x in opts]


# =====================================================
# FORMAT HELPERS (an toàn - không phụ thuộc Streamlit format)
# =====================================================
def fmt_int(x):
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):,.0f}"
    except:
        return ""

def fmt_num(x, decimals=2):
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):,.{decimals}f}"
    except:
        return ""

def fmt_pct(x, decimals=2):
    # x đang là 20.8 => "20.80%"
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):,.{decimals}f}%"
    except:
        return ""

def to_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()

def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if "Ngày" in df.columns:
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
        df = df.dropna(subset=["Ngày"])
    return df

def fix_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in ["Tổng_Gross", "Tổng_Net"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def show_df(df_show: pd.DataFrame, title: str | None = None):
    if title:
        st.subheader(title)
    st.dataframe(df_show, use_container_width=True, hide_index=True)

# =====================================================
# PAGE
# =====================================================
st.title("📤 CRM & Cohort Retention")

# =====================================================
# LOAD
# =====================================================
df = get_active_data()
df = ensure_datetime(df)
df = fix_numeric(df)

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích. Kiểm tra lại nguồn dữ liệu.")
    st.stop()

# =====================================================
# SIDEBAR FILTER (có liên kết Brand → Region → Cửa hàng)
# =====================================================
def with_all_option(values: list[str], label_all="All"):
    return [label_all] + values
def normalize_filter(selected, all_values, label_all="All"):
    if (not selected) or (label_all in selected):
        return all_values
    return selected

with st.sidebar:
    st.header("🎛️ Bộ lọc dữ liệu (CRM & Cohort)")

    start_date = st.date_input("Từ ngày", df["Ngày"].min().date())
    end_date = st.date_input("Đến ngày", df["Ngày"].max().date())

    # Loại CT
    all_loaiCT = sorted(df["LoaiCT"].dropna().unique()) if "LoaiCT" in df.columns else []
    loaiCT_ui = st.multiselect("Loại CT", with_all_option(all_loaiCT), default=["All"])
    loaiCT_filter = normalize_filter(loaiCT_ui, all_loaiCT)

    # Brand -> Region -> Cửa hàng
    with st.sidebar:
        brand_filter = safe_multiselect_all(
        key="brand_filter",
        label="Brand",
        options=df["Brand"],
        all_label="All",
        default_all=True,
    )

    df_b = df[df["Brand"].isin(brand_filter)] if brand_filter else df.iloc[0:0]

    all_region = sorted(df_b["Region"].dropna().unique()) if "Region" in df_b.columns else []
    region_ui = st.multiselect("Region", with_all_option(all_region), default=["All"])
    region_filter = normalize_filter(region_ui, all_region)

    df_br = df_b[df_b["Region"].isin(region_filter)] if region_filter else df_b.iloc[0:0]

    all_store = sorted(df_br["Điểm_mua_hàng"].dropna().unique()) if "Điểm_mua_hàng" in df_br.columns else []
    store_ui = st.multiselect("Cửa hàng", with_all_option(all_store), default=["All"])
    store_filter = normalize_filter(store_ui, all_store)

def apply_filters(df: pd.DataFrame, start_date, end_date, loaiCT, brand, region, store) -> pd.DataFrame:
    mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))

    if "LoaiCT" in df.columns:
        mask &= df["LoaiCT"].isin(loaiCT if loaiCT else [])
    if "Brand" in df.columns:
        mask &= df["Brand"].isin(brand if brand else [])
    if "Region" in df.columns:
        mask &= df["Region"].isin(region if region else [])
    if "Điểm_mua_hàng" in df.columns:
        mask &= df["Điểm_mua_hàng"].isin(store if store else [])

    return df.loc[mask].copy()

df_f = apply_filters(df, start_date, end_date, loaiCT_filter, brand_filter, region_filter, store_filter)

if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

today = df_f["Ngày"].max()

# =========================
# PARAMETER XUẤT CRM & PHÂN LOẠI KH
# =========================
st.sidebar.header("📤 Xuất KH")

INACTIVE_DAYS = st.sidebar.slider("Inactive ≥ bao nhiêu ngày", 30, 365, 90, 15)

VIP_NET_THRESHOLD = st.sidebar.number_input(
    "Net tối thiểu để vào VIP", min_value=0, value=300_000_000, step=10_000_000
)

GROUP_BY_CUSTOMER = st.sidebar.checkbox("Gộp tất cả giao dịch của 1 KH", value=False)
min_net = st.sidebar.number_input("Net tối thiểu (lọc)", 0, value=0)

group_cols = ["Số_điện_thoại"]
if not GROUP_BY_CUSTOMER:
    group_cols.append("Điểm_mua_hàng")

def build_crm(df_f: pd.DataFrame, group_cols):
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
).astype("float")

df_export = df_export[df_export["Net"] >= min_net].copy()

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

# =========================
# FILTER BẢNG CRM
# =========================
st.subheader("📄 Danh sách KH xuất CRM")
st.markdown("### 🔎 Lọc nhanh trên bảng")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    show_inactive = st.checkbox("Chỉ KH Inactive", value=False)
with col2:
    show_vip = st.checkbox("Chỉ KH VIP", value=False)
with col3:
    show_customer = st.checkbox("Khách hàng thường", value=True)

if "kiem_tra_ten_filter" not in st.session_state:
    st.session_state.kiem_tra_ten_filter = df_f["Kiểm_tra_tên"].dropna().unique().tolist()

with col4:
    kiem_tra_ten_filter = safe_multiselect_all(
        key="kiem_tra_ten_filter",
        label="Kiểm tra tên KH",
        options=df_f["Kiểm_tra_tên"],
        all_label="All",
        default_all=True,
    )

    st.session_state.kiem_tra_ten_filter = kiem_tra_ten_filter

with col5:
    check_sdt_filter = safe_multiselect_all(
        key="check_sdt_filter",
        label="Check SĐT",
        options=df_export["Check_SDT"],
        all_label="All",
        default_all=True,
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
    index=list(df_export.columns).index("Net") if "Net" in df_export.columns else 0,
)
sort_order = st.radio("Thứ tự", ["Giảm dần", "Tăng dần"], horizontal=True)
df_export = df_export.sort_values(sort_col, ascending=(sort_order == "Tăng dần"))

total_kh_filtered = df_export["Số_điện_thoại"].nunique()
st.info(f"👥 Tổng số KH theo bộ lọc hiện tại: **{total_kh_filtered:,}** khách hàng")

# Row tổng
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
    elif col == "Bao_lâu_không_mua":
        total_row[col] = np.nan
    else:
        total_row[col] = ""

df_export_with_total = pd.concat([df_export, pd.DataFrame([total_row])], ignore_index=True)

# ===== format hiển thị CRM =====
df_export_display = df_export_with_total[display_cols].copy()

# format số
for c in ["Gross", "Net", "Orders"]:
    if c in df_export_display.columns:
        df_export_display[c] = df_export_display[c].apply(fmt_int)

if "CK_%" in df_export_display.columns:
    df_export_display["CK_%"] = df_export_display["CK_%"].apply(lambda v: fmt_pct(v, 2))

if "Bao_lâu_không_mua" in df_export_display.columns:
    # cột này là số ngày, giữ int format
    df_export_display["Bao_lâu_không_mua"] = df_export_display["Bao_lâu_không_mua"].apply(
        lambda v: "" if pd.isna(v) else fmt_int(v)
    )

# Last_Order hiển thị yyyy-mm-dd
if "Last_Order" in df_export_display.columns:
    df_export_display["Last_Order"] = pd.to_datetime(df_export_display["Last_Order"], errors="coerce").dt.strftime("%Y-%m-%d")

show_df(df_export_display, title=None)

st.download_button(
    "📥 Tải danh sách KH (Excel)",
    data=to_excel(df_export_display),
    file_name="customer_marketing.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# =========================
# PARETO KH THEO CỬA HÀNG
# =========================
st.sidebar.header("🏆 Pareto KH theo Cửa hàng")
pareto_percent = st.sidebar.slider("Chọn % KH Pareto", 5, 50, 20)
pareto_type = st.sidebar.radio("Loại Pareto", ["Top", "Bottom"])

store_filter_pareto = st.sidebar.multiselect(
    "Chọn Cửa hàng (Pareto)",
    sorted(df_f["Điểm_mua_hàng"].dropna().unique()),
    default=sorted(df_f["Điểm_mua_hàng"].dropna().unique()),
)

def pareto_customer_by_store(df: pd.DataFrame, percent=20, top=True) -> pd.DataFrame:
    rows = []
    for store, d in df.groupby("Điểm_mua_hàng"):
        g = (
            d.groupby("Số_điện_thoại")
            .agg(Gross=("Tổng_Gross", "sum"), Net=("Tổng_Net", "sum"), Orders=("Số_CT", "nunique"))
            .reset_index()
            .sort_values("Net", ascending=False)
        )
        if g.empty:
            continue

        g["CK_%"] = ((g["Gross"] - g["Net"]) / g["Gross"] * 100).round(2)
        total_net = g["Net"].sum()
        g["Contribution_%"] = (g["Net"] / total_net * 100).round(2) if total_net != 0 else 0
        g["Cum_%"] = g["Contribution_%"].cumsum().round(2)

        n = max(1, int(len(g) * percent / 100))
        g_sel = g.head(n) if top else g.tail(n)

        g_sel = g_sel.copy()
        g_sel.loc[:, "Điểm_mua_hàng"] = store
        rows.append(g_sel)

    if rows:
        return pd.concat(rows, ignore_index=True)
    return pd.DataFrame()

df_pareto_base = df_f.copy()
if store_filter_pareto:
    df_pareto_base = df_pareto_base[df_pareto_base["Điểm_mua_hàng"].isin(store_filter_pareto)]

df_pareto = pareto_customer_by_store(df_pareto_base, percent=pareto_percent, top=(pareto_type == "Top"))

st.subheader(f"🏆 {pareto_type} {pareto_percent}% KH theo từng Cửa hàng (Pareto)")
if not df_pareto.empty:
    df_pareto_show = df_pareto[
        ["Điểm_mua_hàng", "Số_điện_thoại", "Gross", "Net", "CK_%", "Orders", "Contribution_%", "Cum_%"]
    ].copy()

    for c in ["Gross", "Net", "Orders"]:
        df_pareto_show[c] = df_pareto_show[c].apply(fmt_int)
    df_pareto_show["CK_%"] = df_pareto_show["CK_%"].apply(lambda v: fmt_pct(v, 2))
    df_pareto_show["Contribution_%"] = df_pareto_show["Contribution_%"].apply(lambda v: fmt_pct(v, 2))
    df_pareto_show["Cum_%"] = df_pareto_show["Cum_%"].apply(lambda v: fmt_pct(v, 2))

    show_df(df_pareto_show, title=None)
else:
    st.info("Không có dữ liệu phù hợp cho Pareto.")

# =========================
# KH MỚI VS KH QUAY LẠI
# =========================
df_fp = first_purchase(df)  # dùng toàn bộ active_df để đúng First_Date
df_kh = df_f.merge(df_fp, on="Số_điện_thoại", how="left")
df_kh["KH_type"] = np.where(df_kh["First_Date"] >= pd.to_datetime(start_date), "KH mới", "KH quay lại")

st.subheader("👥 KH mới vs KH quay lại")
st.dataframe(
    df_kh.groupby("KH_type")["Số_điện_thoại"].nunique().reset_index(name="Số KH"),
    use_container_width=True,
    hide_index=True,
)

# =========================
# COHORT RETENTION – CỘNG DỒN (%)
# =========================
st.sidebar.subheader("⚙️ Cohort Retention")
MAX_MONTH = st.sidebar.slider("Giới hạn số tháng retention", 3, 12, 7)

df_cohort = df_f.copy()
df_cohort = ensure_datetime(df_cohort)

df_cohort["Order_Month"] = df_cohort["Ngày"].dt.to_period("M")
df_cohort["First_Month"] = df_cohort.groupby("Số_điện_thoại")["Order_Month"].transform("min")

df_cohort["Cohort_Index"] = (
    (df_cohort["Order_Month"].dt.year - df_cohort["First_Month"].dt.year) * 12
    + (df_cohort["Order_Month"].dt.month - df_cohort["First_Month"].dt.month)
)
df_cohort = df_cohort[df_cohort["Cohort_Index"] >= 0]

cohort_size = df_cohort[df_cohort["Cohort_Index"] == 0].groupby("First_Month")["Số_điện_thoại"].nunique()

rows = []
for cohort, size in cohort_size.items():
    d = df_cohort[df_cohort["First_Month"] == cohort]
    row = {"First_Month": str(cohort), "Tổng KH": int(size)}

    for m in range(1, MAX_MONTH + 1):
        kh_quay_lai = d[(d["Cohort_Index"] >= 1) & (d["Cohort_Index"] <= m)]["Số_điện_thoại"].nunique()
        row[f"Sau {m} tháng"] = round(kh_quay_lai / size * 100, 2) if size else 0

    rows.append(row)

retention = pd.DataFrame(rows)

# GRAND TOTAL
if not retention.empty:
    total_kh = retention["Tổng KH"].sum()
    grand = {"First_Month": "Grand Total", "Tổng KH": int(total_kh)}

    for c in retention.columns:
        if c.startswith("Sau"):
            grand[c] = round((retention[c] * retention["Tổng KH"]).sum() / total_kh, 2) if total_kh else 0

    retention = pd.concat([retention, pd.DataFrame([grand])], ignore_index=True)

st.subheader("🏅 Cohort Retention – Cộng dồn (%)")

# format hiển thị retention
if retention.empty:
    st.info("Không có dữ liệu cohort.")
else:
    retention_show = retention.copy()
    retention_show["Tổng KH"] = retention_show["Tổng KH"].apply(fmt_int)
    for c in retention_show.columns:
        if c.startswith("Sau"):
            retention_show[c] = retention_show[c].apply(lambda v: fmt_pct(v, 2))
    show_df(retention_show, title=None)
