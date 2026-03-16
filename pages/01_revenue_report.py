# pages/01_revenue_report.py
import hashlib
import json

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

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

def label_from_time(time_s: pd.Series, grain: str) -> pd.Series:
    """Sinh label hiển thị ổn định từ cột Time (datetime)."""
    t = pd.to_datetime(time_s)
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

def _hash_filters(d: dict) -> str:
    s = json.dumps(d, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.md5(s).hexdigest()

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

    if st.button("🔄 Reset bộ lọc (Revenue)", use_container_width=True):
        reset_by_prefix(REV)

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key=REV + "time_grain",
    )

    # Tuần bắt đầu theo thứ (riêng Revenue)
    if time_grain == "Tuần":
        rev_week_label = st.selectbox(
            "Tuần bắt đầu từ thứ",
            list(WEEKDAY_MAP.keys()),
            key=REV + "week_start",
        )
        REV_WEEK_START = WEEKDAY_MAP[rev_week_label]
    else:
        REV_WEEK_START = 0

    # init ngày mặc định 1 lần (tránh KeyError)
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

    # cascade Region theo Brand
    df_b = df[df["Brand"].isin(brand_filter)] if ("Brand" in df.columns) else df
    region_filter = ms_all(
        key=REV + "region",
        label="Region",
        options=df_b["Region"] if "Region" in df_b.columns else [],
    )

    # cascade Store theo Brand + Region
    df_br = df_b[df_b["Region"].isin(region_filter)] if ("Region" in df_b.columns) else df_b
    store_filter = ms_all(
        key=REV + "store",
        label="Điểm mua hàng",
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

tmp = df.loc[mask].copy()
if tmp.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# ADD Time (datetime) + Label
# =====================================================
if time_grain == "Ngày":
    tmp["Time"] = tmp["Ngày"].dt.normalize()
elif time_grain == "Tuần":
    tmp["Time"] = week_anchor(tmp["Ngày"], REV_WEEK_START)
elif time_grain == "Tháng":
    tmp["Time"] = tmp["Ngày"].dt.to_period("M").dt.to_timestamp()
else:  # Quý
    tmp["Time"] = tmp["Ngày"].dt.to_period("Q").dt.to_timestamp()

tmp["Label"] = label_from_time(tmp["Time"], time_grain)

# cache key theo filter
filter_signature = _hash_filters({
    "time_grain": time_grain,
    "week_start": REV_WEEK_START,
    "start_date": str(start_date),
    "end_date": str(end_date),
    "loaict": loaict_filter,
    "brand": brand_filter,
    "region": region_filter,
    "store": store_filter,
    "checksdt": checksdt_filter,
    "checkten": checkten_filter,
})

# =====================================================
# CACHE: SUMMARY / REGION / STORE (TOP-BOTTOM)
# =====================================================
@st.cache_data(show_spinner=False)
def build_tables(tmp_df: pd.DataFrame, _sig: str):
    # --- SUMMARY ---
    summary = (
        tmp_df.groupby(["Time"], observed=True)
        .agg(
            Label=("Label", "first"),
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_KH=("Số_điện_thoại", "nunique"),
            Số_đơn_hàng=("Số_CT", "nunique"),
        )
        .reset_index()
        .sort_values("Time")
    )

    summary["Tỷ_lệ_CK (%)"] = np.where(
        summary["Tổng_Gross"] != 0,
        (1 - summary["Tổng_Net"] / summary["Tổng_Gross"]) * 100,
        0,
    )

    # Prev + % compare (theo thời gian)
    summary["Prev_Tổng_Net"] = summary["Tổng_Net"].shift(1)
    summary["%_So_sánh_Tổng_Net"] = np.where(
        summary["Prev_Tổng_Net"] > 0,
        (summary["Tổng_Net"] - summary["Prev_Tổng_Net"]) / summary["Prev_Tổng_Net"] * 100,
        np.nan,
    )

    # --- REGION ---
    if "Region" in tmp_df.columns:
        reg = (
            tmp_df.groupby(["Region", "Time"], observed=True)
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

        reg = reg.sort_values(["Region", "Time"])

        reg["Prev_Tổng_Net"] = reg.groupby("Region")["Tổng_Net"].shift(1)
        reg["Prev_Tổng_Gross"] = reg.groupby("Region")["Tổng_Gross"].shift(1)
        reg["Prev_Số_đơn_hàng"] = reg.groupby("Region")["Số_đơn_hàng"].shift(1)

        reg["Change Net%"] = np.where(
            reg["Prev_Tổng_Net"] > 0,
            (reg["Tổng_Net"] - reg["Prev_Tổng_Net"]) / reg["Prev_Tổng_Net"] * 100,
            np.nan,
        )

        reg["Change Gross%"] = np.where(
            reg["Prev_Tổng_Gross"] > 0,
            (reg["Tổng_Gross"] - reg["Prev_Tổng_Gross"]) / reg["Prev_Tổng_Gross"] * 100,
            np.nan,
        )

        reg["Change ĐH%"] = np.where(
            reg["Prev_Số_đơn_hàng"] > 0,
            (reg["Số_đơn_hàng"] - reg["Prev_Số_đơn_hàng"]) / reg["Prev_Số_đơn_hàng"] * 100,
            np.nan,
        )

        reg["AOV"] = np.where(
            reg["Số_đơn_hàng"] > 0,
            reg["Tổng_Net"] / reg["Số_đơn_hàng"],
            np.nan,
        )
    else:
        reg = pd.DataFrame()

    # --- STORE ---
    if "Điểm_mua_hàng" in tmp_df.columns:
        store = (
            tmp_df.groupby(["Điểm_mua_hàng", "Time"], observed=True)
            .agg(
                Label=("Label", "first"),
                Tổng_Gross=("Tổng_Gross", "sum"),
                Tổng_Net=("Tổng_Net", "sum"),
                Số_đơn_hàng=("Số_CT", "nunique"),
            )
            .reset_index()
        )
        store["Tỷ_lệ_CK (%)"] = np.where(
            store["Tổng_Gross"] != 0,
            (1 - store["Tổng_Net"] / store["Tổng_Gross"]) * 100,
            0
        )
        store = store.sort_values(["Điểm_mua_hàng", "Time"])
        store["Prev_Tổng_Net"] = store.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
        store["Change%"] = np.where(
            store["Prev_Tổng_Net"] > 0,
            (store["Tổng_Net"] - store["Prev_Tổng_Net"]) / store["Prev_Tổng_Net"] * 100,
            np.nan,
        )
    else:
        store = pd.DataFrame()

    return summary, reg, store

summary, reg, store = build_tables(tmp, filter_signature)

# =====================================================
# SUMMARY DISPLAY + CHART
# =====================================================
st.subheader("📊 Tổng hợp doanh thu")

summary_show = summary.copy()
for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Prev_Tổng_Net"]:
    if c in summary_show.columns:
        summary_show[c] = summary_show[c].apply(fmt_int)
for c in ["Tỷ_lệ_CK (%)", "%_So_sánh_Tổng_Net"]:
    if c in summary_show.columns:
        summary_show[c] = summary_show[c].apply(lambda v: fmt_pct(v, 2, with_sign=(c == "%_So_sánh_Tổng_Net")))

show_df(
    summary_show[["Label", "Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "%_So_sánh_Tổng_Net"]]
    .rename(columns={"Label": "Kỳ"}),
    title=None
)

fig = px.line(
    summary,
    x="Time",
    y=["Tổng_Gross", "Tổng_Net"],
    markers=True,
    title=f"Doanh thu theo {time_grain}",
)
st.plotly_chart(fig, use_container_width=True)

# =====================================================
# REGION (chọn kỳ)
# =====================================================
st.subheader("🌍 Theo Region")

if reg.empty:
    st.info("Thiếu cột Region hoặc không có dữ liệu.")
else:
    periods = summary["Label"].tolist()
    sel_period = st.selectbox("Chọn kỳ", periods, index=len(periods) - 1, key=REV + "region_period")

    reg_view = reg[reg["Label"] == sel_period].sort_values("Tổng_Net", ascending=False).copy()

    reg_show = reg_view[
        [
            "Label",
            "Region",
            "Tổng_Gross",
            "Tổng_Net",
            "Số_đơn_hàng",
            "AOV",
            "Tỷ_lệ_CK (%)",
            "Change Gross%",
            "Change Net%",
            "Change ĐH%",
        ]
    ].rename(columns={"Label": "Kỳ"})

    for c in ["Tổng_Gross", "Tổng_Net", "Số_đơn_hàng", "AOV"]:
        reg_show[c] = reg_show[c].apply(fmt_int)

    reg_show["Tỷ_lệ_CK (%)"] = reg_show["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
    reg_show["Change Gross%"] = reg_show["Change Gross%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))
    reg_show["Change Net%"] = reg_show["Change Net%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))
    reg_show["Change ĐH%"] = reg_show["Change ĐH%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))

    st.dataframe(reg_show, use_container_width=True, hide_index=True)

# =====================================================
# TOP / BOTTOM 10 STORE (chọn kỳ) + lọc Region nhỏ
# =====================================================
st.subheader("🏪 Top / Bottom 10")

if store.empty:
    st.info("Thiếu cột Điểm_mua_hàng hoặc không có dữ liệu.")
else:
    periods2 = summary["Label"].tolist()
    sel_period2 = st.selectbox(
        "Chọn kỳ (Top/Bottom)",
        periods2,
        index=len(periods2) - 1,
        key=REV + "store_period",
    )

    s_view = store[store["Label"] == sel_period2].copy()

    if "Region" in tmp.columns and "Điểm_mua_hàng" in tmp.columns:
        store_region = (
            tmp.loc[tmp["Label"] == sel_period2, ["Điểm_mua_hàng", "Region"]]
            .dropna()
            .drop_duplicates()
        )

        if not store_region.empty:
            mode_map = (
                store_region.groupby("Điểm_mua_hàng")["Region"]
                .agg(lambda x: x.value_counts().index[0])
                .reset_index()
            )
            s_view = s_view.merge(mode_map, on="Điểm_mua_hàng", how="left")
        else:
            s_view["Region"] = np.nan

        region_opts = sorted([r for r in s_view["Region"].dropna().astype(str).unique().tolist()])
        region_ui = ["All"] + region_opts

        if REV + "tb_region" not in st.session_state:
            st.session_state[REV + "tb_region"] = "All"

        sel_r = st.selectbox(
            "Lọc Region (Top/Bottom)",
            region_ui,
            index=region_ui.index(st.session_state[REV + "tb_region"])
            if st.session_state[REV + "tb_region"] in region_ui else 0,
            key=REV + "tb_region",
        )

        if sel_r != "All":
            s_view = s_view[s_view["Region"].astype(str) == sel_r].copy()
    else:
        sel_r = "All"

    if s_view.empty:
        st.info("Không có dữ liệu Top/Bottom theo lựa chọn hiện tại.")
        st.stop()

    top10 = s_view.sort_values("Tổng_Net", ascending=False).head(10).copy()
    bottom10 = s_view.sort_values("Tổng_Net", ascending=True).head(10).copy()

    def _fmt_store(df_in: pd.DataFrame) -> pd.DataFrame:
        cols = ["Label", "Điểm_mua_hàng", "Tổng_Gross", "Tổng_Net", "Số_đơn_hàng",
                "Tỷ_lệ_CK (%)", "Prev_Tổng_Net", "Change%"]
        if "Region" in df_in.columns:
            cols.insert(2, "Region")

        out = df_in[cols].rename(columns={"Label": "Kỳ"}).copy()

        for c in ["Tổng_Gross", "Tổng_Net", "Số_đơn_hàng", "Prev_Tổng_Net"]:
            if c in out.columns:
                out[c] = out[c].apply(fmt_int)

        if "Tỷ_lệ_CK (%)" in out.columns:
            out["Tỷ_lệ_CK (%)"] = out["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
        if "Change%" in out.columns:
            out["Change%"] = out["Change%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))

        return out

    colA, colB = st.columns(2)
    with colA:
        st.markdown("### 🏆 Top 10 Điểm mua hàng")
        st.dataframe(_fmt_store(top10), use_container_width=True, hide_index=True)
    with colB:
        st.markdown("### 📉 Bottom 10 Điểm mua hàng")
        st.dataframe(_fmt_store(bottom10), use_container_width=True, hide_index=True)