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
    if pd.isna(x): return ""
    try: return f"{float(x):,.0f}"
    except: return ""

def fmt_pct(x, decimals=2, with_sign=False):
    if pd.isna(x): return ""
    try:
        v = float(x)
        s = f"{v:,.{decimals}f}%"
        if with_sign and v > 0:
            s = "+" + s
        return s
    except:
        return ""

# =====================================================
# CLEAN + OPTIMIZE
# =====================================================
def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if "Ngày" in df.columns:
        df["Ngày"] = pd.to_datetime(df["Ngày"], errors="coerce")
        df = df.dropna(subset=["Ngày"])
    return df

def normalize_strings(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
            df.loc[df[c].isin(["nan", "None", "NaT"]), c] = np.nan
    return df

def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    cat_cols = ["LoaiCT","Brand","Region","Điểm_mua_hàng","Kiểm_tra_tên","Trạng_thái_số_điện_thoại"]
    df = normalize_strings(df, cat_cols + ["Số_điện_thoại"])
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].astype("category")
    for c in ["Tổng_Gross","Tổng_Net"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Số_điện_thoại" in df.columns:
        df["Số_điện_thoại"] = df["Số_điện_thoại"].astype(str)
    return df

# =====================================================
# WEEK
# =====================================================
WEEKDAY_MAP = {
    "Thứ 2": 0, "Thứ 3": 1, "Thứ 4": 2, "Thứ 5": 3,
    "Thứ 6": 4, "Thứ 7": 5, "Chủ nhật": 6
}

def week_anchor(dt: pd.Series, week_start: int) -> pd.Series:
    d = pd.to_datetime(dt)
    return (d - pd.to_timedelta((d.dt.weekday - week_start) % 7, unit="D")).dt.normalize()

# =====================================================
# FILTER STATE (KHÔNG RESET KHI ĐỔI TRANG)
# =====================================================
REV = "rev_"

def init_defaults(df: pd.DataFrame):
    st.session_state.setdefault(REV + "time_grain", "Ngày")
    st.session_state.setdefault(REV + "week_start", "Thứ 2")
    st.session_state.setdefault(REV + "start_date", df["Ngày"].min().date())
    st.session_state.setdefault(REV + "end_date", df["Ngày"].max().date())

    for k in ["loaict","brand","region","store","checksdt","checkten"]:
        st.session_state.setdefault(REV + k, ["All"])

def ms_all(key: str, label: str, options, all_label="All"):
    opts = pd.Series(list(options)).dropna().astype(str).str.strip()
    opts = sorted(opts.unique().tolist())
    ui = [all_label] + opts

    # sanitize state (NHƯNG KHÔNG TỰ GÁN LẠI DEFAULT TRỪ KHI RỖNG/INVALID)
    cur = st.session_state.get(key, [all_label])
    cur = [x for x in cur if str(x).strip() in ui]
    if not cur:
        st.session_state[key] = [all_label]

    st.multiselect(label, options=ui, key=key)
    selected = st.session_state.get(key, [all_label])

    if (not selected) or (all_label in selected):
        return opts
    return [x for x in selected if x in opts]

# =====================================================
# PAGE
# =====================================================
st.set_page_config(page_title="📈 Báo cáo Doanh thu", layout="wide")
st.title("📈 Báo cáo Doanh thu")

df = get_active_data()
df = ensure_datetime(df)
df = optimize_dtypes(df)

if df.empty:
    st.warning("⚠ Không có dữ liệu để phân tích.")
    st.stop()

init_defaults(df)

# =====================================================
# SIDEBAR (TUYỆT ĐỐI KHÔNG DÙNG value=)
# =====================================================
with st.sidebar:
    st.header("🎛 Bộ lọc (Revenue)")

    time_grain = st.selectbox(
        "Phân tích theo",
        ["Ngày", "Tuần", "Tháng", "Quý"],
        key=REV + "time_grain",
    )

    if time_grain == "Tuần":
        st.selectbox("Tuần bắt đầu từ thứ", list(WEEKDAY_MAP.keys()), key=REV + "week_start")

    st.date_input("Từ ngày", key=REV + "start_date")
    st.date_input("Đến ngày", key=REV + "end_date")

    start_date = st.session_state[REV + "start_date"]
    end_date   = st.session_state[REV + "end_date"]

    loaict = ms_all(REV + "loaict", "LoaiCT", df["LoaiCT"] if "LoaiCT" in df.columns else [])
    brand  = ms_all(REV + "brand", "Brand", df["Brand"] if "Brand" in df.columns else [])

    df_b = df[df["Brand"].isin(brand)] if ("Brand" in df.columns and brand) else df.iloc[0:0]
    region = ms_all(REV + "region", "Region", df_b["Region"] if "Region" in df_b.columns else [])

    df_br = df_b[df_b["Region"].isin(region)] if ("Region" in df_b.columns and region) else df_b.iloc[0:0]
    store  = ms_all(REV + "store", "Điểm mua hàng", df_br["Điểm_mua_hàng"] if "Điểm_mua_hàng" in df_br.columns else [])

    checksdt = ms_all(
        REV + "checksdt",
        "Trạng_thái_số_điện_thoại",
        df["Trạng_thái_số_điện_thoại"] if "Trạng_thái_số_điện_thoại" in df.columns else []
    )
    checkten = ms_all(
        REV + "checkten",
        "Kiểm_tra_tên",
        df["Kiểm_tra_tên"] if "Kiểm_tra_tên" in df.columns else []
    )

week_start = WEEKDAY_MAP.get(st.session_state.get(REV + "week_start", "Thứ 2"), 0)

# =====================================================
# APPLY FILTER (chỉ lấy cột cần)
# =====================================================
mask = (df["Ngày"] >= pd.to_datetime(start_date)) & (df["Ngày"] <= pd.to_datetime(end_date))
if "LoaiCT" in df.columns: mask &= df["LoaiCT"].isin(loaict)
if "Brand" in df.columns:  mask &= df["Brand"].isin(brand)
if "Region" in df.columns: mask &= df["Region"].isin(region)
if "Điểm_mua_hàng" in df.columns: mask &= df["Điểm_mua_hàng"].isin(store)
if "Trạng_thái_số_điện_thoại" in df.columns: mask &= df["Trạng_thái_số_điện_thoại"].isin(checksdt)
if "Kiểm_tra_tên" in df.columns: mask &= df["Kiểm_tra_tên"].isin(checkten)

need_cols = [c for c in ["Ngày","Region","Điểm_mua_hàng","Số_CT","Số_điện_thoại","Tổng_Gross","Tổng_Net"] if c in df.columns]
df_f = df.loc[mask, need_cols]

if df_f.empty:
    st.warning("⚠ Không có dữ liệu sau khi áp bộ lọc.")
    st.stop()

# =====================================================
# TIME KEY (vectorized)
# =====================================================
def add_time_key(df_in: pd.DataFrame, grain: str):
    d = df_in.copy()
    if grain == "Ngày":
        d["Year"] = d["Ngày"].dt.year
        d["Key"]  = d["Ngày"].dt.normalize()
        gcols = ["Key"]
        d["Label"] = pd.to_datetime(d["Key"]).dt.strftime("%Y-%m-%d")

    elif grain == "Tuần":
        anch = week_anchor(d["Ngày"], week_start)
        iso = anch.dt.isocalendar()
        d["Year"] = iso["year"].astype(int)
        d["Key"]  = iso["week"].astype(int)
        gcols = ["Year","Key"]
        d["Label"] = "Tuần " + d["Key"].astype(str).str.zfill(2) + "/" + d["Year"].astype(str)

    elif grain == "Tháng":
        d["Year"] = d["Ngày"].dt.year
        d["Key"]  = d["Ngày"].dt.month.astype(int)
        gcols = ["Year","Key"]
        d["Label"] = d["Year"].astype(str) + "-" + d["Key"].astype(str).str.zfill(2)

    else:  # Quý
        d["Year"] = d["Ngày"].dt.year
        d["Key"]  = d["Ngày"].dt.quarter.astype(int)
        gcols = ["Year","Key"]
        d["Label"] = "Q" + d["Key"].astype(str) + " " + d["Year"].astype(str)

    return d, gcols

tmp, gcols = add_time_key(df_f, time_grain)

# =====================================================
# SUMMARY
# =====================================================
st.subheader("📊 Tổng hợp doanh thu")

summary = (
    tmp.groupby(gcols, observed=True)
    .agg(
        Label=("Label","first"),
        Tổng_Gross=("Tổng_Gross","sum"),
        Tổng_Net=("Tổng_Net","sum"),
        Số_KH=("Số_điện_thoại","nunique"),
        Số_đơn_hàng=("Số_CT","nunique"),
    )
    .reset_index()
    .sort_values(gcols)
)

summary["Tỷ_lệ_CK (%)"] = np.where(summary["Tổng_Gross"]!=0, (1 - summary["Tổng_Net"]/summary["Tổng_Gross"])*100, 0)
summary["Prev_Tổng_Net"] = summary["Tổng_Net"].shift(1)
summary["%_So_sánh_Tổng_Net"] = np.where(
    summary["Prev_Tổng_Net"]>0,
    (summary["Tổng_Net"]-summary["Prev_Tổng_Net"])/summary["Prev_Tổng_Net"]*100,
    np.nan
)

show = summary[["Label","Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Tỷ_lệ_CK (%)","Prev_Tổng_Net","%_So_sánh_Tổng_Net"]].copy()
show = show.rename(columns={"Label":"Kỳ"})
for c in ["Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Prev_Tổng_Net"]:
    show[c] = show[c].apply(fmt_int)
show["Tỷ_lệ_CK (%)"] = show["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v,2))
show["%_So_sánh_Tổng_Net"] = show["%_So_sánh_Tổng_Net"].apply(lambda v: fmt_pct(v,2,with_sign=True))

st.dataframe(show, use_container_width=True, hide_index=True)

fig = px.line(summary, x="Label", y=["Tổng_Gross","Tổng_Net"], markers=True, title=f"Doanh thu theo {time_grain}")
st.plotly_chart(fig, use_container_width=True)

# =====================================================
# REGION (chọn kỳ)
# =====================================================
st.subheader("🌍 Doanh thu theo Region")
if "Region" not in tmp.columns:
    st.info("Thiếu cột Region.")
else:
    reg = (
        tmp.groupby(["Region"] + gcols, observed=True)
        .agg(
            Label=("Label","first"),
            Tổng_Gross=("Tổng_Gross","sum"),
            Tổng_Net=("Tổng_Net","sum"),
            Số_KH=("Số_điện_thoại","nunique"),
            Số_đơn_hàng=("Số_CT","nunique"),
        )
        .reset_index()
    )
    reg["Tỷ_lệ_CK (%)"] = np.where(reg["Tổng_Gross"]!=0, (1 - reg["Tổng_Net"]/reg["Tổng_Gross"])*100, 0)

    # ✅ Prev_Tổng_Net & Change% theo từng Region (kỳ trước)
reg = reg.sort_values(["Region"] + gcols)  # quan trọng: đảm bảo đúng thứ tự thời gian
reg["Prev_Tổng_Net"] = reg.groupby("Region")["Tổng_Net"].shift(1)
reg["Change%"] = np.where(
    reg["Prev_Tổng_Net"] > 0,
    (reg["Tổng_Net"] - reg["Prev_Tổng_Net"]) / reg["Prev_Tổng_Net"] * 100,
    np.nan
)


    periods = summary["Label"].tolist()
    sel = st.selectbox("Chọn kỳ", periods, index=len(periods)-1, key=REV + "region_period")

    reg_view = reg[reg["Label"] == sel].sort_values("Tổng_Net", ascending=False).copy()
    reg_show = reg_view[["Label","Region","Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Tỷ_lệ_CK (%)","Prev_Tổng_Net","Change%"]].rename(columns={"Label":"Kỳ"})
    for c in ["Tổng_Gross","Tổng_Net","Số_KH","Số_đơn_hàng","Prev_Tổng_Net"]:
        reg_show[c] = reg_show[c].apply(fmt_int)
    if "Tỷ_lệ_CK (%)" in reg_show.columns:
    reg_show["Tỷ_lệ_CK (%)"] = reg_show["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v,2))
    if "Change%" in reg_show.columns:
    reg_show["Change%"] = reg_show["Change%"].apply(lambda v: fmt_pct(v,2,with_sign=True))
    st.dataframe(reg_show, use_container_width=True, hide_index=True)

# =====================================================
# =====================================================
# TOP/BOTTOM 10 STORE (CÓ Prev_Net & %Change + Số_đơn_hàng)
# =====================================================
st.subheader("🏪 Top/Bottom 10 Điểm mua hàng")
if "Điểm_mua_hàng" not in tmp.columns:
    st.info("Thiếu cột Điểm_mua_hàng.")
else:
    store_g = (
        tmp.groupby(["Điểm_mua_hàng"] + gcols, observed=True, sort=False)
        .agg(
            Label=("Label","first"),
            Tổng_Gross=("Tổng_Gross","sum"),
            Tổng_Net=("Tổng_Net","sum"),
            Số_đơn_hàng=("Số_CT","nunique"),   # ✅ thêm
        )
        .reset_index()
    )

    store_g["Tỷ_lệ_CK (%)"] = np.where(
        store_g["Tổng_Gross"]!=0,
        (1 - store_g["Tổng_Net"]/store_g["Tổng_Gross"])*100,
        0
    )

    store_g = store_g.sort_values(["Điểm_mua_hàng"] + gcols)
    store_g["Prev_Tổng_Net"] = store_g.groupby("Điểm_mua_hàng")["Tổng_Net"].shift(1)
    store_g["Change%"] = np.where(
        store_g["Prev_Tổng_Net"] > 0,
        (store_g["Tổng_Net"] - store_g["Prev_Tổng_Net"]) / store_g["Prev_Tổng_Net"] * 100,
        np.nan
    )

    periods2 = summary["Label"].tolist()
    sel2 = st.selectbox(
        "Chọn kỳ để xem Top/Bottom",
        periods2,
        index=len(periods2)-1,
        key=REV + "store_period"
    )

    ss = store_g[store_g["Label"] == sel2].copy()

    top10 = ss.sort_values("Tổng_Net", ascending=False).head(10)
    bot10 = ss.sort_values("Tổng_Net", ascending=True).head(10)

    def show_store_table(d):
        out = d[[
            "Label","Điểm_mua_hàng",
            "Tổng_Gross","Tổng_Net","Số_đơn_hàng",
            "Tỷ_lệ_CK (%)","Prev_Tổng_Net","Change%"
        ]].rename(columns={"Label":"Kỳ"})

        out["Tổng_Gross"] = out["Tổng_Gross"].apply(fmt_int)
        out["Tổng_Net"] = out["Tổng_Net"].apply(fmt_int)
        out["Số_đơn_hàng"] = out["Số_đơn_hàng"].apply(fmt_int)   # ✅ format
        out["Prev_Tổng_Net"] = out["Prev_Tổng_Net"].apply(fmt_int)
        out["Tỷ_lệ_CK (%)"] = out["Tỷ_lệ_CK (%)"].apply(lambda v: fmt_pct(v,2))
        out["Change%"] = out["Change%"].apply(lambda v: fmt_pct(v,2,with_sign=True))
        return out

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🏆 Top 10")
        st.dataframe(show_store_table(top10), use_container_width=True, hide_index=True)
    with c2:
        st.markdown("### 📉 Bottom 10")
        st.dataframe(show_store_table(bot10), use_container_width=True, hide_index=True)

