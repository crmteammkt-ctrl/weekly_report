# pages/00_general_report.py
import pandas as pd
import numpy as np
import streamlit as st

from load_data import get_active_data, set_active_data

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
# WEEK HELPERS (GENERAL - riêng trang)
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
# FILTER HELPERS
# =====================================================
GEN = "gen_"

def reset_by_prefix(prefix: str):
    for k in list(st.session_state.keys()):
        if k.startswith(prefix):
            st.session_state.pop(k, None)
    st.rerun()

def ms_all(key: str, label: str, options, all_label="All", default_all=True):
    opts = pd.Series(list(options)).dropna().astype(str).str.strip()
    opts = sorted(opts.unique().tolist())
    ui_opts = [all_label] + opts

    if key not in st.session_state:
        st.session_state[key] = [all_label] if default_all else (opts[:1] if opts else [all_label])

    cur = [str(x).strip() for x in st.session_state.get(key, []) if str(x).strip() in ui_opts]
    if not cur:
        cur = [all_label] if default_all else (opts[:1] if opts else [all_label])
        st.session_state[key] = cur

    selected = st.multiselect(label, options=ui_opts, key=key)

    if (not selected) or (all_label in selected):
        return opts
    return [x for x in selected if x in opts]

# =====================================================
# PAGE
# =====================================================
st.set_page_config(page_title="Marketing Revenue Dashboard – Tổng quan", layout="wide")
st.title("📊 MARKETING REVENUE DASHBOARD – Tổng quan")

# =====================================================
# DATA SOURCE (giữ y như bạn đang dùng)
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
    if not df_up.empty:
        set_active_data(df_up, source="upload")
        st.success(f"✅ Đã cập nhật dữ liệu từ {len(uploaded_files)} file parquet upload")
    else:
        st.warning("⚠ File parquet upload không có dữ liệu hợp lệ. Vẫn giữ dữ liệu cũ.")

elif src_choice == "Quay lại dữ liệu mặc định":
    if "active_df" in st.session_state:
        del st.session_state["active_df"]
    _ = get_active_data()
    st.success("↩ Đã quay lại dùng dữ liệu mặc định trên server")

df = get_active_data()
st.sidebar.caption("🔎 Đang dùng nguồn: **{}**".format(st.session_state.get("active_source", "default")))

df = ensure_datetime(df)
df = fix_numeric(df)

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích.")
    st.stop()

# =====================================================
# SIDEBAR FILTER (GENERAL) - KHÔNG reset khi chuyển trang
# =====================================================
with st.sidebar:
    st.header("🎛️ Bộ lọc dữ liệu (Tổng quan)")

    if st.button("🔄 Reset bộ lọc (General)", use_container_width=True):
        reset_by_prefix(GEN)

    time_type = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý", "Năm"],
        key=GEN + "time_type",
    )

    if time_type == "Tuần":
        gen_week_label = st.selectbox(
            "Tuần bắt đầu từ thứ",
            list(WEEKDAY_MAP.keys()),
            key=GEN + "week_start",
        )
        week_start = WEEKDAY_MAP[gen_week_label]
    else:
        week_start = 0

    # ✅ init mặc định 1 lần (để tránh KeyError)
    if GEN + "start_date" not in st.session_state:
        st.session_state[GEN + "start_date"] = df["Ngày"].min().date()
    if GEN + "end_date" not in st.session_state:
        st.session_state[GEN + "end_date"] = df["Ngày"].max().date()

    start_date = st.date_input("Từ ngày", key=GEN + "start_date")
    end_date = st.date_input("Đến ngày", key=GEN + "end_date")

    loaiCT = ms_all(GEN + "loaiCT", "Loại CT", df["LoaiCT"] if "LoaiCT" in df.columns else [])
    brand = ms_all(GEN + "brand", "Brand", df["Brand"] if "Brand" in df.columns else [])

    df_b = df[df["Brand"].isin(brand)] if ("Brand" in df.columns) else df
    region = ms_all(GEN + "region", "Region", df_b["Region"] if "Region" in df_b.columns else [])

    df_br = df_b[df_b["Region"].isin(region)] if ("Region" in df_b.columns) else df_b
    store = ms_all(GEN + "store", "Cửa hàng", df_br["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df_br.columns else [])

# =====================================================
# APPLY FILTER
# =====================================================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))
if "LoaiCT" in df.columns: mask &= df["LoaiCT"].isin(loaiCT)
if "Brand" in df.columns: mask &= df["Brand"].isin(brand)
if "Region" in df.columns: mask &= df["Region"].isin(region)
if "Điểm_mua_hàng" in df.columns: mask &= df["Điểm_mua_hàng"].isin(store)

df_f = df.loc[mask].copy()
if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# TIME KEY (datetime để sort/group chuẩn)
# =====================================================
if time_type == "Ngày":
    df_f = df_f.assign(Time=df_f["Ngày"].dt.normalize())
elif time_type == "Tuần":
    anch = week_anchor(df_f["Ngày"], week_start)
    df_f = df_f.assign(Time=anch)
elif time_type == "Tháng":
    df_f = df_f.assign(Time=df_f["Ngày"].dt.to_period("M").dt.to_timestamp())
elif time_type == "Quý":
    df_f = df_f.assign(Time=df_f["Ngày"].dt.to_period("Q").dt.to_timestamp())
else:  # Năm
    df_f = df_f.assign(Time=pd.to_datetime(df_f["Ngày"].dt.year.astype(str) + "-01-01"))

# =====================================================
# KPI
# =====================================================
gross = float(df_f["Tổng_Gross"].sum()) if "Tổng_Gross" in df_f.columns else 0
net = float(df_f["Tổng_Net"].sum()) if "Tổng_Net" in df_f.columns else 0
orders = df_f["Số_CT"].nunique() if "Số_CT" in df_f.columns else 0
customers = df_f["Số_điện_thoại"].nunique() if "Số_điện_thoại" in df_f.columns else 0
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gross", f"{gross:,.0f}")
c2.metric("Net", f"{net:,.0f}")
c3.metric("CK %", f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", f"{orders:,}")
c5.metric("Khách hàng", f"{customers:,}")

# =====================================================
# CACHE GROUPBYS (tăng tốc)
# =====================================================
@st.cache_data(show_spinner=False)
def build_time_table(df_in: pd.DataFrame) -> pd.DataFrame:
    g = (
        df_in.groupby("Time", observed=True)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique"),
        )
        .reset_index()
        .sort_values("Time")
    )
    g["CK_%"] = np.where(g["Gross"]>0, (1 - g["Net"]/g["Gross"])*100, 0)
    g["Net_prev"] = g["Net"].shift(1)
    g["Growth_%"] = np.where(g["Net_prev"]>0, (g["Net"]-g["Net_prev"])/g["Net_prev"]*100, np.nan)
    return g

@st.cache_data(show_spinner=False)
def build_region_time(df_in: pd.DataFrame) -> pd.DataFrame:
    if "Region" not in df_in.columns:
        return pd.DataFrame()

    g = (
        df_in.groupby(["Time","Region"], observed=True, dropna=False)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique"),
        )
        .reset_index()
        .sort_values(["Region","Time"])
    )
    g["CK_%"] = np.where(g["Gross"]>0, (1 - g["Net"]/g["Gross"])*100, 0)

    # ✅ Prev Net + Change% theo từng Region
    g["Prev_Net"] = g.groupby("Region")["Net"].shift(1)
    g["Change%"] = np.where(
        g["Prev_Net"] > 0,
        (g["Net"] - g["Prev_Net"]) / g["Prev_Net"] * 100,
        np.nan
    )
    return g

@st.cache_data(show_spinner=False)
def build_store(df_in: pd.DataFrame) -> pd.DataFrame:
    if "Điểm_mua_hàng" not in df_in.columns:
        return pd.DataFrame()
    g = (
        df_in.groupby("Điểm_mua_hàng", observed=True, dropna=False)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique"),
        )
        .reset_index()
    )
    g["CK_%"] = np.where(g["Gross"]>0, (1 - g["Net"]/g["Gross"])*100, 0)
    return g.sort_values("Net", ascending=False)

# =====================================================
# TIME TABLE
# =====================================================
st.subheader(f"⏱ Theo thời gian ({time_type})")
g_time = build_time_table(df_f)
g_time_show = g_time.copy()

if time_type == "Ngày":
    g_time_show["Kỳ"] = g_time_show["Time"].dt.strftime("%Y-%m-%d")
elif time_type == "Tuần":
    g_time_show["Kỳ"] = week_label_from_anchor(g_time_show["Time"])
elif time_type == "Tháng":
    g_time_show["Kỳ"] = g_time_show["Time"].dt.to_period("M").astype(str)
elif time_type == "Quý":
    g_time_show["Kỳ"] = g_time_show["Time"].dt.to_period("Q").astype(str)
else:
    g_time_show["Kỳ"] = g_time_show["Time"].dt.year.astype(str)

g_time_show = g_time_show.drop(columns=["Time"])
for c in ["Gross","Net","Orders","Customers","Net_prev"]:
    g_time_show[c] = g_time_show[c].apply(fmt_int)
for c in ["CK_%","Growth_%"]:
    g_time_show[c] = g_time_show[c].apply(lambda v: fmt_pct(v,2,with_sign=(c=="Growth_%")))
st.dataframe(g_time_show[["Kỳ","Gross","Net","Orders","Customers","CK_%","Net_prev","Growth_%"]], use_container_width=True, hide_index=True)

# =====================================================
# REGION + TIME (Prev Net + Change%)
# =====================================================
st.subheader(f"🌍 Theo Region + {time_type}")
g_rt = build_region_time(df_f)
if g_rt.empty:
    st.info("Thiếu cột Region hoặc không có dữ liệu.")
else:
    g_rt_show = g_rt.copy()
    if time_type == "Ngày":
        g_rt_show["Kỳ"] = g_rt_show["Time"].dt.strftime("%Y-%m-%d")
    elif time_type == "Tuần":
        g_rt_show["Kỳ"] = week_label_from_anchor(g_rt_show["Time"])
    elif time_type == "Tháng":
        g_rt_show["Kỳ"] = g_rt_show["Time"].dt.to_period("M").astype(str)
    elif time_type == "Quý":
        g_rt_show["Kỳ"] = g_rt_show["Time"].dt.to_period("Q").astype(str)
    else:
        g_rt_show["Kỳ"] = g_rt_show["Time"].dt.year.astype(str)

    g_rt_show = g_rt_show.drop(columns=["Time"]).sort_values(["Kỳ","Net"], ascending=[True,False])

    for c in ["Gross","Net","Orders","Customers","Prev_Net"]:
        g_rt_show[c] = g_rt_show[c].apply(fmt_int)
    for c in ["CK_%","Change%"]:
        g_rt_show[c] = g_rt_show[c].apply(lambda v: fmt_pct(v,2,with_sign=(c=="Change%")))

    st.dataframe(
        g_rt_show[["Kỳ","Region","Gross","Net","Orders","Customers","CK_%","Prev_Net","Change%"]],
        use_container_width=True,
        hide_index=True
    )

# =====================================================
# STORE SUMMARY
# =====================================================
st.subheader("🏪 Tổng quan theo Cửa hàng")
g_store = build_store(df_f)
if g_store.empty:
    st.info("Thiếu cột Điểm_mua_hàng.")
else:
    g_store_show = g_store.copy()
    for c in ["Gross","Net","Orders","Customers"]:
        g_store_show[c] = g_store_show[c].apply(fmt_int)
    g_store_show["CK_%"] = g_store_show["CK_%"].apply(lambda v: fmt_pct(v,2))
    st.dataframe(g_store_show, use_container_width=True, hide_index=True)

# =====================================================
# PRODUCT SUMMARY (Mã NB) + CK%
# =====================================================
st.subheader("📦 Theo Nhóm SP / Mã NB")

df_product = df_f.copy()

col1, col2 = st.columns(2)
with col1:
    nhom_vals = sorted(df_product["Nhóm_hàng"].dropna().unique()) if "Nhóm_hàng" in df_product.columns else []
    nhom_sp = st.multiselect("📦 Chọn Nhóm SP", nhom_vals, key=GEN + "nhom_sp")
with col2:
    ma_vals = sorted(df_product["Mã_NB"].dropna().unique()) if "Mã_NB" in df_product.columns else []
    ma_nb = st.multiselect("🏷️ Chọn Mã NB", ma_vals, key=GEN + "ma_nb")

if nhom_sp and "Nhóm_hàng" in df_product.columns:
    df_product = df_product[df_product["Nhóm_hàng"].isin(nhom_sp)]
if ma_nb and "Mã_NB" in df_product.columns:
    df_product = df_product[df_product["Mã_NB"].isin(ma_nb)]

if df_product.empty or "Mã_NB" not in df_product.columns:
    st.info("Không có dữ liệu hoặc thiếu cột Mã_NB.")
else:
    # Orders: ưu tiên Số_lượng nếu có
    if "Số_lượng" in df_product.columns:
        orders_agg = ("Số_lượng","sum")
    else:
        orders_agg = ("Số_CT","nunique")

    g_prod = (
        df_product.groupby("Mã_NB", observed=True, dropna=False)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=orders_agg,
            Customers=("Số_điện_thoại","nunique"),
        )
        .reset_index()
        .sort_values("Net", ascending=False)
    )
    g_prod["CK_%"] = np.where(g_prod["Gross"]>0, (1 - g_prod["Net"]/g_prod["Gross"])*100, 0)

    g_prod_show = g_prod.copy()
    for c in ["Gross","Net","Orders","Customers"]:
        g_prod_show[c] = g_prod_show[c].apply(fmt_int)
    g_prod_show["CK_%"] = g_prod_show["CK_%"].apply(lambda v: fmt_pct(v,2))

    st.dataframe(g_prod_show, use_container_width=True, hide_index=True)
