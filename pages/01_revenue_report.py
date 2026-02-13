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
# PAGE
# =====================================================
st.set_page_config(page_title="📈 Báo cáo Doanh thu", layout="wide")
st.title("📈 Báo cáo Doanh thu")

df = get_active_data()
st.sidebar.caption("🔎 Đang dùng nguồn: **{}**".format(st.session_state.get("active_source", "default")))

if df is None or df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích.")
    st.stop()

# =====================================================
# SIDEBAR FILTER
# =====================================================
with st.sidebar:
    st.header("🎛 Bộ lọc dữ liệu")

    if st.button("🔄 Reset bộ lọc (Revenue)", width="stretch"):
        reset_by_prefix(REV)

    if REV + "time_grain" not in st.session_state:
        st.session_state[REV + "time_grain"] = "Ngày"

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key=REV + "time_grain",
    )

    if time_grain == "Tuần":
        if REV + "week_start" not in st.session_state:
            st.session_state[REV + "week_start"] = "Thứ 2"
        rev_week_label = st.selectbox(
            "Tuần bắt đầu từ thứ",
            list(WEEKDAY_MAP.keys()),
            key=REV + "week_start",
        )
        week_start = WEEKDAY_MAP[rev_week_label]
    else:
        week_start = 0

    if REV + "start_date" not in st.session_state:
        st.session_state[REV + "start_date"] = pd.to_datetime(df["Ngày"]).min().date()
    if REV + "end_date" not in st.session_state:
        st.session_state[REV + "end_date"] = pd.to_datetime(df["Ngày"]).max().date()

    start_date = st.date_input("Từ ngày", key=REV + "start_date")
    end_date = st.date_input("Đến ngày", key=REV + "end_date")

    loaict = ms_all(REV + "loaict", "LoaiCT", df["LoaiCT"] if "LoaiCT" in df.columns else [])
    brand = ms_all(REV + "brand", "Brand", df["Brand"] if "Brand" in df.columns else [])

    df_b = df[df["Brand"].isin(brand)] if ("Brand" in df.columns and brand) else df
    region = ms_all(REV + "region", "Region", df_b["Region"] if "Region" in df_b.columns else [])

    df_br = df_b[df_b["Region"].isin(region)] if ("Region" in df_b.columns and region) else df_b
    store = ms_all(REV + "store", "Điểm mua hàng", df_br["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df_br.columns else [])

    checksdt = ms_all(
        REV + "checksdt",
        "Trạng_thái_số_điện_thoại",
        df["Trạng_thái_số_điện_thoại"] if "Trạng_thái_số_điện_thoại" in df.columns else [],
    )

    checkten = ms_all(
        REV + "checkten",
        "Kiểm_tra_tên",
        df["Kiểm_tra_tên"] if "Kiểm_tra_tên" in df.columns else [],
    )

# =====================================================
# APPLY FILTER
# =====================================================
dmin = pd.to_datetime(start_date)
dmax = pd.to_datetime(end_date)

mask = (df["Ngày"] >= dmin) & (df["Ngày"] <= dmax)
if "LoaiCT" in df.columns and loaict: mask &= df["LoaiCT"].isin(loaict)
if "Brand" in df.columns and brand: mask &= df["Brand"].isin(brand)
if "Region" in df.columns and region: mask &= df["Region"].isin(region)
if "Điểm_mua_hàng" in df.columns and store: mask &= df["Điểm_mua_hàng"].isin(store)
if "Trạng_thái_số_điện_thoại" in df.columns and checksdt: mask &= df["Trạng_thái_số_điện_thoại"].isin(checksdt)
if "Kiểm_tra_tên" in df.columns and checkten: mask &= df["Kiểm_tra_tên"].isin(checkten)

df_f = df.loc[mask].copy()
if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# TIME KEY
# =====================================================
def add_time_key(df_in: pd.DataFrame, grain: str):
    out = df_in.copy()

    if grain == "Ngày":
        out["Label"] = out["Ngày"].dt.normalize()
        gcols = ["Label"]
        return out, gcols

    if grain == "Tuần":
        out["Label"] = week_anchor(out["Ngày"], week_start)
        iso = out["Label"].dt.isocalendar()
        out["Year"] = iso["year"].astype(int)
        out["Key"] = iso["week"].astype(int)
        gcols = ["Year", "Key", "Label"]
        return out, gcols

    if grain == "Tháng":
        out["Label"] = out["Ngày"].dt.to_period("M").dt.to_timestamp()
        out["Year"] = out["Ngày"].dt.year.astype(int)
        out["Key"] = out["Ngày"].dt.month.astype(int)
        gcols = ["Year", "Key", "Label"]
        return out, gcols

    # Quý
    out["Label"] = out["Ngày"].dt.to_period("Q").dt.to_timestamp()
    out["Year"] = out["Ngày"].dt.year.astype(int)
    out["Key"] = out["Ngày"].dt.quarter.astype(int)
    gcols = ["Year", "Key", "Label"]
    return out, gcols


# =====================================================
# SUMMARY
# =====================================================
df_tmp, gcols = add_time_key(df_f, time_grain)

summary = (
    df_tmp.groupby(gcols, observed=True)
    .agg(
        Tổng_Gross=("Tổng_Gross", "sum"),
        Tổng_Net=("Tổng_Net", "sum"),
        Số_KH=("Số_điện_thoại", "nunique"),
        Số_đơn_hàng=("Số_CT", "nunique"),
    )
    .reset_index()
    .sort_values("Label")
)

summary["Tỷ_lệ_CK (%)"] = np.where(summary["Tổng_Gross"] > 0, (1 - summary["Tổng_Net"] / summary["Tổng_Gross"]) * 100, 0)
summary["Prev_Tổng_Net"] = summary["Tổng_Net"].shift(1)
summary["Change%"] = np.where(summary["Prev_Tổng_Net"] > 0, (summary["Tổng_Net"] - summary["Prev_Tổng_Net"]) / summary["Prev_Tổng_Net"] * 100, np.nan)

# Label hiển thị
summary_show = summary.copy()
if time_grain == "Ngày":
    summary_show["Kỳ"] = pd.to_datetime(summary_show["Label"]).dt.strftime("%Y-%m-%d")
elif time_grain == "Tuần":
    summary_show["Kỳ"] = "Tuần " + summary_show["Key"].astype(int).astype(str).str.zfill(2) + "/" + summary_show["Year"].astype(int).astype(str)
elif time_grain == "Tháng":
    summary_show["Kỳ"] = summary_show["Year"].astype(int).astype(str) + "-" + summary_show["Key"].astype(int).astype(str).str.zfill(2)
else:
    summary_show["Kỳ"] = "Q" + summary_show["Key"].astype(int).astype(str) + " " + summary_show["Year"].astype(int).astype(str)

for c in ["Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Prev_Tổng_Net"]:
    summary_show[c] = summary_show[c].apply(fmt_int)
summary_show["Tỷ_lệ_CK (%)"] = summary_show["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v, 2))
summary_show["Change%"] = summary_show["Change%"].apply(lambda v: fmt_pct(v, 2, with_sign=True))

st.subheader("📊 Tổng hợp doanh thu")
st.dataframe(
    summary_show[["Kỳ","Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Tỷ_lệ_CK (%)","Prev_Tổng_Net","Change%"]],
    width="stretch",
    hide_index=True
)

fig = px.line(summary, x="Label", y=["Tổng_Gross","Tổng_Net"], markers=True, title=f"Doanh thu theo {time_grain}")
st.plotly_chart(fig, use_container_width=True)  # plotly vẫn dùng ok

# =====================================================
# TOP/BOTTOM STORE (GIỮ Prev + Change% + THÊM SỐ_ĐƠN_HÀNG)
# =====================================================
st.subheader("🏪 Top/Bottom 10 Điểm mua hàng")
st.markdown("### 🔍 Chọn kỳ để xem Top/Bottom")

# periods label list
period_labels = summary_show["Kỳ"].tolist()
sel = st.selectbox("Chọn kỳ", period_labels, index=len(period_labels)-1, key=REV + "store_period")

# map back to selected Label timestamp
sel_label_ts = summary.loc[summary_show["Kỳ"] == sel, "Label"].iloc[0]

df_store = df_tmp.copy()
# lọc theo kỳ
df_store = df_store[df_store["Label"] == sel_label_ts].copy()

# store group
store_g = (
    df_store.groupby("Điểm_mua_hàng", observed=True, dropna=False)
    .agg(
        Tổng_Gross=("Tổng_Gross","sum"),
        Tổng_Net=("Tổng_Net","sum"),
        Số_đơn_hàng=("Số_CT","nunique"),
    )
    .reset_index()
)

store_g["Tỷ_lệ_CK (%)"] = np.where(store_g["Tổng_Gross"]>0, (1 - store_g["Tổng_Net"]/store_g["Tổng_Gross"])*100, 0)

# ✅ Prev Net & Change% theo cửa hàng: tính dựa trên ALL kỳ trước đó
store_all = (
    df_tmp.groupby(["Điểm_mua_hàng"] + gcols, observed=True, dropna=False)
    .agg(Tổng_Net=("Tổng_Net","sum"))
    .reset_index()
    .sort_values(["Điểm_mua_hàng","Label"])
)
store_all["Prev_Tổng_Net"] = store_all.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
store_all["Change%"] = np.where(
    store_all["Prev_Tổng_Net"]>0,
    (store_all["Tổng_Net"]-store_all["Prev_Tổng_Net"])/store_all["Prev_Tổng_Net"]*100,
    np.nan
)

# join prev/change vào kỳ đang xem
store_key = store_all[store_all["Label"] == sel_label_ts][["Điểm_mua_hàng","Prev_Tổng_Net","Change%"]]
store_g = store_g.merge(store_key, on="Điểm_mua_hàng", how="left")

top10 = store_g.sort_values("Tổng_Net", ascending=False).head(10).copy()
bot10 = store_g.sort_values("Tổng_Net", ascending=True).head(10).copy()

def fmt_store_table(d):
    out = d.copy()
    out.insert(0, "Kỳ", sel)
    for c in ["Tổng_Gross","Tổng_Net","Số_đơn_hàng","Prev_Tổng_Net"]:
        out[c] = out[c].apply(fmt_int)
    out["Tỷ_lệ_CK (%)"] = out["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v,2))
    out["Change%"] = out["Change%"].apply(lambda v: fmt_pct(v,2,with_sign=True))
    return out[["Kỳ","Điểm_mua_hàng","Tổng_Gross","Tổng_Net","Số_đơn_hàng","Tỷ_lệ_CK (%)","Prev_Tổng_Net","Change%"]]

colA, colB = st.columns(2)
with colA:
    st.markdown("### 🏆 Top 10 Điểm mua hàng")
    st.dataframe(fmt_store_table(top10), width="stretch", hide_index=True)

with colB:
    st.markdown("### 📉 Bottom 10 Điểm mua hàng")
    st.dataframe(fmt_store_table(bot10), width="stretch", hide_index=True)
