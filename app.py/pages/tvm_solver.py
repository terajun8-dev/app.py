import streamlit as st
import numpy_financial as npf
import numpy as np
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(page_title="TVM Solver", layout="wide")

# --- Initialize Session State ---
# PpY/CpYを一括で扱うための 'py' を追加
defaults = {'n': 0.0, 'i': 0.0, 'pv': 0.0, 'pmt': 0.0, 'fv': 0.0, 'py': 12.0}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- Solve Logic ---
def calculate(target):
    try:
        n, i, pv, pmt, fv = st.session_state.n, st.session_state.i, st.session_state.pv, st.session_state.pmt, st.session_state.fv
        py = st.session_state.py
        
        # Periodic Rate
        r = (i / 100) / py if i != 0 else 0
        
        if target == "n":
            res = npf.nper(r, pmt, pv, fv) if i != 0 else -(fv + pv) / pmt
            st.session_state.n = float(res)
        elif target == "i":
            rate_p = npf.rate(n, pmt, pv, fv)
            st.session_state.i = float(rate_p * py * 100)
        elif target == "pv":
            res = npf.pv(r, n, pmt, fv) if i != 0 else -(fv + pmt * n)
            st.session_state.pv = float(res)
        elif target == "pmt":
            res = npf.pmt(r, n, pv, fv) if i != 0 else -(fv + pv) / n
            st.session_state.pmt = float(res)
        elif target == "fv":
            res = npf.fv(r, n, pmt, pv) if i != 0 else -(pv + pmt * n)
            st.session_state.fv = float(res)
            
    except:
        st.toast("Calculation Error", icon="⚠️")

# --- UI ---
st.title("📟 TVM Solver Pro")
st.divider()

col_in, col_gr = st.columns([1, 2], gap="large")

with col_in:
    # Main TVM Variables
    st.number_input("N", key="n", step=1.0, format="%.3f")
    st.button("SOLVE N", on_click=calculate, args=("n",), use_container_width=True)
    
    st.number_input("I%", key="i", step=0.001, format="%.3f")
    st.button("SOLVE I%", on_click=calculate, args=("i",), use_container_width=True)
    
    st.number_input("PV", key="pv", step=1.0, format="%.3f")
    st.button("SOLVE PV", on_click=calculate, args=("pv",), use_container_width=True)
    
    st.number_input("PMT", key="pmt", step=1.0, format="%.3f")
    st.button("SOLVE PMT", on_click=calculate, args=("pmt",), use_container_width=True)
    
    st.number_input("FV", key="fv", step=1.0, format="%.3f")
    st.button("SOLVE FV", on_click=calculate, args=("fv",), use_container_width=True)

    st.write("---")
    # P/Y and C/Y synchronized as 'py'
    st.number_input("P/Y & C/Y", key="py", step=1.0, min_value=1.0, format="%.0f")
    st.caption("Common: 12 (Monthly), 2 (Semi-annual), 1 (Annual)")

with col_gr:
    try:
        if st.session_state.n > 0:
            n_val = int(st.session_state.n)
            i_val = st.session_state.i
            py_val = st.session_state.py
            r = (i_val / 100) / py_val
            periods = np.arange(n_val + 1)
            
            # Trajectory
            if i_val != 0:
                y_vals = [npf.fv(r, p, st.session_state.pmt, st.session_state.pv) for p in periods]
            else:
                y_vals = [-(st.session_state.pv + st.session_state.pmt * p) for p in periods]
            
            # --- Auto-Zoom Logic ---
            y_min, y_max = min(y_vals), max(y_vals)
            diff = abs(y_max - y_min)
            # 全体の変化が0.1%以下ならズームを効かせる
            padding = diff * 0.1 if diff > 0 else 1.0

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=periods, y=y_vals, mode='lines+markers', 
                line=dict(color='#00FFCC', width=3),
                fill='none', # ズーム時はfillがない方が見やすい
                hovertemplate="N: %{x}<br>Value: %{y:.3f}<extra></extra>"
            ))
            
            fig.update_layout(
                template="plotly_dark", title="Balance Trajectory (Auto-Scaled)",
                xaxis_title="N (Periods)", yaxis_title="Value",
                # 0固定をやめて、データの範囲に合わせる
                yaxis=dict(range=[y_min - padding, y_max + padding], tickformat=",.3f"),
                margin=dict(l=0, r=0, t=40, b=0), height=500
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Input N > 0 to see the trajectory. Y-axis scales automatically.")
    except:
        pass