import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("Monte Carlo Simulation: Full-Width Sigma & Risk Analysis")

# --- 📚 設定のヒント（数値を修正！） ---
with st.expander("📚 設定の目安と用語解説（ここをクリック）"):
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("""
        ### 1. 市場リスク（通常のゆれ）
        * **全世界株式**: 期待 5.0% ~ 7.0% / リスク 15.0% ~ 20.0%
        * **米国S&P500**: 期待 7.0% ~ 9.0% / リスク 18.0% ~ 22.0%
        """)
    with col_h2:
        st.markdown("""
        ### 2. ブラックスワン（突発的な暴落）
        * **4.0%**: 25年に一度（リーマン・コロナ級）
        * **10.0%**: 10年に一度（必ず一度は経験する嵐）
        """)
    st.info("※1σ（標準偏差1）は68%の確率、2σ（標準偏差2）は95%の確率で収まる範囲です。")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. 基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000, step=100)
    mode = st.radio("モード選択", ["Accumulation (積立)", "4% Rule Withdrawal (取崩)"])
    
    if "Accumulation" in mode:
        monthly_investment = st.number_input("毎月の積立額 (万円)", value=10, min_value=0)
        investment_period = st.number_input("積立期間 (ヶ月)", value=60, min_value=0)
        # 元本の計算：初期資産 + (積立額 × 積立期間)
        total_principal = initial_asset + (monthly_investment * investment_period)
    else:
        monthly_investment = 0
        investment_period = 0
        total_principal = initial_asset # 取崩の場合は初期資産が元本
        
    total_months = st.number_input("シミュレーション期間 (ヶ月)", value=120, min_value=1)
    
    st.header("2. 詳細設定")
    sim_count = st.selectbox("試行回数", options=[1000, 2000, 5000], index=1)
    annual_return = st.number_input("期待収益率 (%)", value=5.0, step=0.1) / 100
    annual_volatility = st.number_input("リスク/標準偏差 (%)", value=15.0, step=0.1) / 100
    
    st.header("3. オプション")
    use_inflation = st.checkbox("インフレ考慮", value=True)
    inf_rate = st.number_input("インフレ率 (%)", value=2.0) / 100 if use_inflation else 0
    
    st.header("4. ブラックスワン設定")
    use_bs = st.checkbox("暴落を考慮", value=True)
    bs_prob = st.number_input("発生確率 (%)", value=4.0) / 100 if use_bs else 0
    bs_impact = st.number_input("下落率 (%)", value=-40.0) / 100 if use_bs else 0

    st.markdown("---")
    run_button = st.button("🚀 シミュレーションを実行", use_container_width=True, type="primary")

# --- シミュレーション関数 ---
def run_simulation(n_sim, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, investment_period, mode, inf_rate, bs_prob, bs_impact):
    dt = 1/12
    all_results = np.zeros((n_sim, total_months + 1))
    all_results[:, 0] = initial_asset
    bs_events = [[] for _ in range(n_sim)]
    m_inf = (1 + inf_rate)**(1/12) - 1
    m_bs_prob = bs_prob / 12
    withdrawal = (initial_asset * 0.04) / 12

    for i in range(n_sim):
        current = initial_asset
        for m in range(1, total_months + 1):
            noise = np.random.normal(0, 1)
            growth = np.exp((annual_return - 0.5 * annual_volatility**2) * dt + annual_volatility * np.sqrt(dt) * noise)
            if use_bs and bs_prob > 0 and np.random.rand() < m_bs_prob:
                growth *= (1 + bs_impact)
                bs_events[i].append(m)
            current *= growth
            if "Accumulation" in mode:
                if m <= investment_period: current += monthly_investment
            else:
                current -= (withdrawal * (1 + m_inf)**m)
            val = current / ((1 + m_inf)**m) if inf_rate > 0 else current
            all_results[i, m] = max(0, val)
    return all_results, bs_events

# --- メインロジック ---
if run_button:
    results, bs_logs = run_simulation(sim_count, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, investment_period, mode, inf_rate, bs_prob, bs_impact)
    
    time_axis = np.arange(total_months + 1)
    final_p = results[:, -1]
    p_median = np.median(results, axis=0)
    p_97_5, p_2_5 = np.percentile(results, [97.5, 2.5], axis=0)
    p_84, p_16 = np.percentile(results, [84, 16], axis=0)
    
    # 指標計算（元本維持は「投資総額」と比較）
    success_rate = (np.sum(final_p > 0.01) / sim_count) * 100
    prob_above_principal = (np.sum(final_p >= total_principal) / sim_count) * 100
    prob_1_5x = (np.sum(final_p >= total_principal * 1.5) / sim_count) * 100

    # 1. メトリクス
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("最終資産 (中央値)", f"{int(p_median[-1]):,} 万円")
    m2.metric("成功率 (残高 > 0)", f"{success_rate:.1f} %")
    m3.metric("元本維持率", f"{prob_above_principal:.1f} %")
    m4.metric("1.5倍達成率", f"{prob_1_5x:.1f} %")

    # 2. 推移グラフ
    st.subheader("Interactive Monthly Projection (Sigma Ranges)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_axis, y=p_97_5, line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=time_axis, y=p_2_5, fill='tonexty', fillcolor='rgba(255,165,0,0.08)', name='2σ Range (95%)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=time_axis, y=p_84, line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=time_axis, y=p_16, fill='tonexty', fillcolor='rgba(40,167,69,0.15)', name='1σ Range (68%)', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=time_axis, y=p_median, line=dict(color='#007bff', width=4), name='Median (中央値)'))

    if use_bs:
        bs_indices = [i for i, log in enumerate(bs_logs) if len(log) > 0]
        idx = np.random.choice(bs_indices) if bs_indices else np.random.randint(0, sim_count)
        fig.add_trace(go.Scatter(x=time_axis, y=results[idx, :], line=dict(color='red', width=2.5), name='暴落遭遇サンプル'))
        st.info(f"🚩 **ブラックスワン診断（ID: {idx}）**: 赤い線は **{len(bs_logs[idx])}回** の暴落を経験。最終資産: **{int(results[idx, -1]):,} 万円**")
    
    fig.update_layout(xaxis_title="Months", yaxis_title="Asset (万円)", template="plotly_white", height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 3. 分布図
    st.subheader("Final Asset Distribution & Sigma Analysis")
    fig_hist = go.Figure(data=[go.Histogram(x=final_p, nbinsx=120, marker_color='#6c757d', opacity=0.4, name='分布')])
    
    stats = {
        'Median': (np.median(final_p), '#007bff', 'solid', 4),
        'Principal (投資総額)': (total_principal, '#6f42c1', 'dash', 3),
        '1σ (上位16%)': (np.percentile(final_p, 84), '#28a745', 'dash', 2),
        '1σ (下位16%)': (np.percentile(final_p, 16), '#28a745', 'dash', 2),
        '2σ (上位2.5%)': (np.percentile(final_p, 97.5), '#ffc107', 'dot', 2),
        '2σ (下位2.5%)': (np.percentile(final_p, 2.5), '#ffc107', 'dot', 2),
    }
    
    for label, (val, color, dash, width) in stats.items():
        fig_hist.add_vline(x=val, line_dash=dash, line_color=color, line_width=width, 
                          annotation_text=f"{label}: {int(val)}", annotation_position="top left")

    fig_hist.update_layout(xaxis_title="最終資産 (万円)", yaxis_title="頻度", template="plotly_white", height=550)
    st.plotly_chart(fig_hist, use_container_width=True)

    # 4. ターゲット達成率（プログレスバー）
    st.subheader("Target Achievement Summary")
    t_list = [total_principal, total_principal * 1.5, total_principal * 2.0, 10000]
    t_names = ['元本維持（投資総額）', '元本の1.5倍', '元本の2.0倍', '資産1億円以上']
    t_probs = [(np.sum(final_p >= t) / sim_count) * 100 for t in t_list]
    
    cols = st.columns(len(t_list))
    for i, col in enumerate(cols):
        col.write(f"**{t_names[i]}**")
        col.progress(t_probs[i] / 100)
        col.write(f"{t_probs[i]:.1f} %")

else:
    st.info("条件を設定して実行してください。")