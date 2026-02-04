# filters_shared.py
import pandas as pd
import streamlit as st

GLOBAL_PREFIX = "f_global_"

def init_global_defaults(df: pd.DataFrame):
    if st.session_state.get(GLOBAL_PREFIX + "inited", False):
        return

    if "Ngày" in df.columns and not df.empty:
        st.session_state[GLOBAL_PREFIX + "start_date"] = df["Ngày"].min().date()
        st.session_state[GLOBAL_PREFIX + "end_date"] = df["Ngày"].max().date()
    else:
        today = pd.Timestamp.today().date()
        st.session_state[GLOBAL_PREFIX + "start_date"] = today
        st.session_state[GLOBAL_PREFIX + "end_date"] = today

    st.session_state[GLOBAL_PREFIX + "loaiCT"] = ["All"]
    st.session_state[GLOBAL_PREFIX + "brand"]  = ["All"]
    st.session_state[GLOBAL_PREFIX + "region"] = ["All"]
    st.session_state[GLOBAL_PREFIX + "store"]  = ["All"]

    st.session_state[GLOBAL_PREFIX + "inited"] = True

def reset_global_filters():
    for k in list(st.session_state.keys()):
        if k.startswith(GLOBAL_PREFIX):
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
