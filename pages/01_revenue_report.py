# pages/01_revenue_report.py

import pandas as pd
import streamlit as st
import plotly.express as px

from load_data import get_active_data

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="📈 Báo cáo Doanh thu", layout="wide")
st.title("📈 Báo cáo Doanh thu")

# =====================================================
# LẤY DỮ LIỆU HIỆN HÀNH
# =====================================================
df = get_active_data()
st.sidebar.caption(
    "🔎 Đang dùng nguồn: **{}**".format(
        st.session_state.get("active_source", "default")
    )
)

df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
df = df.dropna(subset=["Ngày"])

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích. Kiểm tra lại nguồn dữ liệu.")
    st.stop()

# =====================================================
# SIDEBAR FILTER (có liên kết Brand → Region → Điểm mua hàng)
# =====================================================
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
    all_loaict = sorted(df["LoaiCT"].dropna().unique())
    loaict_filter = st.multiselect(
        "LoaiCT", all_loaict, default=all_loaict, key="rev_loaict"
    )

    # Brand -> Region -> Điểm mua hàng
    all_brands = sorted(df["Brand"].dropna().unique())
    brand_filter = st.multiselect(
        "Brand", all_brands, default=all_brands, key="rev_brand"
    )

    df_b = df[df["Brand"].isin(brand_filter)]

    all_regions = sorted(df_b["Region"].dropna().unique())
    region_filter = st.multiselect(
        "Region", all_regions, default=all_regions, key="rev_region"
    )

    df_br = df_b[df_b["Region"].isin(region_filter)]

    all_stores = sorted(df_br["Điểm_mua_hàng"].dropna().unique())
    store_filter = st.multiselect(
        "Điểm mua hàng", all_stores, default=all_stores, key="rev_store"
    )

    # Check SĐT & Kiểm tra tên
    all_checksdt = sorted(df["Trạng_thái_số_điện_thoại"].dropna().unique())
    checksdt_filter = st.multiselect(
        "Trạng_thái_số_điện_thoại",
        all_checksdt,
        default=all_checksdt,
        key="rev_checksdt",
    )

    all_checkten = sorted(df["Kiểm_tra_tên"].dropna().unique())
    checkten_filter = st.multiselect(
        "Kiểm_tra_tên",
        all_checkten,
        default=all_checkten,
        key="rev_checkten",
    )

# Lọc dữ liệu
mask = (
    (df["Ngày"] >= pd.to_datetime(start_date))
    & (df["Ngày"] <= pd.to_datetime(end_date))
    & (df["LoaiCT"].isin(loaict_filter))
    & (df["Brand"].isin(brand_filter))
    & (df["Region"].isin(region_filter))
    & (df["Điểm_mua_hàng"].isin(store_filter))
    & (df["Trạng_thái_số_điện_thoại"].isin(checksdt_filter))
    & (df["Kiểm_tra_tên"].isin(checkten_filter))
)
df_filtered = df.loc[mask].copy()

if df_filtered.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def add_time_key(df_in: pd.DataFrame, grain: str):
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


def summarize_revenue(df_in: pd.DataFrame, grain: str) -> pd.DataFrame:
    """Tổng hợp Gross/Net/Số KH/Số ĐH + so sánh kỳ trước."""
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


def top_bottom_store(
    df_in: pd.DataFrame,
    grain: str,
    top: bool = True,
    year=None,
    key=None,
) -> pd.DataFrame:
    """Top/Bottom 10 Điểm_mua_hàng theo Tổng_Net ở 1 kỳ cụ thể."""
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

    # ----------- CHỌN KỲ ĐỂ XEM -----------
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

    latest = grouped.loc[mask].copy()
    latest = latest.sort_values("Tổng_Net", ascending=not top).head(10)
    return latest


# =====================================================
# DATA VIEW
# =====================================================
st.subheader("📑 Dữ liệu đã lọc")
st.dataframe(df_filtered, width="stretch")

# =====================================================
# SUMMARY TABLE
# =====================================================
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
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                "Tỷ lệ CK (%)", format="%.2f"
            ),
        },
    )

    fig = px.line(
        df_summary,
        x="Key",
        y=["Tổng_Gross", "Tổng_Net"],
        markers=True,
        title=f"Doanh thu theo {time_grain}",
    )
    st.plotly_chart(fig, width="stretch")

# =====================================================
# REGION REPORT
# =====================================================
st.subheader("🌍 Doanh thu theo Region")

if df_filtered.empty:
    st.info("Không có dữ liệu sau khi lọc.")
else:
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

    grouped_region = grouped_region.sort_values(["Region"] + group_cols_region[1:])
    for col in ["Tổng_Gross", "Tổng_Net", "Số_KH", "Số_đơn_hàng"]:
        prev_col = f"Prev_{col}"
        pct_col = f"%_So_sánh_{col}"
        grouped_region[prev_col] = grouped_region.groupby("Region")[col].shift(1)
        grouped_region[pct_col] = (
            (grouped_region[col] - grouped_region[prev_col])
            / grouped_region[prev_col]
            * 100
        ).where(
            grouped_region[prev_col].notna()
            & (grouped_region[prev_col] != 0)
        )

    if time_grain == "Ngày":
        latest_key = grouped_region["Key"].max()
        latest_mask = grouped_region["Key"] == latest_key
    else:
        latest_year = grouped_region["Year"].max()
        latest_key = grouped_region.query("Year == @latest_year")["Key"].max()
        latest_mask = (grouped_region["Year"] == latest_year) & (
            grouped_region["Key"] == latest_key
        )

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
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                "Tỷ lệ CK (%)", format="%.2f"
            ),
        },
    )

# =====================================================
# STORE TOP / BOTTOM (có chọn kỳ)
# =====================================================
st.subheader("🏪 Top/Bottom 10 Điểm mua hàng")

# Tạo danh sách kỳ để chọn (dùng df_summary để tránh tính lại)
if not df_summary.empty:
    period_df = df_summary[["Year", "Key"]].drop_duplicates().copy()

    # Tạo label đẹp
    if time_grain == "Ngày":
        period_df["label"] = period_df["Key"].astype(str)
    elif time_grain == "Tuần":
        period_df["label"] = period_df.apply(
            lambda r: f"Tuần {int(r['Key']):02d}/{int(r['Year'])}", axis=1
        )
    elif time_grain == "Tháng":
        period_df["label"] = period_df.apply(
            lambda r: f"{int(r['Year'])}-{int(r['Key']):02d}", axis=1
        )
    elif time_grain == "Quý":
        period_df["label"] = period_df.apply(
            lambda r: f"Q{int(r['Key'])} {int(r['Year'])}", axis=1
        )
    else:
        period_df["label"] = period_df["Year"].astype(str)

    period_df = period_df.sort_values(["Year", "Key"])

    st.markdown("### 🔍 Chọn kỳ để xem Top/Bottom")
    sel_label = st.selectbox(
        "Kỳ thời gian",
        options=period_df["label"].tolist(),
        index=len(period_df) - 1,
    )

    row_sel = period_df.loc[period_df["label"] == sel_label].iloc[0]
    sel_year = int(row_sel["Year"]) if "Year" in row_sel else None
    sel_key = row_sel["Key"]

    if time_grain == "Ngày":
        top10 = top_bottom_store(df_filtered, time_grain, top=True, key=sel_key)
        bottom10 = top_bottom_store(df_filtered, time_grain, top=False, key=sel_key)
    else:
        top10 = top_bottom_store(
            df_filtered, time_grain, top=True, year=sel_year, key=sel_key
        )
        bottom10 = top_bottom_store(
            df_filtered, time_grain, top=False, year=sel_year, key=sel_key
        )
else:
    top10 = pd.DataFrame()
    bottom10 = pd.DataFrame()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏆 Top 10 Điểm mua hàng")
    if top10.empty:
        st.info("Không có dữ liệu.")
    else:
        st.data_editor(
            top10,
            width="stretch",
            hide_index=True,
            column_config={
                "Tổng_Gross": st.column_config.NumberColumn("Gross", format="%.0f"),
                "Tổng_Net": st.column_config.NumberColumn("Net", format="%.0f"),
                "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                    "Tỷ lệ CK (%)", format="%.2f"
                ),
                "Prev": st.column_config.NumberColumn(
                    "Net kỳ trước", format="%.0f"
                ),
                "Change%": st.column_config.NumberColumn(
                    "Tăng/giảm (%)", format="%.2f"
                ),
            },
        )

with col2:
    st.markdown("### 📉 Bottom 10 Điểm mua hàng")
    if bottom10.empty:
        st.info("Không có dữ liệu.")
    else:
        st.data_editor(
            bottom10,
            width="stretch",
            hide_index=True,
            column_config={
                "Tổng_Gross": st.column_config.NumberColumn("Gross", format="%.0f"),
                "Tổng_Net": st.column_config.NumberColumn("Net", format="%.0f"),
                "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                    "Tỷ lệ CK (%)", format="%.2f"
                ),
                "Prev": st.column_config.NumberColumn(
                    "Net kỳ trước", format="%.0f"
                ),
                "Change%": st.column_config.NumberColumn(
                    "Tăng/giảm (%)", format="%.2f"
                ),
            },
        )
