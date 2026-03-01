import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("Monthly Monte Carlo Simulation: Multi-Color Risk Analysis")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. 基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000, step=100)
    mode = st.radio("モード選択", ["Accumulation (積立)", "4% Rule Withdrawal (取崩)"])
    
    if "Accumulation" in mode:
        monthly_investment = st.slider("毎月の積立額 (万円)", 0, 100, 10)
    else:
        monthly_investment = 0
        
    total_months = st.slider("シミュレーション期間 (ヶ月)", 1, 600, 120)
    
    st.header("2. 市場リスク設定 (年次率)")
    annual_return = st.slider("期待収益率 (年利 %)", -5.0, 15.0, 5.0) / 100
    annual_volatility = st.slider("標準偏差 / リスク (年次 %)", 0.0, 30.0, 15.0) / 100
    
    st.header("3. オプション")
    use_inflation = st.checkbox("インフレ率を考慮 (実質価値)", value=True)
    inflation_rate_annual = st.slider("年間インフレ率 (%)", 0.0, 5.0, 2.0) / 100 if use_inflation else 0.0
    
    use_black_swan = st.checkbox("ブラックスワン (暴落) を考慮", value=True)
    if use_black_swan:
        bs_prob_annual = st.slider("発生確率 (年次 %)", 0.0, 10.0, 2.0) / 100
        bs_impact = st.slider("下落率 (%)", -80, -10, -40) / 100

# --- シミュレーション実行 ---
@st.cache_data
def run_simulation(initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, use_inflation, inflation_rate_annual, use_black_swan, bs_prob_annual, bs_impact):
    simulations = 2000
    dt = 1/12
    all_results = np.zeros((simulations, total_months + 1))
    all_results[:, 0] = initial_asset
    
    initial_withdrawal_monthly = (initial_asset * 0.04) / 12
    monthly_inflation = (1 + inflation_rate_annual)**(1/12) - 1
    monthly_bs_prob = bs_prob_annual / 12

    for i in range(simulations):
        current_asset = initial_asset
        current_withdrawal = initial_withdrawal_monthly
        for m in range(1, total_months + 1):
            # 幾何ブラウン運動
            noise = np.random.normal(0, 1)
            growth = np.exp((annual_return - 0.5 * annual_volatility**2) * dt + annual_volatility * np.sqrt(dt) * noise)
            
            # ブラックスワン
            if use_black_swan and np.random.rand() < monthly_bs_prob:
                growth *= (1 + bs_impact)
            
            current_asset *= growth
            if "Withdrawal" in mode:
                current_asset -= current_withdrawal
                current_withdrawal *= (1 + monthly_inflation)
            else:
                current_asset += monthly_investment
            
            # インフレ調整
            val = current_asset / ((1 + monthly_inflation)**m) if use_inflation else current_asset
            all_results[i, m] = max(0, val)
    return all_results

results = run_simulation(initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, use_inflation, inflation_rate_annual, use_black_swan, bs_prob_annual if use_black_swan else 0, bs_impact if use_black_swan else 0)
time_axis = np.arange(total_months + 1)

# --- 統計計算 ---
final_values = results[:, -1]
p_50 = np.median(results, axis=0)
p_84, p_16 = np.percentile(results, 84, axis=0), np.percentile(results, 16, axis=0)
p_97_5, p_2_5 = np.percentile(results, 97.5, axis=0), np.percentile(results, 2.5, axis=0)

# --- 指標表示 ---
col1, col2, col3 = st.columns(3)
col1.metric("Median Final Asset", f"{int(p_50[-1])} 万円")
col2.metric("Success Rate", f"{(np.sum(final_values > 0)/2000)*100:.1f} %")
col3.metric("Prob. > Initial", f"{(np.sum(final_values > initial_asset)/2000)*100:.1f} %")

# --- メイングラフ (Plotly: 高視認性カラー) ---
st.subheader("Interactive Monthly Projection")
fig = go.Figure()

# 2-sigma (オレンジ: 95% 範囲)
fig.add_trace(go.Scatter(x=time_axis, y=p_97_5, line=dict(color='rgba(255, 165, 0, 0)', width=0), showlegend=False, hoverinfo='skip'))
fig.add_trace(go.Scatter(x=time_axis, y=p_2_5, line=dict(color='rgba(255, 165, 0, 0)', width=0), fill='tonexty', fillcolor='rgba(255, 165, 0, 0.1)', name='2-sigma (95% Prob.)'))

# 1-sigma (グリーン: 68% 範囲)
fig.add_trace(go.Scatter(x=time_axis, y=p_84, line=dict(color='rgba(40, 167, 69, 0)', width=0), showlegend=False, hoverinfo='skip'))
fig.add_trace(go.Scatter(x=time_axis, y=p_16, line=dict(color='rgba(40, 167, 69, 0)', width=0), fill='tonexty', fillcolor='rgba(40, 167, 69, 0.25)', name='1-sigma (68% Prob.)'))

# 中央値 (ブルー)
fig.add_trace(go.Scatter(x=time_axis, y=p_50, line=dict(color='#007bff', width=4), name='Median (Most Likely)'))

fig.update_layout(
    xaxis_title="Months", yaxis_title="Asset (10k JPY)",
    hovermode="x unified", template="plotly_white",
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    margin=dict(l=20, r=20, t=40, b=20)
)
st.plotly_chart(fig, use_container_width=True)

# --- ヒストグラム ---
st.subheader("Final Asset Distribution Analysis")
fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(x=final_values, nbinsx=60, marker_color='#6c757d', opacity=0.6, name='Frequency'))
fig_hist.add_vline(x=p_50[-1], line_width=3, line_dash="dash", line_color="#007bff", annotation_text="Median")
fig_hist.add_vline(x=initial_asset, line_width=2, line_color="#28a745", annotation_text="Initial")

fig_hist.update_layout(xaxis_title="Final Asset (10k JPY)", yaxis_title="Count", template="plotly_white")
st.plotly_chart(fig_hist, use_container_width=True)

# --- 到達確率表 ---
st.markdown(f"### 🎯 Probability Table after {total_months} Months")
target_list = [initial_asset, initial_asset * 1.5, initial_asset * 2.0, 10000]
target_probs = [(np.sum(final_values >= t) / 2000) * 100 for t in target_list]

df_res = pd.DataFrame({
    "Target Outcome": ["Keep Initial (元本維持)", "1.5x Growth (1.5倍)", "2.0x Growth (2倍)", "100M JPY (億り人)"],
    "Required Asset": [f"{int(t)} 万円" for t in target_list],
    "Probability": [f"{p:.1f} %" for p in target_probs]
})
st.table(df_res)