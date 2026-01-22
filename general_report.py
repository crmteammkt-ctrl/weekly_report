# pages/00_general_report.py
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

from load_data import get_active_data, set_active_data

# =====================================================
# FORMAT HELPERS (an toàn - không phụ thuộc Streamlit version)
# =====================================================
def fmt_int(x):
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):,.0f}"
    except:
        return ""

def fmt_pct(x, decimals=2, with_sign=False):
    # x đang là 20.8 nghĩa là 20.8%
    if pd.isna(x):
        return ""
    try:
        v = float(x)
        s = f"{v:,.{decimals}f}%"
        if with_sign and v > 0:
            s = "+" + s
        return s
    except:
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

# Xử lý upload / reset
if src_choice == "Upload file parquet từ máy" and uploaded_files:
    # KHÔNG cache để tránh giữ nhiều bản copy => giảm nguy cơ vượt RAM
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

    # giải phóng tham chiếu list (giảm nguy cơ giữ RAM)
    del dfs, df_up

elif src_choice == "Quay lại dữ liệu mặc định":
    if "active_df" in st.session_state:
        del st.session_state["active_df"]
    _ = get_active_data()
    st.success("↩ Đã quay lại dùng dữ liệu mặc định trên server")

# Luôn lấy lại dữ liệu đang active
df = get_active_data()
st.sidebar.caption(
    "🔎 Đang dùng nguồn: **{}**".format(st.session_state.get("active_source", "default"))
)

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
    st.header("🎛️ Bộ lọc dữ liệu (Tổng quan)")

    time_type = st.selectbox("Phân tích theo", ["Ngày", "Tuần", "Tháng", "Quý", "Năm"])

    start_date = st.date_input("Từ ngày", df["Ngày"].min().date())
    end_date   = st.date_input("Đến ngày", df["Ngày"].max().date())

    # Loại CT (độc lập)
    all_loaiCT = sorted(df["LoaiCT"].dropna().unique()) if "LoaiCT" in df.columns else []
    loaiCT_ui = st.multiselect("Loại CT", with_all_option(all_loaiCT), default=["All"])
    loaiCT_filter = normalize_filter(loaiCT_ui, all_loaiCT)

    # Brand
    all_brand = sorted(df["Brand"].dropna().unique()) if "Brand" in df.columns else []
    brand_ui = st.multiselect("Brand", with_all_option(all_brand), default=["All"])
    brand_filter = normalize_filter(brand_ui, all_brand)

    df_brand = df[df["Brand"].isin(brand_filter)] if (all_brand and brand_filter) else df.iloc[0:0]

    # Region (phụ thuộc Brand)
    all_region = sorted(df_brand["Region"].dropna().unique()) if "Region" in df_brand.columns else []
    region_ui = st.multiselect("Region", with_all_option(all_region), default=["All"])
    region_filter = normalize_filter(region_ui, all_region)

    df_brand_region = df_brand[df_brand["Region"].isin(region_filter)] if (all_region and region_filter) else df_brand.iloc[0:0]

    # Store (phụ thuộc Brand + Region)
    all_store = sorted(df_brand_region["Điểm_mua_hàng"].dropna().unique()) if "Điểm_mua_hàng" in df_brand_region.columns else []
    store_ui = st.multiselect("Cửa hàng", with_all_option(all_store), default=["All"])
    store_filter = normalize_filter(store_ui, all_store)


# =====================================================
# APPLY FILTER
# =====================================================
mask = (
    (df["Ngày"] >= pd.to_datetime(start_date))
    & (df["Ngày"] <= pd.to_datetime(end_date))
)

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
    iso = df_f_time["Ngày"].dt.isocalendar()
    df_f_time["Time"] = ("Tuần " + iso["week"].astype(str).str.zfill(2) + "/" + iso["year"].astype(str))
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
net   = float(df_f["Tổng_Net"].sum()) if "Tổng_Net" in df_f.columns else 0
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
# TIME GROUP
# =====================================================
def group_time(df_in: pd.DataFrame, tt: str) -> pd.DataFrame:
    freq_map = {"Ngày": "D", "Tuần": "W", "Tháng": "ME", "Quý": "Q", "Năm": "Y"}
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
    )
    d["CK_%"] = np.where(d["Gross"] > 0, (1 - d["Net"] / d["Gross"]) * 100, 0)
    d["Net_prev"] = d["Net"].shift(1)
    d["Growth_%"] = np.where(d["Net_prev"] > 0, (d["Net"] - d["Net_prev"]) / d["Net_prev"] * 100, 0)
    return d

df_time = group_time(df_f, time_type)

st.subheader(f"⏱ Theo thời gian ({time_type})")
df_time_show = df_time.copy()
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
def group_region_time(df_in: pd.DataFrame) -> pd.DataFrame:
    d = (
        df_in.groupby(["Time", "Region"], dropna=False)
        .agg(
            Gross=("Tổng_Gross", "sum"),
            Net=("Tổng_Net", "sum"),
            Orders=("Số_CT", "nunique"),
            Customers=("Số_điện_thoại", "nunique"),
        )
        .reset_index()
    )
    d["CK_%"] = np.where(d["Gross"] > 0, (d["Gross"] - d["Net"]) / d["Gross"] * 100, 0)
    return d.sort_values(["Time", "Net"], ascending=[True, False])

df_region_time = group_region_time(df_f_time)

st.subheader(f"🌍 Theo Region + {time_type}")
df_region_time_show = df_region_time.copy()
df_region_time_show["Time"] = df_region_time_show["Time"].astype(str)

for c in ["Gross", "Net", "Orders", "Customers"]:
    if c in df_region_time_show.columns:
        df_region_time_show[c] = df_region_time_show[c].apply(fmt_int)
if "CK_%" in df_region_time_show.columns:
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
# PRODUCT SUMMARY
# =====================================================
st.subheader("📦 Theo Nhóm SP / Mã NB")

df_product = df_f.copy()

col1, col2 = st.columns(2)
with col1:
    nhom_vals = sorted(df_product["Nhóm_hàng"].dropna().unique()) if "Nhóm_hàng" in df_product.columns else []
    nhom_sp_selected = st.multiselect("📦 Chọn Nhóm SP", nhom_vals)
with col2:
    ma_vals = sorted(df_product["Mã_NB"].dropna().unique()) if "Mã_NB" in df_product.columns else []
    ma_nb_selected = st.multiselect("🏷️ Chọn Mã NB", ma_vals)

if nhom_sp_selected and "Nhóm_hàng" in df_product.columns:
    df_product = df_product[df_product["Nhóm_hàng"].isin(nhom_sp_selected)]
if ma_nb_selected and "Mã_NB" in df_product.columns:
    df_product = df_product[df_product["Mã_NB"].isin(ma_nb_selected)]

df_product_group = (
    df_product.groupby("Mã_NB", dropna=False)
    .agg(
        Gross=("Tổng_Gross", "sum"),
        Net=("Tổng_Net", "sum"),
        Orders=("Số_CT", "nunique"),
        Customers=("Số_điện_thoại", "nunique"),
    )
    .reset_index()
    .sort_values("Net", ascending=False)
)

df_product_show = df_product_group.copy()
for c in ["Gross", "Net", "Orders", "Customers"]:
    if c in df_product_show.columns:
        df_product_show[c] = df_product_show[c].apply(fmt_int)

st.dataframe(df_product_show, use_container_width=True, hide_index=True)
 