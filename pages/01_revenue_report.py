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
# WEEK HELPERS (REVENUE - riêng trang)
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
REV = "rev_"

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
# CONFIG
# =====================================================
st.set_page_config(page_title="📈 Báo cáo Doanh thu", layout="wide")
st.title("📈 Báo cáo Doanh thu")

# =====================================================
# LOAD
# =====================================================
df = get_active_data()
st.sidebar.caption("🔎 Đang dùng nguồn: **{}**".format(st.session_state.get("active_source", "default")))

df = ensure_datetime(df)
df = fix_numeric(df)

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích.")
    st.stop()

# =====================================================
# SIDEBAR FILTER (REVENUE)
# =====================================================
with st.sidebar:
    st.header("🎛 Bộ lọc dữ liệu")

    if st.button("🔄 Reset bộ lọc (Revenue)", use_container_width=True, key=REV + "btn_reset"):
        reset_by_prefix(REV)

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key=REV + "time_grain",
    )

    # Tuần riêng Revenue
    if time_grain == "Tuần":
        rev_week_label = st.selectbox(
            "Tuần bắt đầu",
            list(WEEKDAY_MAP.keys()),
            key=REV + "week_start",
        )
        REV_WEEK_START = WEEKDAY_MAP[rev_week_label]
    else:
        REV_WEEK_START = 0

    # Init date 1 lần để không KeyError
    if REV + "start_date" not in st.session_state:
        st.session_state[REV + "start_date"] = df["Ngày"].min().date()
    if REV + "end_date" not in st.session_state:
        st.session_state[REV + "end_date"] = df["Ngày"].max().date()

    start_date = st.date_input("Từ ngày", key=REV + "start_date")
    end_date = st.date_input("Đến ngày", key=REV + "end_date")

    loaict_filter = ms_all(
        key=REV + "loaict",
        label="LoaiCT",
        options=df["LoaiCT"] if "LoaiCT" in df.columns else [],
    )

    brand_filter = ms_all(
        key=REV + "brand",
        label="Brand",
        options=df["Brand"] if "Brand" in df.columns else [],
    )

    df_b = df[df["Brand"].isin(brand_filter)] if (brand_filter and "Brand" in df.columns) else df.iloc[0:0]
    region_filter = ms_all(
        key=REV + "region",
        label="Region",
        options=df_b["Region"] if "Region" in df_b.columns else [],
    )

    df_br = df_b[df_b["Region"].isin(region_filter)] if (region_filter and "Region" in df_b.columns) else df_b.iloc[0:0]
    store_filter = ms_all(
        key=REV + "store_filter",  # ✅ khác key với selectbox kỳ
        label="Cửa hàng",
        options=df_br["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df_br.columns else [],
    )

    checksdt_filter = ms_all(
        key=REV + "checksdt",
        label="Trạng_thái_số_điện_thoại",
        options=df["Trạng_thái_số_điện_thoại"] if "Trạng_thái_số_điện_thoại" in df.columns else [],
    )

    checkten_filter = ms_all(
        key=REV + "checkten",
        label="Kiểm_tra_tên",
        options=df["Kiểm_tra_tên"] if "Kiểm_tra_tên" in df.columns else [],
    )

# =====================================================
# APPLY FILTER
# =====================================================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))

if "LoaiCT" in df.columns:
    mask &= df["LoaiCT"].isin(loaict_filter if loaict_filter else [])
if "Brand" in df.columns:
    mask &= df["Brand"].isin(brand_filter if brand_filter else [])
if "Region" in df.columns:
    mask &= df["Region"].isin(region_filter if region_filter else [])
if "Điểm_mua_hàng" in df.columns:
    mask &= df["Điểm_mua_hàng"].isin(store_filter if store_filter else [])
if "Trạng_thái_số_điện_thoại" in df.columns:
    mask &= df["Trạng_thái_số_điện_thoại"].isin(checksdt_filter if checksdt_filter else [])
if "Kiểm_tra_tên" in df.columns:
    mask &= df["Kiểm_tra_tên"].isin(checkten_filter if checkten_filter else [])

tmp = df.loc[mask].copy()

if tmp.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# TIME KEY + LABEL (1 lần, reuse)
# =====================================================
def add_time_cols(df_in: pd.DataFrame, grain: str, week_start: int) -> pd.DataFrame:
    out = df_in.copy()

    if grain == "Ngày":
        out["Time"] = out["Ngày"].dt.normalize()
        out["Label"] = out["Time"].dt.strftime("%Y-%m-%d")
        out["Year"] = out["Ngày"].dt.year
        out["Key"] = out["Ngày"].dt.date  # dùng cho plot

    elif grain == "Tuần":
        anch = week_anchor(out["Ngày"], week_start)
        out["Time"] = anch
        iso = anch.dt.isocalendar()
        out["Year"] = iso["year"].astype(int)
        out["Key"] = iso["week"].astype(int)
        out["Label"] = week_label_from_anchor(anch)

    elif grain == "Tháng":
        out["Time"] = out["Ngày"].dt.to_period("M").dt.to_timestamp()
        out["Year"] = out["Ngày"].dt.year
        out["Key"] = out["Ngày"].dt.month.astype(int)
        out["Label"] = out["Year"].astype(str) + "-" + out["Key"].astype(str).str.zfill(2)

    else:  # Quý
        out["Time"] = out["Ngày"].dt.to_period("Q").dt.to_timestamp()
        out["Year"] = out["Ngày"].dt.year
        out["Key"] = out["Ngày"].dt.quarter.astype(int)
        out["Label"] = "Q" + out["Key"].astype(str) + " " + out["Year"].astype(str)

    return out

tmp = add_time_cols(tmp, time_grain, REV_WEEK_START)

# group cols theo grain
if time_grain == "Ngày":
    gcols = ["Time"]
else:
    gcols = ["Year", "Key"]

# =====================================================
# SUMMARY
# =====================================================
summary = (
    tmp.groupby(gcols, observed=True)
    .agg(
        Label=("Label", "first"),
        Tổng_Gross=("Tổng_Gross", "sum"),
        Tổng_Net=("Tổng_Net", "sum"),
        Số_KH=("Số_điện_thoại", "nunique"),
        Số_đơn_hàng=("Số_CT", "nunique"),
    )
    .reset_index()
    .sort_values(gcols)
)

summary["Tỷ_lệ_CK (%)"] = np.where(
    summary["Tổng_Gross"] != 0,
    (1 - summary["Tổng_Net"] / summary["Tổng_Gross"]) * 100,
    0
)

# Prev & % so sánh (giữ đúng kiểu bạn đang dùng)
for col in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng"]:
    prev_col = f"Prev_{col}"
    pct_col = f"%_So_sánh_{col}"
    summary[prev_col] = summary[col].shift(1)
    summary[pct_col] = ((summary[col] - summary[prev_col]) / summary[prev_col] * 100).where(
        summary[prev_col].notna() & (summary[prev_col] != 0)
    )

# =====================================================
# VIEW RAW
# =====================================================
with st.expander("📑 Xem dữ liệu đã lọc (mở/đóng)", expanded=False):
    st.dataframe(tmp, use_container_width=True)

# =====================================================
# SUMMARY DISPLAY + CHART
# =====================================================
st.subheader("📊 Tổng hợp doanh thu")

summary_show = summary.copy()
summary_show = summary_show.rename(columns={"Label": "Kỳ"})

for c in [
    "Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng",
    "Prev_Tổng_Gross", "Prev_Tổng_Net", "Prev_Số_KH", "Prev_Số_đơn_hàng"
]:
    if c in summary_show.columns:
        summary_show[c] = summary_show[c].apply(fmt_int)

for c in [
    "Tỷ_lệ_CK (%)",
    "%_So_sánh_Tổng_Gross", "%_So_sánh_Tổng_Net", "%_So_sánh_Số_KH", "%_So_sánh_Số_đơn_hàng"
]:
    if c in summary_show.columns:
        summary_show[c] = summary_show[c].apply(lambda v: fmt_pct(v, 2, with_sign=c.startswith("%_So_sánh")))

show_cols = ["Kỳ"]
for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "%_So_sánh_Tổng_Net"]:
    if c in summary_show.columns:
        show_cols.append(c)

show_df(summary_show[show_cols], title=None)

# Plotly: dùng trục thời gian ổn định
if time_grain == "Ngày":
    chart_x = summary["Time"]
else:
    # tạo x = Year-Key để line nối đúng
    chart_x = summary["Year"].astype(str) + "-" + summary["Key"].astype(str)

fig = px.line(
    summary.assign(_x=chart_x),
    x="_x",
    y=["Tổng_Gross", "Tổng_Net"],
    markers=True,
    title=f"Doanh thu theo {time_grain}",
)
st.plotly_chart(fig, use_container_width=True)

# =====================================================
# REGION (chọn kỳ) + Prev_Tổng_Net & Change%
# =====================================================
st.subheader("🌍 Theo Region")

if "Region" not in tmp.columns:
    st.info("Thiếu cột Region.")
else:
    reg = (
        tmp.groupby(["Region"] + gcols, observed=True)
        .agg(
            Label=("Label", "first"),
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_KH=("Số_điện_thoại", "nunique"),
            Số_đơn_hàng=("Số_CT", "nunique"),
        )
        .reset_index()
    )

    reg["Tỷ_lệ_CK (%)"] = np.where(
        reg["Tổng_Gross"] != 0,
        (1 - reg["Tổng_Net"] / reg["Tổng_Gross"]) * 100,
        0
    )

    reg = reg.sort_values(["Region"] + gcols)
    reg["Prev_Tổng_Net"] = reg.groupby("Region")["Tổng_Net"].shift(1)
    reg["Change%"] = np.where(
        reg["Prev_Tổng_Net"] > 0,
        (reg["Tổng_Net"] - reg["Prev_Tổng_Net"]) / reg["Prev_Tổng_Net"] * 100,
        np.nan
    )

    st.markdown("### 🔍 Chọn kỳ")
    periods = summary["Label"].tolist()
    sel = st.selectbox("Chọn kỳ", periods, index=len(periods) - 1, key=REV + "region_period")

    reg_view = reg[reg["Label"] == sel].sort_values("Tổng_Net", ascending=False).copy()

    reg_show = reg_view[
        ["Label", "Region", "Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng",
         "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "Change%"]
    ].rename(columns={"Label": "Kỳ"})

    for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Prev_Tổng_Net"]:
        reg_show[c] = reg_show[c].apply(fmt_int)

    reg_show["Tỷ_lệ_CK (%)"] = reg_show["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
    reg_show["Change%"] = reg_show["Change%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))

    st.dataframe(reg_show, use_container_width=True, hide_index=True)

# =====================================================
# TOP/BOTTOM 10 STORE (chọn kỳ) + thêm Số_đơn_hàng
# =====================================================
st.subheader("🏪 Top / Bottom 10")

if "Điểm_mua_hàng" not in tmp.columns:
    st.info("Thiếu cột Điểm_mua_hàng.")
else:
    store = (
        tmp.groupby(["Điểm_mua_hàng"] + gcols, observed=True)
        .agg(
            Label=("Label", "first"),
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_đơn_hàng=("Số_CT", "nunique"),   # ✅ thêm cột số đơn hàng
        )
        .reset_index()
    )

    store["Tỷ_lệ_CK (%)"] = np.where(
        store["Tổng_Gross"] != 0,
        (1 - store["Tổng_Net"] / store["Tổng_Gross"]) * 100,
        0
    )

    store = store.sort_values(["Điểm_mua_hàng"] + gcols)
    store["Prev_Tổng_Net"] = store.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
    store["Change%"] = np.where(
        store["Prev_Tổng_Net"] > 0,
        (store["Tổng_Net"] - store["Prev_Tổng_Net"]) / store["Prev_Tổng_Net"] * 100,
        np.nan
    )

    st.markdown("### 🔍 Chọn kỳ")
    periods2 = summary["Label"].tolist()
    sel2 = st.selectbox("Chọn kỳ (Top/Bottom)", periods2, index=len(periods2) - 1, key=REV + "store_period")

    cur = store[store["Label"] == sel2].copy()

    top10 = cur.sort_values("Tổng_Net", ascending=False).head(10)
    bottom10 = cur.sort_values("Tổng_Net", ascending=True).head(10)

    def format_store(dfin: pd.DataFrame) -> pd.DataFrame:
        if dfin.empty:
            return dfin
        out = dfin[
            ["Label", "Điểm_mua_hàng", "Tổng_Gross", "Tổng_Net", "Số_đơn_hàng",
             "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "Change%"]
        ].rename(columns={"Label": "Kỳ"}).copy()

        for c in ["Tổng_Gross", "Tổng_Net", "Số_đơn_hàng", "Prev_Tổng_Net"]:
            out[c] = out[c].apply(fmt_int)

        out["Tỷ_lệ_CK (%)"] = out["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
        out["Change%"] = out["Change%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))
        return out

    colA, colB = st.columns(2)
    with colA:
        st.markdown("### 🏆 Top 10 Điểm mua hàng")
        st.dataframe(format_store(top10), use_container_width=True, hide_index=True)
    with colB:
        st.markdown("### 📉 Bottom 10 Điểm mua hàng")
        st.dataframe(format_store(bottom10), use_container_width=True, hide_index=True)
