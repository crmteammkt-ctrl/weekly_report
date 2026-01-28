# pages/01_revenue_report.py
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from load_data import get_active_data

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

def show_df(df_show: pd.DataFrame, title=None):
    if title:
        st.subheader(title)
    st.dataframe(df_show, use_container_width=True, hide_index=True)

# =====================================================
# WEEK HELPERS (ĐỒNG BỘ VỚI GENERAL)
# =====================================================
WEEKDAY_MAP = {
    "Thứ 2": 0, "Thứ 3": 1, "Thứ 4": 2, "Thứ 5": 3,
    "Thứ 6": 4, "Thứ 7": 5, "Chủ nhật": 6
}
week_label = st.session_state.get("gen_week_start", "Thứ 2")
WEEK_START = WEEKDAY_MAP.get(week_label, 0)

def week_anchor(dt: pd.Series, week_start: int) -> pd.Series:
    d = pd.to_datetime(dt)
    return (d - pd.to_timedelta((d.dt.weekday - week_start) % 7, unit="D")).dt.normalize()

# =====================================================
# FILTER HELPERS
# =====================================================
REV_PREFIX = "rev_"

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
        st.session_state[key] = [all_label] if default_all else opts[:1]

    cur = [x for x in st.session_state.get(key, []) if x in ui_opts]
    if not cur:
        cur = [all_label]
        st.session_state[key] = cur

    selected = st.multiselect(label, ui_opts, key=key)
    if (not selected) or (all_label in selected):
        return opts
    return [x for x in selected if x in opts]

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="📈 Báo cáo Doanh thu", layout="wide")
st.title("📈 Báo cáo Doanh thu")

# =====================================================
# LOAD DATA
# =====================================================
df = get_active_data()
st.sidebar.caption("🔎 Đang dùng nguồn: **{}**".format(st.session_state.get("active_source", "default")))

df = ensure_datetime(df)
df = fix_numeric(df)

if df.empty:
    st.warning("⚠ Không có dữ liệu.")
    st.stop()

# =====================================================
# SIDEBAR FILTER
# =====================================================
with st.sidebar:
    st.header("🎛 Bộ lọc dữ liệu")

    if st.button("🔄 Reset bộ lọc (Revenue)", use_container_width=True):
        reset_by_prefix(REV_PREFIX)

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key=REV_PREFIX + "time_grain",
    )

    start_date = st.date_input(
        "Từ ngày",
        df["Ngày"].min().date(),
        key=REV_PREFIX + "start_date",
    )
    end_date = st.date_input(
        "Đến ngày",
        df["Ngày"].max().date(),
        key=REV_PREFIX + "end_date",
    )

    loaict_filter = ms_all(
        key=REV_PREFIX + "loaict",
        label="LoaiCT",
        options=df["LoaiCT"] if "LoaiCT" in df.columns else [],
    )

    brand_filter = ms_all(
        key=REV_PREFIX + "brand",
        label="Brand",
        options=df["Brand"] if "Brand" in df.columns else [],
    )

    df_b = df[df["Brand"].isin(brand_filter)] if brand_filter else df.iloc[0:0]
    region_filter = ms_all(
        key=REV_PREFIX + "region",
        label="Region",
        options=df_b["Region"] if "Region" in df_b.columns else [],
    )

    df_br = df_b[df_b["Region"].isin(region_filter)] if region_filter else df_b.iloc[0:0]
    store_filter = ms_all(
        key=REV_PREFIX + "store",
        label="Điểm mua hàng",
        options=df_br["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df_br.columns else [],
    )

# =====================================================
# APPLY FILTER
# =====================================================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))
if "LoaiCT" in df.columns:
    mask &= df["LoaiCT"].isin(loaict_filter)
if "Brand" in df.columns:
    mask &= df["Brand"].isin(brand_filter)
if "Region" in df.columns:
    mask &= df["Region"].isin(region_filter)
if "Điểm_mua_hàng" in df.columns:
    mask &= df["Điểm_mua_hàng"].isin(store_filter)

df_filtered = df.loc[mask].copy()
if df_filtered.empty:
    st.warning("⚠ Không có dữ liệu sau khi lọc.")
    st.stop()

# =====================================================
# TIME KEY (CUSTOM WEEK)
# =====================================================
def add_time_key(df_in: pd.DataFrame, grain: str):
    d = df_in.copy()

    if grain == "Ngày":
        d["Key"] = d["Ngày"].dt.date
        d["Year"] = d["Ngày"].dt.year
        group_cols = ["Key"]

    elif grain == "Tuần":
        d["_WeekAnchor"] = week_anchor(d["Ngày"], WEEK_START)
        iso = d["_WeekAnchor"].dt.isocalendar()
        d["Year"] = iso["year"].astype(int)
        d["Key"] = iso["week"].astype(int)
        group_cols = ["Year", "Key"]

    elif grain == "Tháng":
        d["Year"] = d["Ngày"].dt.year
        d["Key"] = d["Ngày"].dt.month.astype(int)
        group_cols = ["Year", "Key"]

    else:  # Quý
        d["Year"] = d["Ngày"].dt.year
        d["Key"] = d["Ngày"].dt.quarter.astype(int)
        group_cols = ["Year", "Key"]

    return d, group_cols

# =====================================================
# SUMMARY
# =====================================================
def summarize_revenue(df_in, grain):
    df_t, group_cols = add_time_key(df_in, grain)

    g = (
        df_t.groupby(group_cols)
        .agg(
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_KH=("Số_điện_thoại", "nunique"),
            Số_đơn_hàng=("Số_CT", "nunique"),
        )
        .reset_index()
        .sort_values(group_cols)
    )

    g["Tỷ_lệ_CK (%)"] = np.where(g["Tổng_Gross"] > 0, (1 - g["Tổng_Net"] / g["Tổng_Gross"]) * 100, 0)

    for col in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng"]:
        g[f"Prev_{col}"] = g[col].shift(1)
        g[f"%_So_sánh_{col}"] = np.where(
            g[f"Prev_{col}"] > 0,
            (g[col] - g[f"Prev_{col}"]) / g[f"Prev_{col}"] * 100,
            np.nan,
        )

    return g

df_summary = summarize_revenue(df_filtered, time_grain)

# =====================================================
# DISPLAY SUMMARY
# =====================================================
df_show = df_summary.copy()

if time_grain == "Ngày":
    df_show["Kỳ"] = pd.to_datetime(df_show["Key"]).dt.strftime("%Y-%m-%d")
elif time_grain == "Tuần":
    df_show["Kỳ"] = df_show.apply(lambda r: f"Tuần {int(r['Key']):02d}/{int(r['Year'])}", axis=1)
elif time_grain == "Tháng":
    df_show["Kỳ"] = df_show.apply(lambda r: f"{int(r['Year'])}-{int(r['Key']):02d}", axis=1)
else:
    df_show["Kỳ"] = df_show.apply(lambda r: f"Q{int(r['Key'])} {int(r['Year'])}", axis=1)

for c in df_show.columns:
    if c.startswith("Tổng") or c.startswith("Prev") or c.startswith("Số_"):
        df_show[c] = df_show[c].apply(fmt_int)
    if c.startswith("%") or c.endswith("(%)"):
        df_show[c] = df_show[c].apply(lambda v: fmt_pct(v, 2, with_sign=True))

show_cols = ["Kỳ", "Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Tỷ_lệ_CK (%)", "%_So_sánh_Tổng_Net"]
show_cols = [c for c in show_cols if c in df_show.columns]
show_df(df_show[show_cols])

# =====================================================
# CHART
# =====================================================
fig = px.line(
    df_summary,
    x="Key",
    y=["Tổng_Gross", "Tổng_Net"],
    markers=True,
    title=f"Doanh thu theo {time_grain}",
)
st.plotly_chart(fig, use_container_width=True)
