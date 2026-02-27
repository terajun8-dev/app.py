import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import platform

# --- Page Configuration ---
st.set_page_config(page_title="Strategic Asset Analyzer", layout="wide")

# --- 2026 Updated Defaults (Portfolio-specific) ---
DEFAULTS = {
    "m": 10.0,      
    "n": 3000,     
    "ma": 240,     # 20 years
    "hold_m": 120, # 10 years
    "init": 100.0, 
    "target": 5000.0,
    "scenarios": {
        "S&P500 (US Equity)": {"g": 9.0, "s": 18.0, "color": "#FFA502"},
        "All Country (Equity)": {"g": 7.0, "s": 15.0, "color": "#2ED573"},
        "Balanced (60/40)": {"g": 4.0, "s": 10.0, "color": "#1E90FF"}
    }
}

st.title("🛡️ Strategic Asset Analyzer")
st.caption("Interactive Monte Carlo Simulation: Portfolios 2026 Edition")

# --- Sidebar: Configuration ---
st.sidebar.header("⚙️ Basic Settings")
m = st.sidebar.number_input("Monthly Contribution (10k JPY)", value=DEFAULTS["m"], step=1.0)
n = st.sidebar.number_input("Number of Trials (n)", value=DEFAULTS["n"], min_value=100, max_value=5000, step=500)
ma = st.sidebar.number_input("Contribution Period (Months)", value=DEFAULTS["ma"], step=12)
hold_m = st.sidebar.number_input("Holding Period after (Months)", value=DEFAULTS["hold_m"], step=12)

init_v = st.sidebar.number_input("Initial Investment (10k JPY)", value=DEFAULTS["init"], step=10.0)
target_v = st.sidebar.number_input("Target Amount (10k JPY)", value=DEFAULTS["target"], step=100.0)

st.sidebar.write("---")
st.sidebar.header("📊 Portfolio Params (%)")
scenario_params = {}
for name, vals in DEFAULTS["scenarios"].items():
    st.sidebar.subheader(f"■ {name}")
    g = st.sidebar.number_input(f"Return (%)", value=vals["g"], key=f"g_{name}")
    s = st.sidebar.number_input(f"Risk (%)", value=vals["s"], key=f"s_{name}")
    scenario_params[name] = {"g": g/100, "s": s/100, "color": vals["color"]}

# --- Analysis Execution ---
if st.sidebar.button("🚀 Run Analysis", use_container_width=True):
    total_days = (ma + hold_m) * 30
    total_invested = init_v + (m * ma)
    years_axis = np.arange(total_days + 1) / 360
    
    fig_t = go.Figure()
    fig_d = go.Figure()
    summary_list = []

    for name, prm in scenario_params.items():
        # Simulation Logic (Geometric Brownian Motion)
        dt = 1/365
        mu_d = (np.log(1 + prm["g"]) - 0.5 * prm["s"]**2) * dt
        sig_d = prm["s"] * np.sqrt(dt)
        
        daily_returns = np.exp(np.random.normal(mu_d, sig_d, (n, total_days)))
        paths = np.zeros((n, total_days + 1))
        paths[:, 0] = init_v
        
        for d in range(1, total_days + 1):
            curr = paths[:, d-1]
            if d <= ma * 30 and d % 30 == 0:
                curr = curr + m
            paths[:, d] = curr * daily_returns[:, d-1]

        # Statistics
        p5, p50, p95 = np.percentile(paths, [5, 50, 95], axis=0)
        final_vals = paths[:, -1]
        loss_p = (np.sum(final_vals < total_invested) / n) * 100
        target_p = (np.sum(final_vals >= target_v) / n) * 100

        # --- Chart 1: Projection (Time Series) ---
        fig_t.add_trace(go.Scatter(
            x=np.concatenate([years_axis, years_axis[::-1]]),
            y=np.concatenate([p95, p5[::-1]]),
            fill='toself', fillcolor=prm["color"], opacity=0.1,
            line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip", showlegend=False
        ))
        fig_t.add_trace(go.Scatter(
            x=years_axis, y=p50, name=name,
            line=dict(color=prm["color"], width=3),
            hovertemplate="Year: %{x:.1f}<br>Value: %{y:,.0f} (10k JPY)<extra></extra>"
        ))

        # --- Chart 2: Probability (CDF) ---
        sorted_res = np.sort(final_vals)
        cdf = np.arange(len(sorted_res)) / float(len(sorted_res)) * 100
        fig_d.add_trace(go.Scatter(
            x=sorted_res, y=cdf, name=name,
            line=dict(color=prm["color"], width=2),
            hovertemplate="Final Value: %{x:,.0f} (10k JPY)<br>Probability: %{y:.1f}%<extra></extra>"
        ))

        summary_list.append({
            "Portfolio": name,
            "Median (10k)": f"{p50[-1]:,.0f}",
            "Loss Prob": f"{loss_p:.1f}%",
            "Target Prob": f"{target_p:.1f}%"
        })

    # Update Layouts
    fig_t.update_layout(
        title="Asset Projection (Median & 90% Range)",
        xaxis_title="Years", yaxis_title="Asset (10k JPY)",
        hovermode="x unified", template="plotly_dark",
        yaxis_range=[0, float(summary_list[0]["Median (10k)"].replace(',','')) * 2.5]
    )
    
    fig_d.update_layout(
        title="Cumulative Probability (Will it reach the target?)",
        xaxis_title="Final Value (10k JPY)", yaxis_title="Probability (%)",
        template="plotly_dark", xaxis_range=[0, target_v * 3]
    )
    fig_d.add_vline(x=total_invested, line_dash="dash", line_color="white", annotation_text="Principal")
    fig_d.add_vline(x=target_v, line_dash="dot", line_color="gold", annotation_text="Target")

    # Display Charts
    col1, col2 = st.columns(2)
    with col1: st.plotly_chart(fig_t, use_container_width=True)
    with col2: st.plotly_chart(fig_d, use_container_width=True)

    # Summary Table
    st.subheader("📋 Analysis Summary")
    st.table(pd.DataFrame(summary_list))
    st.info(f"Total Invested: {total_invested:,.0f} (10k JPY) / Duration: {ma + hold_m} months")

else:
    st.info("👈 Choose your portfolio and click 'Run Analysis'.")
    st.warning("""
    **【2026 Recommended Guide】**
    * **S&P500 (US)**: Return 9.0% / Risk 18.0% (Aggressive growth)
    * **All Country (Global)**: Return 7.0% / Risk 15.0% (Standard diversification)
    * **Balanced (Asset Mix)**: Return 4.0% / Risk 10.0% (Defensive approach)
    """)