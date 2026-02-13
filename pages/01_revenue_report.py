# pages/01_revenue_report.py
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from load_data import get_active_data

# =====================================================
# FORMAT
# =====================================================
def fmt_int(x):
    if pd.isna(x):
        return ""
    try:
        return f"{float(x):,.0f}"
    except:
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
    except:
        return ""

# =====================================================
# WEEK
# =====================================================
WEEKDAY_MAP = {
    "Thứ 2": 0, "Thứ 3": 1, "Thứ 4": 2, "Thứ 5": 3,
    "Thứ 6": 4, "Thứ 7": 5, "Chủ nhật": 6
}

def week_anchor(dt, start):
    return (dt - pd.to_timedelta((dt.dt.weekday - start) % 7, unit="D")).dt.normalize()

# =====================================================
# FILTER
# =====================================================
REV = "rev_"

def reset_by_prefix(prefix):
    for k in list(st.session_state.keys()):
        if k.startswith(prefix):
            del st.session_state[k]
    st.rerun()

def ms_all(key, label, options):
    opts = sorted(pd.Series(options).dropna().astype(str).unique().tolist())
    ui = ["All"] + opts

    if key not in st.session_state:
        st.session_state[key] = ["All"]

    selected = st.multiselect(label, ui, key=key)

    if (not selected) or ("All" in selected):
        return opts
    return selected

# =====================================================
# PAGE
# =====================================================
st.set_page_config(page_title="Revenue Report", layout="wide")
st.title("📈 Báo cáo Doanh thu")

df = get_active_data()

if df.empty:
    st.warning("Không có dữ liệu")
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.header("🎛 Bộ lọc")

    if st.button("🔄 Reset", use_container_width=True):
        reset_by_prefix(REV)

    grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key=REV + "grain"
    )

    if grain == "Tuần":
        wlabel = st.selectbox(
            "Tuần bắt đầu",
            list(WEEKDAY_MAP.keys()),
            key=REV + "weekstart"
        )
        week_start = WEEKDAY_MAP[wlabel]
    else:
        week_start = 0

    if REV + "start" not in st.session_state:
        st.session_state[REV + "start"] = df["Ngày"].min().date()
    if REV + "end" not in st.session_state:
        st.session_state[REV + "end"] = df["Ngày"].max().date()

    start = st.date_input("Từ ngày", key=REV + "start")
    end = st.date_input("Đến ngày", key=REV + "end")

    brand = ms_all(REV + "brand", "Brand", df["Brand"] if "Brand" in df.columns else [])
    region = ms_all(REV + "region", "Region", df["Region"] if "Region" in df.columns else [])
    store = ms_all(REV + "store", "Cửa hàng", df["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df.columns else [])

# =====================================================
# APPLY FILTER
# =====================================================
mask = (df["Ngày"] >= pd.to_datetime(start)) & (df["Ngày"] <= pd.to_datetime(end))
if "Brand" in df.columns: mask &= df["Brand"].isin(brand)
if "Region" in df.columns: mask &= df["Region"].isin(region)
if "Điểm_mua_hàng" in df.columns: mask &= df["Điểm_mua_hàng"].isin(store)

df_f = df.loc[mask].copy()

if df_f.empty:
    st.warning("Không có dữ liệu sau filter")
    st.stop()

# =====================================================
# TIME KEY (Label)
# =====================================================
if grain == "Ngày":
    df_f["Label"] = df_f["Ngày"].dt.normalize()
elif grain == "Tuần":
    df_f["Label"] = week_anchor(df_f["Ngày"], week_start)
elif grain == "Tháng":
    df_f["Label"] = df_f["Ngày"].dt.to_period("M").dt.to_timestamp()
else:
    df_f["Label"] = df_f["Ngày"].dt.to_period("Q").dt.to_timestamp()

# =====================================================
# CACHE SUMMARY
# =====================================================
@st.cache_data(show_spinner=False)
def build_summary(data):
    g = (
        data.groupby("Label", observed=True)
        .agg(
            Tổng_Gross=("Tổng_Gross","sum"),
            Tổng_Net=("Tổng_Net","sum"),
            Số_KH=("Số_điện_thoại","nunique"),
            Số_đơn_hàng=("Số_CT","nunique"),
        )
        .reset_index()
        .sort_values("Label")
    )
    g["Tỷ_lệ_CK (%)"] = np.where(g["Tổng_Gross"]>0,(1-g["Tổng_Net"]/g["Tổng_Gross"])*100,0)
    g["Prev_Tổng_Net"] = g["Tổng_Net"].shift(1)
    g["Change%"] = np.where(
        g["Prev_Tổng_Net"]>0,
        (g["Tổng_Net"]-g["Prev_Tổng_Net"])/g["Prev_Tổng_Net"]*100,
        np.nan
    )
    return g

summary = build_summary(df_f)

# =====================================================
# SHOW SUMMARY
# =====================================================
st.subheader("📊 Tổng hợp")

show = summary.copy()

if grain == "Ngày":
    show["Kỳ"] = show["Label"].dt.strftime("%Y-%m-%d")
elif grain == "Tuần":
    iso = show["Label"].dt.isocalendar()
    show["Kỳ"] = "Tuần " + iso["week"].astype(str).str.zfill(2) + "/" + iso["year"].astype(str)
elif grain == "Tháng":
    show["Kỳ"] = show["Label"].dt.to_period("M").astype(str)
else:
    show["Kỳ"] = show["Label"].dt.to_period("Q").astype(str)

for c in ["Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Prev_Tổng_Net"]:
    show[c] = show[c].apply(fmt_int)

for c in ["Tỷ_lệ_CK (%)","Change%"]:
    show[c] = show[c].apply(lambda v: fmt_pct(v,2,with_sign=(c=="Change%")))

st.dataframe(
    show[["Kỳ","Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Tỷ_lệ_CK (%)","Prev_Tổng_Net","Change%"]],
    width="stretch",
    hide_index=True
)

# =====================================================
# CHART
# =====================================================
fig = px.line(summary, x="Label", y=["Tổng_Gross","Tổng_Net"], markers=True)
st.plotly_chart(fig, use_container_width=True)

# =====================================================
# REGION
# =====================================================
st.subheader("🌍 Theo Region")

if "Region" in df_f.columns:
    reg = (
        df_f.groupby(["Label","Region"], observed=True)
        .agg(
            Tổng_Gross=("Tổng_Gross","sum"),
            Tổng_Net=("Tổng_Net","sum"),
            Số_KH=("Số_điện_thoại","nunique"),
            Số_đơn_hàng=("Số_CT","nunique"),
        )
        .reset_index()
        .sort_values(["Region","Label"])
    )

    reg["Tỷ_lệ_CK (%)"] = np.where(reg["Tổng_Gross"]>0,(1-reg["Tổng_Net"]/reg["Tổng_Gross"])*100,0)
    reg["Prev_Tổng_Net"] = reg.groupby("Region")["Tổng_Net"].shift(1)
    reg["Change%"] = np.where(
        reg["Prev_Tổng_Net"]>0,
        (reg["Tổng_Net"]-reg["Prev_Tổng_Net"])/reg["Prev_Tổng_Net"]*100,
        np.nan
    )

    periods = summary["Label"].tolist()
    sel = st.selectbox("Chọn kỳ", periods, index=len(periods)-1, key=REV+"reg")

    reg = reg[reg["Label"]==sel].sort_values("Tổng_Net", ascending=False)

    if grain == "Ngày":
        ky = sel.strftime("%Y-%m-%d")
    elif grain == "Tuần":
        iso = sel.isocalendar()
        ky = f"Tuần {iso.week:02d}/{iso.year}"
    elif grain == "Tháng":
        ky = sel.to_period("M")
    else:
        ky = sel.to_period("Q")

    reg["Kỳ"] = ky

    for c in ["Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Prev_Tổng_Net"]:
        reg[c] = reg[c].apply(fmt_int)
    for c in ["Tỷ_lệ_CK (%)","Change%"]:
        reg[c] = reg[c].apply(lambda v: fmt_pct(v,2,with_sign=(c=="Change%")))

    st.dataframe(
        reg[["Kỳ","Region","Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Tỷ_lệ_CK (%)","Prev_Tổng_Net","Change%"]],
        width="stretch",
        hide_index=True
    )

# =====================================================
# TOP / BOTTOM STORE
# =====================================================
st.subheader("🏪 Top / Bottom 10")

if "Điểm_mua_hàng" in df_f.columns:
    store = (
        df_f.groupby(["Label","Điểm_mua_hàng"], observed=True)
        .agg(
            Tổng_Gross=("Tổng_Gross","sum"),
            Tổng_Net=("Tổng_Net","sum"),
            Số_đơn_hàng=("Số_CT","nunique"),
        )
        .reset_index()
        .sort_values(["Điểm_mua_hàng","Label"])
    )

    store["Prev_Tổng_Net"] = store.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
    store["Change%"] = np.where(
        store["Prev_Tổng_Net"]>0,
        (store["Tổng_Net"]-store["Prev_Tổng_Net"])/store["Prev_Tổng_Net"]*100,
        np.nan
    )

    periods = summary["Label"].tolist()
    sel = st.selectbox("Chọn kỳ ", periods, index=len(periods)-1, key=REV+"store")

    s = store[store["Label"]==sel].copy()

    top = s.sort_values("Tổng_Net", ascending=False).head(10)
    bottom = s.sort_values("Tổng_Net", ascending=True).head(10)

    for df_show in [top, bottom]:
        for c in ["Tổng_Gross","Tổng_Net","Số_đơn_hàng","Prev_Tổng_Net"]:
            df_show[c] = df_show[c].apply(fmt_int)
        df_show["Change%"] = df_show["Change%"].apply(lambda v: fmt_pct(v,2,True))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🏆 Top 10")
        st.dataframe(top[["Điểm_mua_hàng","Tổng_Gross","Tổng_Net","Số_đơn_hàng","Prev_Tổng_Net","Change%"]], width="stretch", hide_index=True)
    with col2:
        st.markdown("### 📉 Bottom 10")
        st.dataframe(bottom[["Điểm_mua_hàng","Tổng_Gross","Tổng_Net","Số_đơn_hàng","Prev_Tổng_Net","Change%"]], width="stretch", hide_index=True)
