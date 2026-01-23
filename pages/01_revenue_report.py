# pages/01_revenue_report.py
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from load_data import get_active_data

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

def show_df(df_show: pd.DataFrame, title: str | None = None):
    if title:
        st.subheader(title)
    st.dataframe(df_show, use_container_width=True, hide_index=True)

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="📈 Báo cáo Doanh thu", layout="wide")
st.title("📈 Báo cáo Doanh thu")

# =====================================================
# LOAD
# =====================================================
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
# SIDEBAR FILTER (Brand → Region → Store)
# =====================================================
def with_all_option(values: list[str], label_all="All"):
    return [label_all] + values
def normalize_filter(selected, all_values, label_all="All"):
    if (not selected) or (label_all in selected):
        return all_values
    return selected

with st.sidebar:
    st.header("🎛 Bộ lọc dữ liệu")

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key="rev_time_grain",
    )

    start_date = st.date_input(
        "Từ ngày",
        df["Ngày"].min().date(),
        key="rev_start_date",
    )
    end_date = st.date_input(
        "Đến ngày",
        df["Ngày"].max().date(),
        key="rev_end_date",
    )

    # Loại CT độc lập
    all_loaict = sorted(df["LoaiCT"].dropna().unique()) if "LoaiCT" in df.columns else []
    loaict_ui = st.multiselect(
        "LoaiCT", with_all_option(all_loaict), default=["All"], key="rev_loaict"
    )
    loaict_filter = normalize_filter(loaict_ui, all_loaict)

    # Brand -> Region -> Store (cascading)
    all_brands = sorted(df["Brand"].dropna().unique()) if "Brand" in df.columns else []
    brand_ui = st.multiselect(
        "Brand", with_all_option(all_brands), default=["All"], key="rev_brand"
    )
    brand_filter = normalize_filter(brand_ui, all_brands)

    df_b = df[df["Brand"].isin(brand_filter)] if brand_filter else df.iloc[0:0]

    all_regions = sorted(df_b["Region"].dropna().unique()) if "Region" in df_b.columns else []
    region_ui = st.multiselect(
        "Region", with_all_option(all_regions), default=["All"], key="rev_region"
    )
    region_filter = normalize_filter(region_ui, all_regions)

    df_br = df_b[df_b["Region"].isin(region_filter)] if region_filter else df_b.iloc[0:0]

    all_stores = sorted(df_br["Điểm_mua_hàng"].dropna().unique()) if "Điểm_mua_hàng" in df_br.columns else []
    store_ui = st.multiselect(
        "Điểm mua hàng", with_all_option(all_stores), default=["All"], key="rev_store"
    )
    store_filter = normalize_filter(store_ui, all_stores)

    # Check SĐT & Kiểm tra tên
    all_checksdt = sorted(df["Trạng_thái_số_điện_thoại"].dropna().unique()) if "Trạng_thái_số_điện_thoại" in df.columns else []
    checksdt_ui = st.multiselect(
        "Trạng_thái_số_điện_thoại",
        with_all_option(all_checksdt),
        default=["All"],
        key="rev_checksdt",
    )
    checksdt_filter = normalize_filter(checksdt_ui, all_checksdt)

    all_checkten = sorted(df["Kiểm_tra_tên"].dropna().unique()) if "Kiểm_tra_tên" in df.columns else []
    checkten_ui = st.multiselect(
        "Kiểm_tra_tên",
        with_all_option(all_checkten),
        default=["All"],
        key="rev_checkten",
    )
    checkten_filter = normalize_filter(checkten_ui, all_checkten)


# =====================================================
# APPLY FILTER
# =====================================================
mask = (
    (df["Ngày"] >= pd.to_datetime(start_date))
    & (df["Ngày"] <= pd.to_datetime(end_date))
)

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

df_filtered = df.loc[mask].copy()

if df_filtered.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# HELPER: TIME KEY
# =====================================================
def add_time_key(df_in: pd.DataFrame, grain: str):
    df_out = df_in.copy()
    if grain == "Ngày":
        df_out["Key"] = df_out["Ngày"].dt.date  # datetime.date
        df_out["Year"] = df_out["Ngày"].dt.year
        group_cols = ["Key"]
    else:
        df_out["Year"] = df_out["Ngày"].dt.year
        if grain == "Tuần":
            df_out["Key"] = df_out["Ngày"].dt.isocalendar().week.astype(int)
        elif grain == "Tháng":
            df_out["Key"] = df_out["Ngày"].dt.month.astype(int)
        elif grain == "Quý":
            df_out["Key"] = df_out["Ngày"].dt.quarter.astype(int)
        group_cols = ["Year", "Key"]
    return df_out, group_cols

# =====================================================
# SUMMARY TABLE
# =====================================================
def summarize_revenue(df_in: pd.DataFrame, grain: str) -> pd.DataFrame:
    if df_in.empty:
        return pd.DataFrame()

    df_tmp, group_cols = add_time_key(df_in, grain)

    summary = (
        df_tmp.groupby(group_cols)
        .agg(
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_KH=("Số_điện_thoại", "nunique"),
            Số_đơn_hàng=("Số_CT", "nunique"),
        )
        .reset_index()
    )

    summary["Tỷ_lệ_CK (%)"] = (
        100 * (1 - summary["Tổng_Net"] / summary["Tổng_Gross"])
    ).where(summary["Tổng_Gross"] != 0, 0)

    summary = summary.sort_values(group_cols)

    for col in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng"]:
        prev_col = f"Prev_{col}"
        pct_col = f"%_So_sánh_{col}"
        summary[prev_col] = summary[col].shift(1)
        summary[pct_col] = (
            (summary[col] - summary[prev_col]) / summary[prev_col] * 100
        ).where(summary[prev_col].notna() & (summary[prev_col] != 0))

    return summary

# =====================================================
# TOP/BOTTOM STORE (lọc theo kỳ được chọn)
# =====================================================
def top_bottom_store(df_in: pd.DataFrame, grain: str, top: bool = True, year=None, key=None) -> pd.DataFrame:
    if df_in.empty:
        return pd.DataFrame()

    df_store, group_cols = add_time_key(df_in, grain)
    group_cols_store = ["Điểm_mua_hàng"] + group_cols

    grouped = (
        df_store.groupby(group_cols_store, as_index=False)[["Tổng_Gross", "Tổng_Net"]]
        .sum()
    )

    grouped["Tỷ_lệ_CK (%)"] = (
        100 * (1 - grouped["Tổng_Net"] / grouped["Tổng_Gross"])
    ).where(grouped["Tổng_Gross"] != 0, 0)

    grouped = grouped.sort_values(["Điểm_mua_hàng"] + group_cols)
    grouped["Prev"] = grouped.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
    grouped["Change%"] = (
        (grouped["Tổng_Net"] - grouped["Prev"]) / grouped["Prev"] * 100
    ).where(grouped["Prev"].notna() & (grouped["Prev"] != 0))

    if grain == "Ngày":
        sel_key = key if key is not None else grouped["Key"].max()
        mask = grouped["Key"] == sel_key
    else:
        if (year is None) or (key is None):
            sel_year = grouped["Year"].max()
            sel_key = grouped.query("Year == @sel_year")["Key"].max()
        else:
            sel_year = year
            sel_key = key
        mask = (grouped["Year"] == sel_year) & (grouped["Key"] == sel_key)

    out = grouped.loc[mask].copy()
    out = out.sort_values("Tổng_Net", ascending=not top).head(10)
    return out

# =====================================================
# VIEW: RAW FILTERED (tuỳ chọn)
# =====================================================
with st.expander("📑 Xem dữ liệu đã lọc (mở/đóng)", expanded=False):
    st.dataframe(df_filtered, use_container_width=True)

# =====================================================
# SUMMARY DISPLAY + CHART
# =====================================================
st.subheader("📊 Tổng hợp doanh thu")
df_summary = summarize_revenue(df_filtered, time_grain)

if df_summary.empty:
    st.info("Không có dữ liệu sau khi lọc.")
    st.stop()

# Tạo cột label hiển thị đẹp
df_summary_show = df_summary.copy()

if time_grain == "Ngày":
    # Key là date
    df_summary_show["Kỳ"] = pd.to_datetime(df_summary_show["Key"], errors="coerce").dt.strftime("%Y-%m-%d")
else:
    if time_grain == "Tuần":
        df_summary_show["Kỳ"] = df_summary_show.apply(lambda r: f"Tuần {int(r['Key']):02d}/{int(r['Year'])}", axis=1)
    elif time_grain == "Tháng":
        df_summary_show["Kỳ"] = df_summary_show.apply(lambda r: f"{int(r['Year'])}-{int(r['Key']):02d}", axis=1)
    else:  # Quý
        df_summary_show["Kỳ"] = df_summary_show.apply(lambda r: f"Q{int(r['Key'])} {int(r['Year'])}", axis=1)

# Format số bằng Python
for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng",
          "Prev_Tổng_Gross", "Prev_Tổng_Net", "Prev_Số_KH", "Prev_Số_đơn_hàng"]:
    if c in df_summary_show.columns:
        df_summary_show[c] = df_summary_show[c].apply(fmt_int)

for c in ["Tỷ_lệ_CK (%)", "%_So_sánh_Tổng_Gross", "%_So_sánh_Tổng_Net", "%_So_sánh_Số_KH", "%_So_sánh_Số_đơn_hàng"]:
    if c in df_summary_show.columns:
        df_summary_show[c] = df_summary_show[c].apply(lambda v: fmt_pct(v, 2, with_sign=(c.startswith("%_So_sánh"))))

# Hiển thị bảng summary
show_cols = ["Kỳ"]
for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Tỷ_lệ_CK (%)",
          "Prev_Tổng_Net", "%_So_sánh_Tổng_Net"]:
    if c in df_summary_show.columns:
        show_cols.append(c)

show_df(df_summary_show[show_cols], title=None)

# Chart (plotly) dùng dữ liệu gốc (chưa format)
fig = px.line(
    df_summary,
    x="Key",
    y=["Tổng_Gross", "Tổng_Net"],
    markers=True,
    title=f"Doanh thu theo {time_grain}",
)
st.plotly_chart(fig, use_container_width=True)

# =====================================================
# REGION REPORT + FILTER "CHỌN KỲ"
# =====================================================
st.subheader("🌍 Doanh thu theo Region")

df_region, group_cols = add_time_key(df_filtered, time_grain)
group_cols_region = ["Region"] + group_cols

grouped_region = (
    df_region.groupby(group_cols_region, as_index=False)
    .agg(
        Tổng_Gross=("Tổng_Gross", "sum"),
        Tổng_Net=("Tổng_Net", "sum"),
        Số_KH=("Số_điện_thoại", "nunique"),
        Số_đơn_hàng=("Số_CT", "nunique"),
    )
)

grouped_region["Tỷ_lệ_CK (%)"] = (
    100 * (1 - grouped_region["Tổng_Net"] / grouped_region["Tổng_Gross"])
).where(grouped_region["Tổng_Gross"] != 0, 0)

# So sánh kỳ trước theo từng Region
grouped_region = grouped_region.sort_values(["Region"] + group_cols)
for col in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng"]:
    prev_col = f"Prev_{col}"
    pct_col = f"%_So_sánh_{col}"
    grouped_region[prev_col] = grouped_region.groupby("Region")[col].shift(1)
    grouped_region[pct_col] = (
        (grouped_region[col] - grouped_region[prev_col]) / grouped_region[prev_col] * 100
    ).where(grouped_region[prev_col].notna() & (grouped_region[prev_col] != 0))

# ====== Chọn kỳ để xem Region
st.markdown("### 🔍 Chọn kỳ để xem bảng Region")

if time_grain == "Ngày":
    periods = (
        df_summary[["Key"]]
        .drop_duplicates()
        .sort_values("Key")
        .copy()
    )
    periods["label"] = pd.to_datetime(periods["Key"], errors="coerce").dt.strftime("%Y-%m-%d")
    sel_label = st.selectbox("Kỳ (Ngày)", periods["label"].tolist(), index=len(periods)-1, key="rev_region_period")
    sel_key = periods.loc[periods["label"] == sel_label, "Key"].iloc[0]
    region_mask = grouped_region["Key"] == sel_key
else:
    periods = (
        df_summary[["Year", "Key"]]
        .drop_duplicates()
        .sort_values(["Year", "Key"])
        .copy()
    )
    if time_grain == "Tuần":
        periods["label"] = periods.apply(lambda r: f"Tuần {int(r['Key']):02d}/{int(r['Year'])}", axis=1)
    elif time_grain == "Tháng":
        periods["label"] = periods.apply(lambda r: f"{int(r['Year'])}-{int(r['Key']):02d}", axis=1)
    else:  # Quý
        periods["label"] = periods.apply(lambda r: f"Q{int(r['Key'])} {int(r['Year'])}", axis=1)

    sel_label = st.selectbox("Kỳ", periods["label"].tolist(), index=len(periods)-1, key="rev_region_period")
    row = periods.loc[periods["label"] == sel_label].iloc[0]
    sel_year = int(row["Year"])
    sel_key = int(row["Key"])
    region_mask = (grouped_region["Year"] == sel_year) & (grouped_region["Key"] == sel_key)

df_region_view = grouped_region.loc[region_mask].copy()
df_region_view = df_region_view.sort_values("Tổng_Net", ascending=False)

# Format hiển thị Region
df_region_show = df_region_view.copy()
if time_grain == "Ngày":
    df_region_show["Kỳ"] = pd.to_datetime(df_region_show["Key"], errors="coerce").dt.strftime("%Y-%m-%d")
else:
    if time_grain == "Tuần":
        df_region_show["Kỳ"] = df_region_show.apply(lambda r: f"Tuần {int(r['Key']):02d}/{int(r['Year'])}", axis=1)
    elif time_grain == "Tháng":
        df_region_show["Kỳ"] = df_region_show.apply(lambda r: f"{int(r['Year'])}-{int(r['Key']):02d}", axis=1)
    else:
        df_region_show["Kỳ"] = df_region_show.apply(lambda r: f"Q{int(r['Key'])} {int(r['Year'])}", axis=1)

for c in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng",
          "Prev_Tổng_Gross", "Prev_Tổng_Net", "Prev_Số_KH", "Prev_Số_đơn_hàng"]:
    if c in df_region_show.columns:
        df_region_show[c] = df_region_show[c].apply(fmt_int)

for c in ["Tỷ_lệ_CK (%)", "%_So_sánh_Tổng_Gross", "%_So_sánh_Tổng_Net", "%_So_sánh_Số_KH", "%_So_sánh_Số_đơn_hàng"]:
    if c in df_region_show.columns:
        df_region_show[c] = df_region_show[c].apply(lambda v: fmt_pct(v, 2, with_sign=(c.startswith("%_So_sánh"))))

region_cols = ["Kỳ", "Region", "Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng", "Tỷ_lệ_CK (%)",
               "Prev_Tổng_Net", "%_So_sánh_Tổng_Net"]
region_cols = [c for c in region_cols if c in df_region_show.columns]
show_df(df_region_show[region_cols], title=None)

# =====================================================
# STORE TOP / BOTTOM + FILTER "CHỌN KỲ"
# =====================================================
st.subheader("🏪 Top/Bottom 10 Điểm mua hàng")

st.markdown("### 🔍 Chọn kỳ để xem Top/Bottom")
if time_grain == "Ngày":
    period_df = df_summary[["Key"]].drop_duplicates().sort_values("Key").copy()
    period_df["label"] = pd.to_datetime(period_df["Key"], errors="coerce").dt.strftime("%Y-%m-%d")
    sel_label2 = st.selectbox("Kỳ (Ngày)", period_df["label"].tolist(), index=len(period_df)-1, key="rev_store_period")
    sel_key2 = period_df.loc[period_df["label"] == sel_label2, "Key"].iloc[0]
    top10 = top_bottom_store(df_filtered, time_grain, top=True, key=sel_key2)
    bottom10 = top_bottom_store(df_filtered, time_grain, top=False, key=sel_key2)
else:
    period_df = df_summary[["Year", "Key"]].drop_duplicates().sort_values(["Year", "Key"]).copy()
    if time_grain == "Tuần":
        period_df["label"] = period_df.apply(lambda r: f"Tuần {int(r['Key']):02d}/{int(r['Year'])}", axis=1)
    elif time_grain == "Tháng":
        period_df["label"] = period_df.apply(lambda r: f"{int(r['Year'])}-{int(r['Key']):02d}", axis=1)
    else:
        period_df["label"] = period_df.apply(lambda r: f"Q{int(r['Key'])} {int(r['Year'])}", axis=1)

    sel_label2 = st.selectbox("Kỳ", period_df["label"].tolist(), index=len(period_df)-1, key="rev_store_period")
    row2 = period_df.loc[period_df["label"] == sel_label2].iloc[0]
    sel_year2 = int(row2["Year"])
    sel_key2 = int(row2["Key"])
    top10 = top_bottom_store(df_filtered, time_grain, top=True, year=sel_year2, key=sel_key2)
    bottom10 = top_bottom_store(df_filtered, time_grain, top=False, year=sel_year2, key=sel_key2)

# Format Top/Bottom
def format_store_table(dfin: pd.DataFrame) -> pd.DataFrame:
    if dfin.empty:
        return dfin
    out = dfin.copy()

    # Key/Year hiển thị
    if time_grain == "Ngày":
        out["Kỳ"] = pd.to_datetime(out["Key"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        if time_grain == "Tuần":
            out["Kỳ"] = out.apply(lambda r: f"Tuần {int(r['Key']):02d}/{int(r['Year'])}", axis=1)
        elif time_grain == "Tháng":
            out["Kỳ"] = out.apply(lambda r: f"{int(r['Year'])}-{int(r['Key']):02d}", axis=1)
        else:
            out["Kỳ"] = out.apply(lambda r: f"Q{int(r['Key'])} {int(r['Year'])}", axis=1)

    for c in ["Tổng_Gross", "Tổng_Net", "Prev"]:
        if c in out.columns:
            out[c] = out[c].apply(fmt_int)

    if "Tỷ_lệ_CK (%)" in out.columns:
        out["Tỷ_lệ_CK (%)"] = out["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
    if "Change%" in out.columns:
        out["Change%"] = out["Change%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))

    cols = ["Kỳ", "Điểm_mua_hàng", "Tổng_Gross", "Tổng_Net", "Tỷ_lệ_CK (%)", "Prev", "Change%"]
    cols = [c for c in cols if c in out.columns]
    return out[cols]

top10_show = format_store_table(top10)
bottom10_show = format_store_table(bottom10)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🏆 Top 10 Điểm mua hàng")
    if top10_show.empty:
        st.info("Không có dữ liệu.")
    else:
        st.dataframe(top10_show, use_container_width=True, hide_index=True)

with col2:
    st.markdown("### 📉 Bottom 10 Điểm mua hàng")
    if bottom10_show.empty:
        st.info("Không có dữ liệu.")
    else:
        st.dataframe(bottom10_show, use_container_width=True, hide_index=True)
