# pages/00_general_report.py
import pandas as pd
import numpy as np
import streamlit as st

from load_data import get_active_data, set_active_data
from filters_shared import GLOBAL_PREFIX, init_global_defaults, ms_all, reset_global_filters

# =====================================================
# FORMAT HELPERS
# =====================================================
def fmt_int(x):
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return ""

def fmt_pct(x, decimals=2, with_sign=False):
    if pd.isna(x):
        return ""
    try:
        v = float(x)
        s = f"{v:,.{decimals}f}%"
        if with_sign and v > 0:
            s = "+" + s
        return s
    except Exception:
        return ""

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

# =====================================================
# WEEK HELPERS (TUẦN BẮT ĐẦU THEO THỨ - RIÊNG GENERAL)
# =====================================================
WEEKDAY_MAP = {
    "Thứ 2": 0, "Thứ 3": 1, "Thứ 4": 2, "Thứ 5": 3,
    "Thứ 6": 4, "Thứ 7": 5, "Chủ nhật": 6
}

def week_anchor(dt: pd.Series, week_start: int) -> pd.Series:
    d = pd.to_datetime(dt)
    return (d - pd.to_timedelta((d.dt.weekday - week_start) % 7, unit="D")).dt.normalize()

def week_label_from_anchor(anchor: pd.Series) -> pd.Series:
    iso = pd.to_datetime(anchor).dt.isocalendar()
    return "Tuần " + iso["week"].astype(str).str.zfill(2) + "/" + iso["year"].astype(str)

# =====================================================
# Page config
# =====================================================
st.set_page_config(page_title="Marketing Revenue Dashboard", layout="wide")
st.title("📊 MARKETING REVENUE DASHBOARD – Tổng quan")

# =====================================================
# CHỌN NGUỒN DỮ LIỆU CHO TOÀN APP
# =====================================================
with st.sidebar:
    st.markdown("### 🗂 Chọn nguồn dữ liệu")

    src_choice = st.radio(
        "Nguồn dữ liệu (áp dụng cho tất cả trang)",
        ["Dùng dữ liệu hiện tại", "Upload file parquet từ máy", "Quay lại dữ liệu mặc định"],
        index=0,
        key="data_source_main",
    )

    uploaded_files = None
    if src_choice == "Upload file parquet từ máy":
        uploaded_files = st.file_uploader(
            "📁 Chọn 1 hoặc nhiều file .parquet",
            type=["parquet"],
            accept_multiple_files=True,
            key="parquet_uploader_main",
        )

if src_choice == "Upload file parquet từ máy" and uploaded_files:
    dfs = []
    for f in uploaded_files:
        try:
            dfs.append(pd.read_parquet(f))
        except Exception as e:
            st.warning(f"⚠ Không đọc được file: {getattr(f, 'name', 'unknown')} ({e})")

    df_up = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    df_up = ensure_datetime(df_up)
    df_up = fix_numeric(df_up)

    if df_up.empty:
        st.warning("⚠ File parquet upload không có dữ liệu hợp lệ. Vẫn giữ dữ liệu cũ.")
    else:
        set_active_data(df_up, source="upload")
        st.success(f"✅ Đã cập nhật dữ liệu từ {len(uploaded_files)} file parquet upload")

    del dfs, df_up

elif src_choice == "Quay lại dữ liệu mặc định":
    if "active_df" in st.session_state:
        del st.session_state["active_df"]
    _ = get_active_data()
    st.success("↩ Đã quay lại dùng dữ liệu mặc định trên server")

# =====================================================
# LOAD DATA
# =====================================================
df = get_active_data()
st.sidebar.caption("🔎 Đang dùng nguồn: **{}**".format(st.session_state.get("active_source", "default")))

df = ensure_datetime(df)
df = fix_numeric(df)

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích. Kiểm tra lại nguồn dữ liệu.")
    st.stop()

# ✅ init filter CHUNG 1 lần
init_global_defaults(df)

# =====================================================
# SIDEBAR FILTER
# - Filter CHUNG: f_global_*
# - Filter RIÊNG General: gen_*
# =====================================================
with st.sidebar:
    st.header("🎛️ Bộ lọc dữ liệu (Tổng quan)")

    # (tuỳ bạn) nút reset filter CHUNG toàn app
    # nếu bạn không muốn có nút reset thì xoá 3 dòng này
    if st.button("🔄 Reset bộ lọc (CHUNG)", use_container_width=True):
        reset_global_filters()

    time_type = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý", "Năm"],
        key="gen_time_type",
    )

    # ✅ tuần riêng general
    if time_type == "Tuần":
        gen_week_label = st.selectbox(
            "Tuần bắt đầu từ thứ",
            ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"],
            key="gen_week_start",
        )
        GEN_WEEK_START = WEEKDAY_MAP[gen_week_label]
    else:
        GEN_WEEK_START = 0

    # ✅ date chung toàn app
    start_date = st.date_input(
        "Từ ngày",
        st.session_state[GLOBAL_PREFIX + "start_date"],
        key=GLOBAL_PREFIX + "start_date",
    )
    end_date = st.date_input(
        "Đến ngày",
        st.session_state[GLOBAL_PREFIX + "end_date"],
        key=GLOBAL_PREFIX + "end_date",
    )

    # ✅ filter CHUNG toàn app
    loaiCT_filter = ms_all(
        key=GLOBAL_PREFIX + "loaiCT",
        label="Loại CT",
        options=df["LoaiCT"] if "LoaiCT" in df.columns else [],
    )

    brand_filter = ms_all(
        key=GLOBAL_PREFIX + "brand",
        label="Brand",
        options=df["Brand"] if "Brand" in df.columns else [],
    )

    df_brand = df[df["Brand"].isin(brand_filter)] if (brand_filter and "Brand" in df.columns) else df.iloc[0:0]
    region_filter = ms_all(
        key=GLOBAL_PREFIX + "region",
        label="Region",
        options=df_brand["Region"] if "Region" in df_brand.columns else [],
    )

    df_brand_region = df_brand[df_brand["Region"].isin(region_filter)] if (region_filter and "Region" in df_brand.columns) else df_brand.iloc[0:0]
    store_filter = ms_all(
        key=GLOBAL_PREFIX + "store",
        label="Cửa hàng",
        options=df_brand_region["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df_brand_region.columns else [],
    )

# =====================================================
# APPLY FILTER (CHUNG)
# =====================================================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))

if "LoaiCT" in df.columns:
    mask &= df["LoaiCT"].isin(loaiCT_filter if loaiCT_filter else [])
if "Brand" in df.columns:
    mask &= df["Brand"].isin(brand_filter if brand_filter else [])
if "Region" in df.columns:
    mask &= df["Region"].isin(region_filter if region_filter else [])
if "Điểm_mua_hàng" in df.columns:
    mask &= df["Điểm_mua_hàng"].isin(store_filter if store_filter else [])

df_f = df.loc[mask].copy()

if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# TIME COLUMN
# =====================================================
df_f_time = df_f.copy()

if time_type == "Ngày":
    df_f_time["Time"] = df_f_time["Ngày"].dt.date.astype(str)
elif time_type == "Tuần":
    df_f_time["_WeekAnchor"] = week_anchor(df_f_time["Ngày"], GEN_WEEK_START)
    df_f_time["Time"] = week_label_from_anchor(df_f_time["_WeekAnchor"])
elif time_type == "Tháng":
    df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("M").astype(str)
elif time_type == "Quý":
    df_f_time["Time"] = df_f_time["Ngày"].dt.to_period("Q").astype(str)
elif time_type == "Năm":
    df_f_time["Time"] = df_f_time["Ngày"].dt.year.astype(str)

# =====================================================
# KPI
# =====================================================
gross = float(df_f["Tổng_Gross"].sum()) if "Tổng_Gross" in df_f.columns else 0
net = float(df_f["Tổng_Net"].sum()) if "Tổng_Net" in df_f.columns else 0
orders = df_f["Số_CT"].nunique() if "Số_CT" in df_f.columns else 0
customers = df_f["Số_điện_thoại"].nunique() if "Số_điện_thoại" in df_f.columns else 0
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gross", value=f"{gross:,.0f}")
c2.metric("Net", value=f"{net:,.0f}")
c3.metric("CK %", value=f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", value=f"{orders:,}")
c5.metric("Khách hàng", value=f"{customers:,}")

# =====================================================
# TIME GROUP (TUẦN: group theo anchor)
# =====================================================
def group_time(df_in: pd.DataFrame, tt: str, week_start: int) -> pd.DataFrame:
    if tt == "Tuần":
        tmp = df_in.copy()
        tmp["_WeekAnchor"] = week_anchor(tmp["Ngày"], week_start)
        d = (
            tmp.groupby("_WeekAnchor", dropna=False)
            .agg(
                Gross=("Tổng_Gross", "sum"),
                Net=("Tổng_Net", "sum"),
                Orders=("Số_CT", "nunique"),
                Customers=("Số_điện_thoại", "nunique"),
            )
            .reset_index()
            .rename(columns={"_WeekAnchor": "Ngày"})
            .sort_values("Ngày")
        )
    else:
        freq_map = {"Ngày": "D", "Tháng": "ME", "Quý": "Q", "Năm": "Y"}
        d = (
            df_in.set_index("Ngày")
            .resample(freq_map[tt])
            .agg(
                Gross=("Tổng_Gross", "sum"),
                Net=("Tổng_Net", "sum"),
                Orders=("Số_CT", "nunique"),
                Customers=("Số_điện_thoại", "nunique"),
            )
            .reset_index()
            .sort_values("Ngày")
        )

    d["CK_%"] = np.where(d["Gross"] > 0, (1 - d["Net"] / d["Gross"]) * 100, 0)
    d["Net_prev"] = d["Net"].shift(1)
    d["Growth_%"] = np.where(d["Net_prev"] > 0, (d["Net"] - d["Net_prev"]) / d["Net_prev"] * 100, 0)
    return d

df_time = group_time(df_f, time_type, GEN_WEEK_START)

st.subheader(f"⏱ Theo thời gian ({time_type})")
df_time_show = df_time.copy()

if time_type == "Tuần":
    df_time_show["Ngày"] = week_label_from_anchor(df_time_show["Ngày"])
else:
    df_time_show["Ngày"] = pd.to_datetime(df_time_show["Ngày"], errors="coerce").dt.strftime("%Y-%m-%d")

for c in ["Gross", "Net", "Orders", "Customers", "Net_prev"]:
    if c in df_time_show.columns:
        df_time_show[c] = df_time_show[c].apply(fmt_int)
for c in ["CK_%", "Growth_%"]:
    if c in df_time_show.columns:
        df_time_show[c] = df_time_show[c].apply(lambda v: fmt_pct(v, 2, with_sign=(c == "Growth_%")))

st.dataframe(df_time_show, use_container_width=True, hide_index=True)

# =====================================================
# REGION + TIME
# =====================================================
st.subheader(f"🌍 Theo Region + {time_type}")

df_region_time = (
    df_f_time.groupby(["Time", "Region"], dropna=False)
    .agg(
        Gross=("Tổng_Gross", "sum"),
        Net=("Tổng_Net", "sum"),
        Orders=("Số_CT", "nunique"),
        Customers=("Số_điện_thoại", "nunique"),
    )
    .reset_index()
)

df_region_time["CK_%"] = np.where(df_region_time["Gross"] > 0, (df_region_time["Gross"] - df_region_time["Net"]) / df_region_time["Gross"] * 100, 0)
df_region_time = df_region_time.sort_values(["Time", "Net"], ascending=[True, False])

df_region_time_show = df_region_time.copy()
for c in ["Gross", "Net", "Orders", "Customers"]:
    df_region_time_show[c] = df_region_time_show[c].apply(fmt_int)
df_region_time_show["CK_%"] = df_region_time_show["CK_%"].apply(lambda v: fmt_pct(v, 2))

st.dataframe(df_region_time_show, use_container_width=True, hide_index=True)

# =====================================================
# STORE SUMMARY
# =====================================================
st.subheader("🏪 Tổng quan theo Cửa hàng")

df_store = (
    df_f.groupby("Điểm_mua_hàng", dropna=False)
    .agg(
        Gross=("Tổng_Gross", "sum"),
        Net=("Tổng_Net", "sum"),
        Orders=("Số_CT", "nunique"),
        Customers=("Số_điện_thoại", "nunique"),
    )
    .reset_index()
)

df_store["CK_%"] = np.where(df_store["Gross"] > 0, (df_store["Gross"] - df_store["Net"]) / df_store["Gross"] * 100, 0)

df_store_show = df_store.sort_values("Net", ascending=False).copy()
for c in ["Gross", "Net", "Orders", "Customers"]:
    df_store_show[c] = df_store_show[c].apply(fmt_int)
df_store_show["CK_%"] = df_store_show["CK_%"].apply(lambda v: fmt_pct(v, 2))

st.dataframe(df_store_show, use_container_width=True, hide_index=True)

# =====================================================
# PRODUCT SUMMARY (THEO MÃ_NB) - RIÊNG GENERAL
# =====================================================
st.subheader("📦 Theo Nhóm SP / Mã NB")

df_product = df_f.copy()

col1, col2 = st.columns(2)
with col1:
    nhom_vals = sorted(df_product["Nhóm_hàng"].dropna().unique()) if "Nhóm_hàng" in df_product.columns else []
    nhom_sp_selected = st.multiselect("📦 Chọn Nhóm SP", nhom_vals, key="gen_nhom_sp")
with col2:
    ma_vals = sorted(df_product["Mã_NB"].dropna().unique()) if "Mã_NB" in df_product.columns else []
    ma_nb_selected = st.multiselect("🏷️ Chọn Mã NB", ma_vals, key="gen_ma_nb")

if nhom_sp_selected and "Nhóm_hàng" in df_product.columns:
    df_product = df_product[df_product["Nhóm_hàng"].isin(nhom_sp_selected)]
if ma_nb_selected and "Mã_NB" in df_product.columns:
    df_product = df_product[df_product["Mã_NB"].isin(ma_nb_selected)]

orders_agg = ("Số_lượng", "sum") if "Số_lượng" in df_product.columns else ("Số_CT", "nunique")

df_product_group = (
    df_product.groupby("Mã_NB", dropna=False)
    .agg(
        Gross=("Tổng_Gross", "sum"),
        Net=("Tổng_Net", "sum"),
        Orders=orders_agg,
        Customers=("Số_điện_thoại", "nunique"),
    )
    .reset_index()
    .sort_values("Net", ascending=False)
)

df_product_show = df_product_group.copy()
for c in ["Gross", "Net", "Orders", "Customers"]:
    df_product_show[c] = df_product_show[c].apply(fmt_int)

st.dataframe(df_product_show, use_container_width=True, hide_index=True)
