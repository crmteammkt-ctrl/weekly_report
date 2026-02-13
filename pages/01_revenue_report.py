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

# =====================================================
# WEEK HELPERS (TUẦN BẮT ĐẦU THEO THỨ - RIÊNG REVENUE)
# =====================================================
WEEKDAY_MAP = {
    "Thứ 2": 0, "Thứ 3": 1, "Thứ 4": 2, "Thứ 5": 3,
    "Thứ 6": 4, "Thứ 7": 5, "Chủ nhật": 6
}

def week_anchor(dt: pd.Series, week_start: int) -> pd.Series:
    d = pd.to_datetime(dt)
    return (d - pd.to_timedelta((d.dt.weekday - week_start) % 7, unit="D")).dt.normalize()

def label_from_time(grain: str, time_col: pd.Series) -> pd.Series:
    t = pd.to_datetime(time_col)
    if grain == "Ngày":
        return t.dt.strftime("%Y-%m-%d")
    if grain == "Tuần":
        iso = t.dt.isocalendar()
        return "Tuần " + iso["week"].astype(str).str.zfill(2) + "/" + iso["year"].astype(str)
    if grain == "Tháng":
        return t.dt.to_period("M").astype(str)
    # Quý
    return t.dt.to_period("Q").astype(str)

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
# SIDEBAR FILTER (REVENUE) - KHÔNG reset khi chuyển trang (trừ khi bấm Reset)
# =====================================================
with st.sidebar:
    st.header("🎛 Bộ lọc dữ liệu")

    if st.button("🔄 Reset bộ lọc (Revenue)", width="stretch"):
        reset_by_prefix(REV)

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key=REV + "time_grain",
    )

    # Tuần bắt đầu (chỉ khi chọn Tuần)
    if time_grain == "Tuần":
        rev_week_label = st.selectbox(
            "Tuần bắt đầu từ thứ",
            list(WEEKDAY_MAP.keys()),
            key=REV + "week_start",
        )
        WEEK_START = WEEKDAY_MAP[rev_week_label]
    else:
        WEEK_START = 0

    # init mặc định 1 lần để không bị KeyError & không bị reset khi quay lại page
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

    df_b = df[df["Brand"].isin(brand_filter)] if ("Brand" in df.columns) else df
    region_filter = ms_all(
        key=REV + "region",
        label="Region",
        options=df_b["Region"] if "Region" in df_b.columns else [],
    )

    df_br = df_b[df_b["Region"].isin(region_filter)] if ("Region" in df_b.columns) else df_b
    store_filter = ms_all(
        key=REV + "store",
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
    mask &= df["LoaiCT"].isin(loaict_filter)
if "Brand" in df.columns:
    mask &= df["Brand"].isin(brand_filter)
if "Region" in df.columns:
    mask &= df["Region"].isin(region_filter)
if "Điểm_mua_hàng" in df.columns:
    mask &= df["Điểm_mua_hàng"].isin(store_filter)
if "Trạng_thái_số_điện_thoại" in df.columns:
    mask &= df["Trạng_thái_số_điện_thoại"].isin(checksdt_filter)
if "Kiểm_tra_tên" in df.columns:
    mask &= df["Kiểm_tra_tên"].isin(checkten_filter)

df_f = df.loc[mask].copy()
if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

with st.expander("📑 Xem dữ liệu đã lọc (mở/đóng)", expanded=False):
    st.dataframe(df_f, width="stretch", hide_index=True)

# =====================================================
# TIME KEY: tạo cột Time (datetime) để group/sort + Label hiển thị
# =====================================================
def add_time(df_in: pd.DataFrame, grain: str, week_start: int) -> pd.DataFrame:
    out = df_in.copy()
    if grain == "Ngày":
        out["Time"] = out["Ngày"].dt.normalize()
    elif grain == "Tuần":
        out["Time"] = week_anchor(out["Ngày"], week_start)
    elif grain == "Tháng":
        out["Time"] = out["Ngày"].dt.to_period("M").dt.to_timestamp()
    else:  # Quý
        out["Time"] = out["Ngày"].dt.to_period("Q").dt.to_timestamp()
    out["Label"] = label_from_time(grain, out["Time"])
    return out

tmp = add_time(df_f, time_grain, WEEK_START)

# =====================================================
# CACHE GROUPS (tăng tốc)
# =====================================================
@st.cache_data(show_spinner=False)
def build_summary(df_in: pd.DataFrame) -> pd.DataFrame:
    g = (
        df_in.groupby(["Time", "Label"], observed=True)
        .agg(
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_KH=("Số_điện_thoại", "nunique"),
            Số_đơn_hàng=("Số_CT", "nunique"),
        )
        .reset_index()
        .sort_values("Time")
    )
    g["Tỷ_lệ_CK (%)"] = np.where(g["Tổng_Gross"] > 0, (1 - g["Tổng_Net"] / g["Tổng_Gross"]) * 100, 0)
    g["Prev_Tổng_Net"] = g["Tổng_Net"].shift(1)
    g["%_So_sánh_Tổng_Net"] = np.where(
        g["Prev_Tổng_Net"] > 0,
        (g["Tổng_Net"] - g["Prev_Tổng_Net"]) / g["Prev_Tổng_Net"] * 100,
        np.nan
    )
    return g

@st.cache_data(show_spinner=False)
def build_region(df_in: pd.DataFrame) -> pd.DataFrame:
    if "Region" not in df_in.columns:
        return pd.DataFrame()

    reg = (
        df_in.groupby(["Region", "Time", "Label"], observed=True)
        .agg(
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_KH=("Số_điện_thoại", "nunique"),
            Số_đơn_hàng=("Số_CT", "nunique"),
        )
        .reset_index()
        .sort_values(["Region", "Time"])
    )
    reg["Tỷ_lệ_CK (%)"] = np.where(reg["Tổng_Gross"] > 0, (1 - reg["Tổng_Net"] / reg["Tổng_Gross"]) * 100, 0)

    # Prev + Change% theo từng Region
    reg["Prev_Tổng_Net"] = reg.groupby("Region")["Tổng_Net"].shift(1)
    reg["Change%"] = np.where(
        reg["Prev_Tổng_Net"] > 0,
        (reg["Tổng_Net"] - reg["Prev_Tổng_Net"]) / reg["Prev_Tổng_Net"] * 100,
        np.nan
    )
    return reg

@st.cache_data(show_spinner=False)
def build_store(df_in: pd.DataFrame) -> pd.DataFrame:
    if "Điểm_mua_hàng" not in df_in.columns:
        return pd.DataFrame()

    store = (
        df_in.groupby(["Điểm_mua_hàng", "Time", "Label"], observed=True)
        .agg(
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_đơn_hàng=("Số_CT", "nunique"),
        )
        .reset_index()
        .sort_values(["Điểm_mua_hàng", "Time"])
    )
    store["Tỷ_lệ_CK (%)"] = np.where(store["Tổng_Gross"] > 0, (1 - store["Tổng_Net"] / store["Tổng_Gross"]) * 100, 0)

    # Prev + Change% theo từng store
    store["Prev_Tổng_Net"] = store.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
    store["Change%"] = np.where(
        store["Prev_Tổng_Net"] > 0,
        (store["Tổng_Net"] - store["Prev_Tổng_Net"]) / store["Prev_Tổng_Net"] * 100,
        np.nan
    )
    return store

summary = build_summary(tmp)

# =====================================================
# SUMMARY DISPLAY + CHART
# =====================================================
st.subheader("📊 Tổng hợp doanh thu")

summary_show = summary.copy()
for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Prev_Tổng_Net"]:
    summary_show[c] = summary_show[c].apply(fmt_int)
for c in ["Tỷ_lệ_CK (%)", "%_So_sánh_Tổng_Net"]:
    summary_show[c] = summary_show[c].apply(lambda v: fmt_pct(v, 2, with_sign=(c == "%_So_sánh_Tổng_Net")))

summary_cols = ["Label", "Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "%_So_sánh_Tổng_Net"]
summary_show = summary_show[summary_cols].rename(columns={"Label": "Kỳ"})
st.dataframe(summary_show, width="stretch", hide_index=True)

fig = px.line(
    summary,
    x="Time",
    y=["Tổng_Gross", "Tổng_Net"],
    markers=True,
    title=f"Doanh thu theo {time_grain}",
)
st.plotly_chart(fig, use_container_width=True)

# =====================================================
# REGION (chọn kỳ) + Prev_Tổng_Net + Change%
# =====================================================
st.subheader("🌍 Theo Region")

reg = build_region(tmp)
if reg.empty:
    st.info("Thiếu cột Region hoặc không có dữ liệu.")
else:
    periods = summary[["Time", "Label"]].drop_duplicates().sort_values("Time")
    period_labels = periods["Label"].tolist()

    # ✅ key KHÁC với store_period để không bị DuplicateElementKey
    sel_period = st.selectbox("Chọn kỳ", period_labels, index=len(period_labels) - 1, key=REV + "region_period")

    reg_view = reg[reg["Label"] == sel_period].sort_values("Tổng_Net", ascending=False).copy()

    reg_show = reg_view[
        ["Label", "Region", "Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "Change%"]
    ].rename(columns={"Label": "Kỳ"})

    for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Prev_Tổng_Net"]:
        reg_show[c] = reg_show[c].apply(fmt_int)
    reg_show["Tỷ_lệ_CK (%)"] = reg_show["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
    reg_show["Change%"] = reg_show["Change%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))

    st.dataframe(reg_show, width="stretch", hide_index=True)

# =====================================================
# TOP / BOTTOM 10 STORE (chọn kỳ) + GIỮ Prev_Tổng_Net + Change% + THÊM Số_đơn_hàng
# =====================================================
st.subheader("🏪 Top / Bottom 10")

store = build_store(tmp)
if store.empty:
    st.info("Thiếu cột Điểm_mua_hàng hoặc không có dữ liệu.")
else:
    periods = summary[["Time", "Label"]].drop_duplicates().sort_values("Time")
    period_labels = periods["Label"].tolist()

    # ✅ key RIÊNG, không trùng với region_period
    sel_period2 = st.selectbox("Chọn kỳ", period_labels, index=len(period_labels) - 1, key=REV + "store_period")

    s = store[store["Label"] == sel_period2].copy()

    top10 = s.sort_values("Tổng_Net", ascending=False).head(10).copy()
    bot10 = s.sort_values("Tổng_Net", ascending=True).head(10).copy()

    def show_store_table(dfin: pd.DataFrame) -> pd.DataFrame:
        out = dfin[
            ["Label", "Điểm_mua_hàng", "Tổng_Gross", "Tổng_Net", "Số_đơn_hàng", "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "Change%"]
        ].rename(columns={"Label": "Kỳ"}).copy()

        for c in ["Tổng_Gross", "Tổng_Net", "Số_đơn_hàng", "Prev_Tổng_Net"]:
            out[c] = out[c].apply(fmt_int)
        out["Tỷ_lệ_CK (%)"] = out["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
        out["Change%"] = out["Change%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))
        return out

    colA, colB = st.columns(2)
    with colA:
        st.markdown("### 🏆 Top 10")
        st.dataframe(show_store_table(top10), width="stretch", hide_index=True)
    with colB:
        st.markdown("### 📉 Bottom 10")
        st.dataframe(show_store_table(bot10), width="stretch", hide_index=True)
