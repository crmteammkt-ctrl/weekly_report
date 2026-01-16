import pandas as pd
import streamlit as st
import plotly.express as px

from load_data import load_data  # dùng chung dữ liệu Parquet

# =====================
# TITLE
# =====================
st.title("📈 Báo cáo Doanh thu")

# =====================
# LOAD DATA (từ Parquet)
# =====================
@st.cache_data(show_spinner="📦 Đang load dữ liệu...")
def get_data():
    df = load_data()
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    return df.dropna(subset=["Ngày"])

df = get_data()

# =====================
# SIDEBAR FILTER
# =====================
brands   = sorted(df["Brand"].dropna().unique())
regions  = sorted(df["Region"].dropna().unique())
stores   = sorted(df["Điểm_mua_hàng"].dropna().unique())
loaicts  = sorted(df["LoaiCT"].dropna().unique())
checksdt = sorted(df["Trạng_thái_số_điện_thoại"].dropna().unique())
checkten = sorted(df["Kiểm_tra_tên"].dropna().unique())

with st.sidebar:
    st.header("Bộ lọc dữ liệu")

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key="rev_time_grain"
    )

    start_date = st.date_input(
        "Từ ngày",
        df["Ngày"].min().date(),
        key="rev_start_date"
    )
    end_date = st.date_input(
        "Đến ngày",
        df["Ngày"].max().date(),
        key="rev_end_date"
    )

    brand_filter  = st.multiselect("Brand", ["Tất cả"] + brands,  default=["Tất cả"], key="rev_brand")
    region_filter = st.multiselect("Region", ["Tất cả"] + regions, default=["Tất cả"], key="rev_region")
    store_filter  = st.multiselect("Điểm mua hàng", ["Tất cả"] + stores, default=["Tất cả"], key="rev_store")
    loaict_filter = st.multiselect("LoaiCT", ["Tất cả"] + loaicts, default=["Tất cả"], key="rev_loaict")
    checksdt_filter = st.multiselect("Trạng_thái_số_điện_thoại", ["Tất cả"] + checksdt, default=["Tất cả"], key="rev_checksdt")
    checkten_filter = st.multiselect("Kiểm_tra_tên", ["Tất cả"] + checkten, default=["Tất cả"], key="rev_checkten")

# Xử lý "Tất cả"
if "Tất cả" in brand_filter:
    brand_filter = brands
if "Tất cả" in region_filter:
    region_filter = regions
if "Tất cả" in store_filter:
    store_filter = stores
if "Tất cả" in loaict_filter:
    loaict_filter = loaicts
if "Tất cả" in checksdt_filter:
    checksdt_filter = checksdt
if "Tất cả" in checkten_filter:
    checkten_filter = checkten

# Lọc dữ liệu
mask = (
    (df["Ngày"] >= pd.to_datetime(start_date)) &
    (df["Ngày"] <= pd.to_datetime(end_date)) &
    (df["Brand"].isin(brand_filter)) &
    (df["Region"].isin(region_filter)) &
    (df["Điểm_mua_hàng"].isin(store_filter)) &
    (df["LoaiCT"].isin(loaict_filter)) &
    (df["Trạng_thái_số_điện_thoại"].isin(checksdt_filter)) &
    (df["Kiểm_tra_tên"].isin(checkten_filter))
)

df_filtered = df.loc[mask].copy()

# =====================
# HELPER FUNCTIONS
# =====================
def add_time_key(df_in, grain):
    """Thêm cột Key + Year để gom theo Ngày/Tuần/Tháng/Quý."""
    df_out = df_in.copy()
    if grain == "Ngày":
        df_out["Key"] = df_out["Ngày"].dt.date
        df_out["Year"] = df_out["Ngày"].dt.year
        group_cols = ["Key"]
    else:
        df_out["Year"] = df_out["Ngày"].dt.year
        if grain == "Tuần":
            df_out["Key"] = df_out["Ngày"].dt.isocalendar().week
        elif grain == "Tháng":
            df_out["Key"] = df_out["Ngày"].dt.month
        elif grain == "Quý":
            df_out["Key"] = df_out["Ngày"].dt.quarter
        group_cols = ["Year", "Key"]
    return df_out, group_cols


def summarize_revenue(df_in, grain):
    """Tổng hợp Gross/Net/Số KH/Số ĐH + so sánh kỳ trước."""
    if df_in.empty:
        return pd.DataFrame()

    df_tmp, group_cols = add_time_key(df_in, grain)

    summary = (
        df_tmp
        .groupby(group_cols)
        .agg(
            Tổng_Gross=("Tổng_Gross", "sum"),
            Tổng_Net=("Tổng_Net", "sum"),
            Số_KH=("Số_điện_thoại", "nunique"),
            Số_đơn_hàng=("Số_CT", "nunique")
        )
        .reset_index()
    )

    summary["Tỷ_lệ_CK (%)"] = (
        100 * (1 - summary["Tổng_Net"] / summary["Tổng_Gross"])
    ).where(summary["Tổng_Gross"] != 0, 0)

    summary = summary.sort_values(group_cols)

    for col in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng"]:
        prev_col = f"Prev_{col}"
        pct_col  = f"%_So_sánh_{col}"
        summary[prev_col] = summary[col].shift(1)
        summary[pct_col] = (
            (summary[col] - summary[prev_col]) / summary[prev_col] * 100
        ).where(summary[prev_col].notna() & (summary[prev_col] != 0))

    return summary


def top_bottom_store(df_in, grain, top=True):
    """Top/Bottom 10 Điểm_mua_hàng theo Tổng_Net ở kỳ mới nhất."""
    if df_in.empty:
        return pd.DataFrame()

    df_store, group_cols = add_time_key(df_in, grain)
    group_cols_store = ["Điểm_mua_hàng"] + group_cols

    grouped = (
        df_store
        .groupby(group_cols_store, as_index=False)[["Tổng_Gross", "Tổng_Net"]]
        .sum()
    )
    grouped["Tỷ_lệ_CK (%)"] = (
        100 * (1 - grouped["Tổng_Net"] / grouped["Tổng_Gross"])
    ).where(grouped["Tổng_Gross"] != 0, 0)

    # Prev & Change theo từng store
    grouped = grouped.sort_values(["Điểm_mua_hàng"] + group_cols)
    grouped["Prev"] = grouped.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
    grouped["Change%"] = (
        (grouped["Tổng_Net"] - grouped["Prev"]) / grouped["Prev"] * 100
    ).where(grouped["Prev"].notna() & (grouped["Prev"] != 0))

    # Lấy kỳ mới nhất
    if grain == "Ngày":
        latest_key = grouped["Key"].max()
        latest_mask = grouped["Key"] == latest_key
    else:
        latest_year = grouped["Year"].max()
        latest_key = grouped.query("Year==@latest_year")["Key"].max()
        latest_mask = (grouped["Year"] == latest_year) & (grouped["Key"] == latest_key)

    latest = grouped.loc[latest_mask].copy()

    latest = latest.sort_values("Tổng_Net", ascending=not top).head(10)
    return latest

# =====================
# DATA VIEW
# =====================
st.subheader("📑 Dữ liệu đã lọc")
st.dataframe(df_filtered, width="stretch")

# =====================
# SUMMARY TABLE
# =====================
st.subheader("📊 Tổng hợp doanh thu")

df_summary = summarize_revenue(df_filtered, time_grain)

if df_summary.empty:
    st.info("Không có dữ liệu sau khi lọc.")
else:
    st.data_editor(
        df_summary,
        width="stretch",
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn("Gross", format="%.0f"),
            "Tổng_Net": st.column_config.NumberColumn("Net", format="%.0f"),
            "Số_KH": st.column_config.NumberColumn("Số KH", format="%.0f"),
            "Số_đơn_hàng": st.column_config.NumberColumn("Số ĐH", format="%.0f"),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f"),
            "Prev_Tổng_Gross": st.column_config.NumberColumn("Gross kỳ trước", format="%.0f"),
            "Prev_Tổng_Net": st.column_config.NumberColumn("Net kỳ trước", format="%.0f"),
            "Prev_Số_KH": st.column_config.NumberColumn("KH kỳ trước", format="%.0f"),
            "Prev_Số_đơn_hàng": st.column_config.NumberColumn("ĐH kỳ trước", format="%.0f"),
            "%_So_sánh_Tổng_Gross": st.column_config.NumberColumn("Gross (%)", format="%.2f"),
            "%_So_sánh_Tổng_Net": st.column_config.NumberColumn("Net (%)", format="%.2f"),
            "%_So_sánh_Số_KH": st.column_config.NumberColumn("KH (%)", format="%.2f"),
            "%_So_sánh_Số_đơn_hàng": st.column_config.NumberColumn("ĐH (%)", format="%.2f"),
        },
    )

    # Line chart Gross/Net
    fig = px.line(
        df_summary,
        x="Key",
        y=["Tổng_Gross", "Tổng_Net"],
        markers=True,
        title=f"Doanh thu theo {time_grain}",
    )
    st.plotly_chart(fig, width="stretch")

# =====================
# REGION REPORT
# =====================
st.subheader("🌍 Doanh thu theo Region")

if df_filtered.empty:
    st.info("Không có dữ liệu sau khi lọc.")
else:
    df_region, group_cols = add_time_key(df_filtered, time_grain)
    group_cols_region = ["Region"] + group_cols

    grouped_region = (
        df_region
        .groupby(group_cols_region, as_index=False)
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

    # tính prev & % so sánh theo Region
    grouped_region = grouped_region.sort_values(["Region"] + group_cols_region[1:])
    for col in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng"]:
        prev_col = f"Prev_{col}"
        pct_col  = f"%_So_sánh_{col}"
        grouped_region[prev_col] = grouped_region.groupby("Region")[col].shift(1)
        grouped_region[pct_col] = (
            (grouped_region[col] - grouped_region[prev_col]) / grouped_region[prev_col] * 100
        ).where(grouped_region[prev_col].notna() & (grouped_region[prev_col] != 0))

    # Lấy kỳ mới nhất để xem
    if time_grain == "Ngày":
        latest_key = grouped_region["Key"].max()
        latest_mask = grouped_region["Key"] == latest_key
    else:
        latest_year = grouped_region["Year"].max()
        latest_key = grouped_region.query("Year==@latest_year")["Key"].max()
        latest_mask = (grouped_region["Year"] == latest_year) & (grouped_region["Key"] == latest_key)

    df_region_latest = grouped_region.loc[latest_mask].copy()

    st.data_editor(
        df_region_latest,
        width="stretch",
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn("Gross", format="%.0f"),
            "Tổng_Net": st.column_config.NumberColumn("Net", format="%.0f"),
            "Số_KH": st.column_config.NumberColumn("Số KH", format="%.0f"),
            "Số_đơn_hàng": st.column_config.NumberColumn("Số ĐH", format="%.0f"),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f"),
        },
    )

# =====================
# STORE TOP / BOTTOM
# =====================
st.subheader("🏪 Top/Bottom 10 Điểm mua hàng")

df_top10 = top_bottom_store(df_filtered, time_grain, top=True)
df_bottom10 = top_bottom_store(df_filtered, time_grain, top=False)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🏆 Top 10 Điểm mua hàng")
    if df_top10.empty:
        st.info("Không có dữ liệu.")
    else:
        st.data_editor(
            df_top10,
            width="stretch",
            hide_index=True,
            column_config={
                "Tổng_Gross": st.column_config.NumberColumn("Gross", format="%.0f"),
                "Tổng_Net": st.column_config.NumberColumn("Net", format="%.0f"),
                "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f"),
                "Prev": st.column_config.NumberColumn("Net kỳ trước", format="%.0f"),
                "Change%": st.column_config.NumberColumn("Tăng/giảm (%)", format="%.2f"),
            },
        )

with col2:
    st.markdown("### 📉 Bottom 10 Điểm mua hàng")
    if df_bottom10.empty:
        st.info("Không có dữ liệu.")
    else:
        st.data_editor(
            df_bottom10,
            width="stretch",
            hide_index=True,
            column_config={
                "Tổng_Gross": st.column_config.NumberColumn("Gross", format="%.0f"),
                "Tổng_Net": st.column_config.NumberColumn("Net", format="%.0f"),
                "Tỷ_lệ_CK (%)": st.column_config.NumberColumn("Tỷ lệ CK (%)", format="%.2f"),
                "Prev": st.column_config.NumberColumn("Net kỳ trước", format="%.0f"),
                "Change%": st.column_config.NumberColumn("Tăng/giảm (%)", format="%.2f"),
            },
        )
