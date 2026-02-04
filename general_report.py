# pages/00_general_report.py
import pandas as pd
import numpy as np
import streamlit as st

from load_data import get_active_data, set_active_data

# =====================================================
# PERF UTILS
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

def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    # Chỉ ép dtype những cột hay dùng để group/filter
    cat_cols = [
        "LoaiCT", "Brand", "Region", "Điểm_mua_hàng",
        "Nhóm_hàng", "Mã_NB", "Kiểm_tra_tên", "Trạng_thái_số_điện_thoại"
    ]
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].astype("category")

    num_cols = ["Tổng_Gross", "Tổng_Net", "Số_lượng"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Số_điện_thoại: để string cho nunique nhanh/ổn định
    if "Số_điện_thoại" in df.columns:
        df["Số_điện_thoại"] = df["Số_điện_thoại"].astype(str)

    return df

# ============ Week helpers (riêng trang) ============
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
# FILTER HELPERS (giữ state - không reset khi đổi trang)
# =====================================================
GEN = "gen_"

def init_defaults(df: pd.DataFrame):
    st.session_state.setdefault(GEN + "time_type", "Ngày")
    st.session_state.setdefault(GEN + "week_start", "Thứ 2")
    st.session_state.setdefault(GEN + "start_date", df["Ngày"].min().date())
    st.session_state.setdefault(GEN + "end_date", df["Ngày"].max().date())

    # multiselect dạng list
    for k in ["loaiCT", "brand", "region", "store"]:
        st.session_state.setdefault_toggle = None
        st.session_state.setdefault(GEN + k, ["All"])

def ms_all(key: str, label: str, options, all_label="All"):
    opts = pd.Series(list(options)).dropna().astype(str)
    opts = sorted(opts.unique().tolist())
    ui = [all_label] + opts

    cur = st.session_state.get(key, [all_label])
    cur = [x for x in cur if x in ui]
    if not cur:
        cur = [all_label]
        st.session_state[key] = cur

    st.multiselect(label, options=ui, key=key)
    selected = st.session_state.get(key, [all_label])

    if (not selected) or (all_label in selected):
        return opts
    return [x for x in selected if x in opts]

# =====================================================
# PAGE
# =====================================================
st.set_page_config(page_title="Marketing Revenue Dashboard", layout="wide")
st.title("📊 MARKETING REVENUE DASHBOARD – Tổng quan")

# ====== Upload parquet (tối ưu: chỉ xử lý khi bấm nút) ======
with st.sidebar:
    st.markdown("### 🗂 Nguồn dữ liệu (tùy chọn)")
    up_files = st.file_uploader("📁 Upload .parquet", type=["parquet"], accept_multiple_files=True, key="gen_upload")
    if up_files:
        if st.button("✅ Áp dụng file upload", use_container_width=True):
            dfs = []
            for f in up_files:
                try:
                    dfs.append(pd.read_parquet(f))
                except Exception as e:
                    st.warning(f"⚠ Không đọc được {getattr(f,'name','file')}: {e}")
            df_up = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            df_up = ensure_datetime(df_up)
            df_up = optimize_dtypes(df_up)
            if df_up.empty:
                st.warning("⚠ File upload không có dữ liệu hợp lệ.")
            else:
                set_active_data(df_up, source="upload")
                st.success(f"✅ Đã set dữ liệu upload ({len(df_up):,} dòng)")
            st.rerun()

    if st.button("↩ Quay về dữ liệu mặc định", use_container_width=True):
        if "active_df" in st.session_state:
            del st.session_state["active_df"]
        st.session_state["active_source"] = "default"
        st.success("✅ Đã quay về mặc định")
        st.rerun()

df = get_active_data()
df = ensure_datetime(df)
df = optimize_dtypes(df)

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích.")
    st.stop()

init_defaults(df)

# =====================================================
# SIDEBAR FILTER
# =====================================================
with st.sidebar:
    st.header("🎛️ Bộ lọc (General)")

    time_type = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý", "Năm"],
        key=GEN + "time_type",
    )

    if time_type == "Tuần":
        st.selectbox(
            "Tuần bắt đầu từ thứ",
            list(WEEKDAY_MAP.keys()),
            key=GEN + "week_start",
        )

    st.date_input("Từ ngày", key=GEN + "start_date")
    st.date_input("Đến ngày", key=GEN + "end_date")

    start_date = st.session_state[GEN + "start_date"]
    end_date = st.session_state[GEN + "end_date"]

    # options lấy từ df (category) nhanh hơn
    loaiCT = ms_all(GEN + "loaiCT", "Loại CT", df["LoaiCT"] if "LoaiCT" in df.columns else [])
    brand  = ms_all(GEN + "brand", "Brand", df["Brand"] if "Brand" in df.columns else [])

    # cascade nhanh: lọc nhẹ theo brand -> region -> store
    df_b = df[df["Brand"].isin(brand)] if ("Brand" in df.columns and brand) else df.iloc[0:0]
    region = ms_all(GEN + "region", "Region", df_b["Region"] if "Region" in df_b.columns else [])

    df_br = df_b[df_b["Region"].isin(region)] if ("Region" in df_b.columns and region) else df_b.iloc[0:0]
    store  = ms_all(GEN + "store", "Cửa hàng", df_br["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df_br.columns else [])

# =====================================================
# APPLY FILTER (nhanh: mask + chỉ dùng cột cần)
# =====================================================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))

if "LoaiCT" in df.columns: mask &= df["LoaiCT"].isin(loaiCT)
if "Brand" in df.columns:  mask &= df["Brand"].isin(brand)
if "Region" in df.columns: mask &= df["Region"].isin(region)
if "Điểm_mua_hàng" in df.columns: mask &= df["Điểm_mua_hàng"].isin(store)

# CHỈ lấy cột cần dùng để report (giảm RAM & speed groupby)
need_cols = [c for c in [
    "Ngày","LoaiCT","Brand","Region","Điểm_mua_hàng",
    "Nhóm_hàng","Mã_NB","Số_CT","Số_điện_thoại","Số_lượng",
    "Tổng_Gross","Tổng_Net"
] if c in df.columns]

df_f = df.loc[mask, need_cols]
if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi lọc.")
    st.stop()

# =====================================================
# KPI
# =====================================================
gross = float(df_f["Tổng_Gross"].sum()) if "Tổng_Gross" in df_f.columns else 0.0
net   = float(df_f["Tổng_Net"].sum())   if "Tổng_Net" in df_f.columns else 0.0
orders = df_f["Số_CT"].nunique() if "Số_CT" in df_f.columns else 0
customers = df_f["Số_điện_thoại"].nunique() if "Số_điện_thoại" in df_f.columns else 0
ck_rate = (1 - net / gross) * 100 if gross > 0 else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Gross", f"{gross:,.0f}")
c2.metric("Net", f"{net:,.0f}")
c3.metric("CK %", f"{ck_rate:.2f}%")
c4.metric("Đơn hàng", f"{orders:,}")
c5.metric("Khách hàng", f"{customers:,}")

# =====================================================
# TIME KEY + GROUP (tối ưu: không resample tuần, group theo anchor)
# =====================================================
week_start = WEEKDAY_MAP.get(st.session_state.get(GEN + "week_start", "Thứ 2"), 0)

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

g_time = (
    df_f.groupby("Time", observed=True)
    .agg(
        Gross=("Tổng_Gross","sum"),
        Net=("Tổng_Net","sum"),
        Orders=("Số_CT","nunique"),
        Customers=("Số_điện_thoại","nunique"),
    )
    .reset_index()
    .sort_values("Time")
)

g_time["CK_%"] = np.where(g_time["Gross"]>0, (1 - g_time["Net"]/g_time["Gross"])*100, 0)
g_time["Net_prev"] = g_time["Net"].shift(1)
g_time["Growth_%"] = np.where(g_time["Net_prev"]>0, (g_time["Net"]-g_time["Net_prev"])/g_time["Net_prev"]*100, 0)

st.subheader(f"⏱ Theo thời gian ({time_type})")
show = g_time.copy()
if time_type == "Tuần":
    show["Kỳ"] = week_label_from_anchor(show["Time"])
else:
    show["Kỳ"] = pd.to_datetime(show["Time"]).dt.strftime("%Y-%m-%d")
show = show.drop(columns=["Time"])

for c in ["Gross","Net","Orders","Customers","Net_prev"]:
    show[c] = show[c].apply(fmt_int)
show["CK_%"] = show["CK_%"].apply(lambda v: fmt_pct(v,2))
show["Growth_%"] = show["Growth_%"].apply(lambda v: fmt_pct(v,2,with_sign=True))

st.dataframe(show, use_container_width=True, hide_index=True)

# =====================================================
# REGION + TIME
# =====================================================
if "Region" in df_f.columns:
    g_rt = (
        df_f.groupby(["Time","Region"], observed=True)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique"),
        )
        .reset_index()
    )
    g_rt["CK_%"] = np.where(g_rt["Gross"]>0, (g_rt["Gross"]-g_rt["Net"])/g_rt["Gross"]*100, 0)
    g_rt = g_rt.sort_values(["Time","Net"], ascending=[True,False])

    st.subheader(f"🌍 Theo Region + {time_type}")
    show_rt = g_rt.copy()
    show_rt["Kỳ"] = week_label_from_anchor(show_rt["Time"]) if time_type=="Tuần" else pd.to_datetime(show_rt["Time"]).dt.strftime("%Y-%m-%d")
    show_rt = show_rt.drop(columns=["Time"])
    for c in ["Gross","Net","Orders","Customers"]:
        show_rt[c] = show_rt[c].apply(fmt_int)
    show_rt["CK_%"] = show_rt["CK_%"].apply(lambda v: fmt_pct(v,2))
    st.dataframe(show_rt, use_container_width=True, hide_index=True)

# =====================================================
# STORE SUMMARY
# =====================================================
if "Điểm_mua_hàng" in df_f.columns:
    st.subheader("🏪 Tổng quan theo Cửa hàng")
    g_store = (
        df_f.groupby("Điểm_mua_hàng", observed=True)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=("Số_CT","nunique"),
            Customers=("Số_điện_thoại","nunique"),
        ).reset_index()
    )
    g_store["CK_%"] = np.where(g_store["Gross"]>0, (g_store["Gross"]-g_store["Net"])/g_store["Gross"]*100, 0)
    g_store = g_store.sort_values("Net", ascending=False)

    show_s = g_store.copy()
    for c in ["Gross","Net","Orders","Customers"]:
        show_s[c] = show_s[c].apply(fmt_int)
    show_s["CK_%"] = show_s["CK_%"].apply(lambda v: fmt_pct(v,2))
    st.dataframe(show_s, use_container_width=True, hide_index=True)

# =====================================================
# PRODUCT SUMMARY (Mã_NB)
# =====================================================
st.subheader("📦 Theo Nhóm SP / Mã NB")

df_prod = df_f
col1,col2 = st.columns(2)
with col1:
    if "Nhóm_hàng" in df_prod.columns:
        nhom = st.multiselect("📦 Chọn Nhóm SP", sorted(df_prod["Nhóm_hàng"].astype(str).unique()),
                              key=GEN + "nhom_sp")
    else:
        nhom = []
with col2:
    if "Mã_NB" in df_prod.columns:
        ma = st.multiselect("🏷️ Chọn Mã NB", sorted(df_prod["Mã_NB"].astype(str).unique()),
                            key=GEN + "ma_nb")
    else:
        ma = []

if nhom and "Nhóm_hàng" in df_prod.columns:
    df_prod = df_prod[df_prod["Nhóm_hàng"].astype(str).isin([str(x) for x in nhom])]
if ma and "Mã_NB" in df_prod.columns:
    df_prod = df_prod[df_prod["Mã_NB"].astype(str).isin([str(x) for x in ma])]

if "Mã_NB" in df_prod.columns and ("Tổng_Gross" in df_prod.columns) and ("Tổng_Net" in df_prod.columns):
    qty_agg = ("Số_lượng","sum") if "Số_lượng" in df_prod.columns else ("Số_CT","nunique")
    g_p = (
        df_prod.groupby("Mã_NB", observed=True)
        .agg(
            Gross=("Tổng_Gross","sum"),
            Net=("Tổng_Net","sum"),
            Orders=qty_agg,
            Customers=("Số_điện_thoại","nunique"),
        ).reset_index()
        .sort_values("Net", ascending=False)
    )
    show_p = g_p.copy()
    for c in ["Gross","Net","Orders","Customers"]:
        show_p[c] = show_p[c].apply(fmt_int)
    st.dataframe(show_p, use_container_width=True, hide_index=True)
else:
    st.info("Thiếu cột Mã_NB / Tổng_Gross / Tổng_Net nên chưa hiển thị được bảng này.")
