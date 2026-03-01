import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("モンテカルロ法による標準偏差・ブラックスワン・4%ルール検証 (Interactive)")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. 基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000, step=100)
    mode = st.radio("モード選択", ["Accumulation (積立)", "4% Rule Withdrawal (取崩)"])
    if "Accumulation" in mode:
        monthly_investment = st.slider("毎月の積立額 (万円)", 0, 50, 10)
    else:
        monthly_investment = 0
    years = st.slider("シミュレーション期間 (年)", 5, 50, 30)
    
    st.header("2. 市場リスク設定 (年次)")
    annual_return = st.slider("期待収益率 (%)", -5.0, 15.0, 5.0) / 100
    annual_volatility = st.slider("標準偏差 / リスク (%)", 0.0, 30.0, 15.0) / 100
    
    st.header("3. オプション")
    use_inflation = st.checkbox("インフレ率を考慮 (実質価値)", value=True)
    inflation_rate = st.slider("年間インフレ率 (%)", 0.0, 5.0, 2.0) / 100 if use_inflation else 0.0
    use_black_swan = st.checkbox("ブラックスワン (暴落) を考慮", value=True)
    if use_black_swan:
        bs_prob = st.slider("発生確率 (年次 %)", 0.0, 10.0, 2.0) / 100
        bs_impact = st.slider("下落率 (%)", -80, -10, -40) / 100

# --- シミュレーション実行 ---
@st.cache_data # 計算を高速化
def run_simulation(initial_asset, annual_return, annual_volatility, years, monthly_investment, mode, use_inflation, inflation_rate, use_black_swan, bs_prob, bs_impact):
    simulations = 2000
    months = years * 12
    dt = 1/12
    all_results = np.zeros((simulations, months + 1))
    all_results[:, 0] = initial_asset
    initial_withdrawal_monthly = (initial_asset * 0.04) / 12

    for i in range(simulations):
        current_asset = initial_asset
        current_withdrawal = initial_withdrawal_monthly
        for m in range(1, months + 1):
            noise = np.random.normal(0, 1)
            growth = np.exp((annual_return - 0.5 * annual_volatility**2) * dt + annual_volatility * np.sqrt(dt) * noise)
            if use_black_swan and np.random.rand() < (bs_prob / 12):
                growth *= (1 + bs_impact)
            current_asset *= growth
            if "Withdrawal" in mode:
                current_asset -= current_withdrawal
                current_withdrawal *= (1 + inflation_rate)**(1/12)
            else:
                current_asset += monthly_investment
            val = current_asset / ((1 + inflation_rate)**(m/12)) if use_inflation else current_asset
            all_results[i, m] = max(0, val)
    return all_results

results = run_simulation(initial_asset, annual_return, annual_volatility, years, monthly_investment, mode, use_inflation, inflation_rate, use_black_swan, bs_prob if use_black_swan else 0, bs_impact if use_black_swan else 0)
time_axis = np.arange(years * 12 + 1) / 12

# --- メトリクス表示 ---
final_values = results[:, -1]
median_final = np.median(final_values)
failure_rate = (np.sum(final_values <= 0) / len(results)) * 100
prob_above_initial = (np.sum(final_values > initial_asset) / len(results)) * 100

col1, col2, col3 = st.columns(3)
col1.metric("Median Final Asset", f"{int(median_final)} 万円")
col2.metric("Success Rate (Not 0)", f"{100 - failure_rate:.1f} %")
col3.metric("Prob. > Initial", f"{prob_above_initial:.1f} %")

# --- メイングラフ (Plotly) ---
st.subheader("Interactive Asset Projection")
p_50 = np.median(results, axis=0)
p_84 = np.percentile(results, 84, axis=0)
p_16 = np.percentile(results, 16, axis=0)
p_97_5 = np.percentile(results, 97.5, axis=0)
p_2_5 = np.percentile(results, 2.5, axis=0)

fig = go.Figure()

# 2-sigma Range
fig.add_trace(go.Scatter(x=time_axis, y=p_97_5, line=dict(width=0), showlegend=False, hoverinfo='skip'))
fig.add_trace(go.Scatter(x=time_axis, y=p_2_5, line=dict(width=0), fill='tonexty', fillcolor='rgba(31, 119, 180, 0.1)', name='2-sigma Range (95%)'))

# 1-sigma Range
fig.add_trace(go.Scatter(x=time_axis, y=p_84, line=dict(width=0), showlegend=False, hoverinfo='skip'))
fig.add_trace(go.Scatter(x=time_axis, y=p_16, line=dict(width=0), fill='tonexty', fillcolor='rgba(31, 119, 180, 0.25)', name='1-sigma Range (68%)'))

# Median Line
fig.add_trace(go.Scatter(x=time_axis, y=p_50, line=dict(color='#1f77b4', width=3), name='Median (Most Likely)'))

fig.update_layout(
    xaxis_title="Years", yaxis_title="Asset Balance (10k JPY)",
    hovermode="x unified", template="plotly_white",
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)
st.plotly_chart(fig, use_container_width=True)

# --- ヒストグラム (情報を追加) ---
st.subheader("Final Asset Distribution Analysis")
fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(x=final_values, nbinsx=50, marker_color='skyblue', opacity=0.7, name='Frequency'))

# 統計情報のラインを追加
fig_hist.add_vline(x=median_final, line_width=3, line_dash="dash", line_color="red", annotation_text=f"Median: {int(median_final)}")
fig_hist.add_vline(x=initial_asset, line_width=2, line_color="green", annotation_text="Initial Asset")

fig_hist.update_layout(
    xaxis_title="Final Asset Value (10k JPY)", yaxis_title="Count",
    template="plotly_white", bargap=0.05
)
st.plotly_chart(fig_hist, use_container_width=True)

# 確率情報のテーブル
st.markdown("### 🎯 Probability of Achieving Goals")
targets = [initial_asset, initial_asset * 1.5, initial_asset * 2, 10000] # 目標：初期値、1.5倍、2倍、1億円
target_probs = [(np.sum(final_values >= t) / len(results)) * 100 for t in targets]

df_prob = pd.DataFrame({
    "Target Asset (10k JPY)": [f"{int(t)} 万円" for t in targets],
    "Probability (%)": [f"{p:.1f} %" for p in target_probs]
})
st.table(df_prob)

st.info("💡 **Interactive Guide:** グラフにマウスを乗せると、その時点での具体的な資産額が表示されます。下の表は、最終的にその金額以上を維持できている確率を示しています。")
