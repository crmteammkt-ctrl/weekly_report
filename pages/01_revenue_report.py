# pages/01_Revenue_Report.py

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from load_data import load_data  # đọc dữ liệu từ parquet


st.title("📈 Báo cáo Doanh thu")

# =====================
# Load dữ liệu
# =====================
@st.cache_data(show_spinner="📦 Đang load dữ liệu doanh thu...")
def _load_df():
    df = load_data()
    df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
    return df.dropna(subset=["Ngày"])

df = _load_df()

# Lấy danh sách cho bộ lọc
brands  = sorted(df["Brand"].dropna().unique().tolist())
regions = sorted(df["Region"].dropna().unique().tolist())
stores  = sorted(df["Điểm_mua_hàng"].dropna().unique().tolist())
loaicts = sorted(df["LoaiCT"].dropna().unique().tolist())

# =====================
# Bộ lọc sidebar
# =====================
with st.sidebar:
    st.header("Bộ lọc dữ liệu – Doanh thu")

    analysis_type = st.selectbox(
        "Chọn kiểu phân tích",
        ["Ngày", "Tuần", "Tháng", "Khoảng thời gian"],
        key="rev_analysis_type",
    )

    # mặc định lấy min/max theo data
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

    # Bộ lọc nhiều lựa chọn
    brand_filter = st.multiselect(
        "Chọn Brand", ["Tất cả"] + brands, default=["Tất cả"], key="rev_brand_filter"
    )
    region_filter = st.multiselect(
        "Chọn Region", ["Tất cả"] + regions, default=["Tất cả"], key="rev_region_filter"
    )
    store_filter = st.multiselect(
        "Chọn Điểm mua hàng",
        ["Tất cả"] + stores,
        default=["Tất cả"],
        key="rev_store_filter",
    )
    loaiCT_filter = st.multiselect(
        "Chọn Loại CT",
        ["Tất cả"] + loaicts,
        default=["Tất cả"],
        key="rev_loaiCT_filter",
    )

    st.markdown("---")
    st.header("Top khách hàng")

    top_percent_option = st.number_input(
        "Nhập % Top khách hàng theo doanh thu",
        min_value=1,
        max_value=100,
        value=20,
        step=1,
        format="%d",
        key="rev_top_percent",
    )

    doanh_thu_type = st.selectbox(
        "Loại doanh thu để xét Top",
        options=["Tổng_Net", "Tổng_Gross"],
        index=0,
        format_func=lambda x: "Doanh thu sau CK" if x == "Tổng_Net" else "Doanh thu trước CK",
        key="rev_doanh_thu_type",
    )

# Xử lý giá trị "Tất cả"
if "Tất cả" in brand_filter:
    brand_filter = brands
if "Tất cả" in region_filter:
    region_filter = regions
if "Tất cả" in store_filter:
    store_filter = stores
if "Tất cả" in loaiCT_filter:
    loaiCT_filter = loaicts

# Lọc dữ liệu
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (
    df["Ngày"] <= pd.to_datetime(end_date)
)
mask &= df["Brand"].isin(brand_filter)
mask &= df["Region"].isin(region_filter)
mask &= df["Điểm_mua_hàng"].isin(store_filter)
mask &= df["LoaiCT"].isin(loaiCT_filter)

df_filtered = df[mask].copy()

st.subheader("📑 Dữ liệu đã lọc")
st.dataframe(df_filtered, width="stretch")

# =====================
# Gom dữ liệu theo tuần & tháng
# =====================
def summary_with_discount(df_in, freq, label):
    if df_in.empty:
        st.markdown(f"### 📊 Doanh thu theo {label}")
        st.info("Không có dữ liệu sau khi lọc.")
        return pd.DataFrame()

    d = (
        df_in.set_index("Ngày")[["Tổng_Gross", "Tổng_Net"]]
        .resample(freq)
        .sum()
        .reset_index()
    )
    d["Tỷ_lệ_CK (%)"] = np.where(
        d["Tổng_Gross"] > 0,
        (1 - d["Tổng_Net"] / d["Tổng_Gross"]) * 100,
        0,
    )
    d["%_change_truoc"] = d["Tổng_Gross"].pct_change() * 100
    d["%_change_sau"] = d["Tổng_Net"].pct_change() * 100

    st.markdown(f"### 📊 Doanh thu theo {label}")
    st.dataframe(d, width="stretch")

    fig = px.line(
        d,
        x="Ngày",
        y=["Tổng_Gross", "Tổng_Net"],
        markers=True,
        title=f"Doanh thu theo {label}",
    )
    fig.update_layout(yaxis_title="VNĐ")
    st.plotly_chart(fig, use_container_width=True)

    return d


col1, col2 = st.columns(2)
with col1:
    df_week = summary_with_discount(df_filtered, "W", "Tuần")
with col2:
    df_month = summary_with_discount(df_filtered, "M", "Tháng")

# =====================
# Báo cáo theo Region
# =====================
st.subheader("🌍 Doanh thu theo Region")

if df_filtered.empty:
    st.info("Không có dữ liệu sau khi lọc.")
    df_region = pd.DataFrame()
    df_region_latest = pd.DataFrame()
else:
    if analysis_type == "Tuần":
        df_region = df_filtered.copy()
        df_region["Year"] = df_region["Ngày"].dt.year
        df_region["Period"] = df_region["Ngày"].dt.isocalendar().week
    elif analysis_type == "Tháng":
        df_region = df_filtered.copy()
        df_region["Year"] = df_region["Ngày"].dt.year
        df_region["Period"] = df_region["Ngày"].dt.month
    else:
        df_region = df_filtered.copy()
        df_region["Year"] = df_region["Ngày"].dt.year
        df_region["Period"] = df_region["Ngày"].dt.month

    grouped_region = (
        df_region.groupby(["Year", "Period", "Region"], as_index=False)[
            ["Tổng_Gross", "Tổng_Net"]
        ]
        .sum()
    )

    grouped_region["Tỷ_lệ_CK (%)"] = np.where(
        grouped_region["Tổng_Gross"] > 0,
        (1 - grouped_region["Tổng_Net"] / grouped_region["Tổng_Gross"]) * 100,
        0,
    )

    grouped_region = grouped_region.sort_values(["Region", "Year", "Period"])
    grouped_region["Prev"] = grouped_region.groupby("Region")["Tổng_Net"].shift(1)
    grouped_region["Change%"] = (
        (grouped_region["Tổng_Net"] - grouped_region["Prev"])
        / grouped_region["Prev"]
        * 100
    ).round(2)

    latest_year = grouped_region["Year"].max()
    latest_period = grouped_region.loc[
        grouped_region["Year"] == latest_year, "Period"
    ].max()
    df_region_latest = grouped_region[
        (grouped_region["Year"] == latest_year)
        & (grouped_region["Period"] == latest_period)
    ]

    def style_change(val):
        if pd.isna(val):
            return ""
        arrow = "↑" if val > 0 else "↓" if val < 0 else "-"
        return f"{arrow} {val:.2f}%"

    styled_df = df_region_latest[
        ["Region", "Tổng_Gross", "Tổng_Net", "Tỷ_lệ_CK (%)", "Prev", "Change%"]
    ].copy()
    styled_df["Change%"] = df_region_latest["Change%"].apply(style_change)

    st.data_editor(
        styled_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn(
                "Doanh thu trước CK", format="%.0f"
            ),
            "Tổng_Net": st.column_config.NumberColumn(
                "Doanh thu sau CK", format="%.0f"
            ),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                "Tỷ lệ CK (%)", format="%.2f %%"
            ),
            "Prev": st.column_config.NumberColumn(
                "Doanh thu kỳ trước", format="%.0f"
            ),
            "Change%": st.column_config.TextColumn("Tăng/giảm (%)"),
        },
    )

    df_region_melt = df_region_latest.melt(
        id_vars="Region",
        value_vars=["Tổng_Gross", "Tổng_Net"],
        var_name="Loại doanh thu",
        value_name="Doanh thu",
    )

    fig_r = px.bar(
        df_region_melt,
        x="Region",
        y="Doanh thu",
        color="Loại doanh thu",
        barmode="group",
        title="Doanh thu theo Region",
    )
    st.plotly_chart(fig_r, use_container_width=True)

# =====================
# Báo cáo theo Điểm mua hàng
# =====================
st.subheader("🏪 Doanh thu theo Điểm mua hàng")

if not df_filtered.empty:
    if analysis_type == "Ngày":
        df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.date
    elif analysis_type == "Tuần":
        df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.strftime("%G-W%V")
    elif analysis_type == "Tháng":
        df_filtered["Thời_gian"] = df_filtered["Ngày"].dt.to_period("M").astype(str)
    else:
        df_filtered["Thời_gian"] = "Tất cả"

    df_store = (
        df_filtered.groupby(["Thời_gian", "Điểm_mua_hàng"])[
            ["Tổng_Gross", "Tổng_Net"]
        ]
        .sum()
        .reset_index()
    )
    df_store["Tỷ_lệ_CK (%)"] = np.where(
        df_store["Tổng_Gross"] > 0,
        (1 - df_store["Tổng_Net"] / df_store["Tổng_Gross"]) * 100,
        0,
    )
    df_store = df_store.sort_values(by="Tổng_Net", ascending=False)

    st.data_editor(
        df_store,
        width="stretch",
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn(format="%.0f"),
            "Tổng_Net": st.column_config.NumberColumn(format="%.0f"),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(format="%.2f %%"),
        },
    )

    df_store_melt = df_store.melt(
        id_vars=["Thời_gian", "Điểm_mua_hàng"],
        value_vars=["Tổng_Gross", "Tổng_Net"],
        var_name="Loại doanh thu",
        value_name="Doanh thu",
    )

    fig_store = px.bar(
        df_store_melt,
        x="Doanh thu",
        y="Điểm_mua_hàng",
        color="Loại doanh thu",
        orientation="h",
        barmode="group",
        title="Doanh thu theo Điểm mua hàng (sắp xếp giảm dần)",
        height=900,
    )
    fig_store.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_store, use_container_width=True)
else:
    df_store = pd.DataFrame()

# =====================
# Top 10 / Bottom 10 điểm mua hàng
# =====================
st.subheader("🏆 Top 10 Điểm mua hàng có Doanh thu cao nhất")

if df_filtered.empty:
    st.info("Không có dữ liệu sau khi lọc.")
    df_top10 = pd.DataFrame()
    df_bottom10 = pd.DataFrame()
else:
    if analysis_type == "Tuần":
        df_group = df_filtered.copy()
        df_group["Year"] = df_group["Ngày"].dt.year
        df_group["Period"] = df_group["Ngày"].dt.isocalendar().week
    elif analysis_type == "Tháng":
        df_group = df_filtered.copy()
        df_group["Year"] = df_group["Ngày"].dt.year
        df_group["Period"] = df_group["Ngày"].dt.month
    else:
        df_group = df_filtered.copy()
        df_group["Year"] = df_group["Ngày"].dt.year
        df_group["Period"] = df_group["Ngày"].dt.month

    grouped = (
        df_group.groupby(["Year", "Period", "Điểm_mua_hàng"], as_index=False)[
            ["Tổng_Gross", "Tổng_Net"]
        ]
        .sum()
    )
    grouped["Tỷ_lệ_CK (%)"] = np.where(
        grouped["Tổng_Gross"] > 0,
        (1 - grouped["Tổng_Net"] / grouped["Tổng_Gross"]) * 100,
        0,
    )

    grouped = grouped.sort_values(["Điểm_mua_hàng", "Year", "Period"])
    grouped["Prev"] = grouped.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
    grouped["Change%"] = (
        (grouped["Tổng_Net"] - grouped["Prev"]) / grouped["Prev"] * 100
    ).round(2)

    latest_year = grouped["Year"].max()
    latest_period = grouped.loc[grouped["Year"] == latest_year, "Period"].max()
    df_latest = grouped[
        (grouped["Year"] == latest_year) & (grouped["Period"] == latest_period)
    ]

    df_top10 = df_latest.sort_values(by="Tổng_Net", ascending=False).head(10)

    st.data_editor(
        df_top10,
        width="stretch",
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn(
                "Doanh thu trước CK", format="%.0f"
            ),
            "Tổng_Net": st.column_config.NumberColumn(
                "Doanh thu sau CK", format="%.0f"
            ),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                "Tỷ lệ CK (%)", format="%.2f %%"
            ),
            "Prev": st.column_config.NumberColumn(
                "Doanh thu kỳ trước", format="%.0f"
            ),
            "Change%": st.column_config.NumberColumn(
                "Tăng/giảm (%)", format="%.2f %%"
            ),
        },
    )

    st.subheader("📉 Top 10 Điểm mua hàng có Doanh thu thấp nhất")

    df_bottom10 = df_latest.sort_values(by="Tổng_Net", ascending=True).head(10)

    st.data_editor(
        df_bottom10,
        width="stretch",
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn(
                "Doanh thu trước CK", format="%.0f"
            ),
            "Tổng_Net": st.column_config.NumberColumn(
                "Doanh thu sau CK", format="%.0f"
            ),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                "Tỷ lệ CK (%)", format="%.2f %%"
            ),
            "Prev": st.column_config.NumberColumn(
                "Doanh thu kỳ trước", format="%.0f"
            ),
            "Change%": st.column_config.NumberColumn(
                "Tăng/giảm (%)", format="%.2f %%"
            ),
        },
    )

# =====================
# 💎 Top % khách hàng theo doanh thu
# =====================
st.subheader(
    f"💎 Top {top_percent_option}% Khách hàng theo "
    f"{'Doanh thu sau CK' if doanh_thu_type == 'Tổng_Net' else 'Doanh thu trước CK'}"
)

if df_filtered.empty:
    st.info("Không có dữ liệu sau khi lọc.")
    df_top_customers_percent = pd.DataFrame()
else:
    df_top_customers = (
        df_filtered.groupby("Số_điện_thoại", as_index=False)[
            ["Tổng_Gross", "Tổng_Net"]
        ]
        .sum()
    )

    df_top_customers["Tỷ_lệ_CK (%)"] = np.where(
        df_top_customers["Tổng_Gross"] > 0,
        (1 - df_top_customers["Tổng_Net"] / df_top_customers["Tổng_Gross"]) * 100,
        0,
    )

    df_top_customers = df_top_customers.sort_values(
        by=doanh_thu_type, ascending=False
    )

    top_n = max(1, int(len(df_top_customers) * top_percent_option / 100))
    df_top_customers_percent = df_top_customers.head(top_n)

    st.data_editor(
        df_top_customers_percent,
        width="stretch",
        hide_index=True,
        column_config={
            "Tổng_Gross": st.column_config.NumberColumn(
                "Doanh thu trước CK", format="%.0f"
            ),
            "Tổng_Net": st.column_config.NumberColumn(
                "Doanh thu sau CK", format="%.0f"
            ),
            "Tỷ_lệ_CK (%)": st.column_config.NumberColumn(
                "Tỷ lệ CK (%)", format="%.2f %%"
            ),
        },
    )

# =====================
# Xuất Excel
# =====================
def to_excel(df_dict):
    import io
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows

    output = io.BytesIO()
    wb = Workbook()

    for i, (sheet_name, d) in enumerate(df_dict.items()):
        if d is None or d.empty:
            continue

        if i == 0:
            ws = wb.active
            ws.title = sheet_name
        else:
            ws = wb.create_sheet(sheet_name)

        for r in dataframe_to_rows(d, index=False, header=True):
            ws.append(r)

    wb.save(output)
    return output.getvalue()


excel_file = to_excel(
    {
        "Du_lieu_loc": df_filtered,
        "Theo_Tuan": df_week,
        "Theo_Thang": df_month,
        "Theo_Region": df_region_latest,
        "Theo_Store": df_store,
        "Top10_Store": df_top10,
        "Bottom10_Store": df_bottom10,
        "TopKH_%": df_top_customers_percent,
    }
)

st.download_button(
    label="📥 Xuất dữ liệu ra Excel",
    data=excel_file,
    file_name="bao_cao_doanh_thu.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
