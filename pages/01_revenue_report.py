import pandas as pd
import streamlit as st
import plotly.express as px

from load_data import get_active_data # dùng chung dữ liệu Parquet

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
# SIDEBAR FILTER (Brand → Region → Cửa hàng phụ thuộc)
# =====================================================

# Các list độc lập
loaict_options   = sorted(df["LoaiCT"].dropna().unique())
checksdt_options = sorted(df["Trạng_thái_số_điện_thoại"].dropna().unique())
checkten_options = sorted(df["Kiểm_tra_tên"].dropna().unique())

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

    # ====== Brand (gốc) ======
    brand_all = sorted(df["Brand"].dropna().unique())
    brand_raw = st.multiselect(
        "Brand",
        ["Tất cả"] + brand_all,
        default=["Tất cả"],
        key="rev_brand",
    )

    # Brand thực sự được chọn để lọc Region
    brand_selected = brand_all if (not brand_raw or "Tất cả" in brand_raw) else brand_raw
    df_for_region = df[df["Brand"].isin(brand_selected)]

    # ====== Region phụ thuộc Brand ======
    region_all = sorted(df_for_region["Region"].dropna().unique())
    region_raw = st.multiselect(
        "Region",
        ["Tất cả"] + region_all,
        default=["Tất cả"],
        key="rev_region",
    )

    region_selected = region_all if (not region_raw or "Tất cả" in region_raw) else region_raw
    df_for_store = df_for_region[df_for_region["Region"].isin(region_selected)]

    # ====== Cửa hàng phụ thuộc Brand + Region ======
    store_all = sorted(df_for_store["Điểm_mua_hàng"].dropna().unique())
    store_raw = st.multiselect(
        "Điểm mua hàng",
        ["Tất cả"] + store_all,
        default=["Tất cả"],
        key="rev_store",
    )

    # ====== Các filter khác (không phụ thuộc) ======
    loaict_raw = st.multiselect(
        "LoaiCT",
        ["Tất cả"] + loaict_options,
        default=["Tất cả"],
        key="rev_loaict",
    )
    checksdt_raw = st.multiselect(
        "Trạng_thái_số_điện_thoại",
        ["Tất cả"] + checksdt_options,
        default=["Tất cả"],
        key="rev_checksdt",
    )
    checkten_raw = st.multiselect(
        "Kiểm_tra_tên",
        ["Tất cả"] + checkten_options,
        default=["Tất cả"],
        key="rev_checkten",
    )

# ---------- Hàm xử lý "Tất cả" ----------
def clean_filter(values, all_values):
    if (not values) or ("Tất cả" in values):
        return all_values
    return values

brand_filter   = clean_filter(brand_raw,   brand_all)
region_filter  = clean_filter(region_raw,  region_all)
store_filter   = clean_filter(store_raw,   store_all)
loaict_filter  = clean_filter(loaict_raw,  loaict_options)
checksdt_filter = clean_filter(checksdt_raw, checksdt_options)
checkten_filter = clean_filter(checkten_raw, checkten_options)

# ---------- Lọc dữ liệu ----------
mask = (
    (df["Ngày"] >= pd.to_datetime(start_date))
    & (df["Ngày"] <= pd.to_datetime(end_date))
    & (df["Brand"].isin(brand_filter))
    & (df["Region"].isin(region_filter))
    & (df["Điểm_mua_hàng"].isin(store_filter))
    & (df["LoaiCT"].isin(loaict_filter))
    & (df["Trạng_thái_số_điện_thoại"].isin(checksdt_filter))
    & (df["Kiểm_tra_tên"].isin(checkten_filter))
)

df_filtered = df.loc[mask].copy()

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


def top_bottom_store(df_in: pd.DataFrame, grain: str, top: bool = True) -> pd.DataFrame:
    """Top/Bottom 10 Điểm_mua_hàng theo Tổng_Net ở kỳ mới nhất."""
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

    # Lấy kỳ mới nhất
    if grain == "Ngày":
        latest_key = grouped["Key"].max()
        latest_mask = grouped["Key"] == latest_key
    else:
        latest_year = grouped["Year"].max()
        latest_key = grouped.query("Year == @latest_year")["Key"].max()
        latest_mask = (grouped["Year"] == latest_year) & (grouped["Key"] == latest_key)

    latest = grouped.loc[latest_mask].copy()
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
# STORE TOP / BOTTOM
# =====================================================
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
                "Tổng_Gross": st.column_config.NumberColumn(
                    "Gross", format="%.0f"
                ),
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
    if df_bottom10.empty:
        st.info("Không có dữ liệu.")
    else:
        st.data_editor(
            df_bottom10,
            width="stretch",
            hide_index=True,
            column_config={
                "Tổng_Gross": st.column_config.NumberColumn(
                    "Gross", format="%.0f"
                ),
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
