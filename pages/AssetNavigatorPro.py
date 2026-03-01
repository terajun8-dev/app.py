import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("Monte Carlo Simulation: Separation of Contribution & Investment Periods")

# --- 設定ガイド ---
with st.expander("📚 設定のヒント"):
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("""
        ### 市場リスク（通常のゆれ）
        * **全世界株式**: 期待 5.0 ~ 7.0% / リスク 15.0 ~ 20.0%
        * **米国S&P500**: 期待 7.0 ~ 9.0% / リスク 18.0 ~ 22.0%
        """)
    with col_h2:
        st.markdown("""
        ### ブラックスワン（突発的な暴落）
        * **2.0%**: 50年に一度（非常に稀な大恐慌）
        * **4.0%**: 25年に一度（現実的な警戒）
        """)

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. 基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000, step=100)
    mode = st.radio("モード選択", ["Accumulation (積立)", "4% Rule Withdrawal (取崩)"])
    
    if "Accumulation" in mode:
        monthly_investment = st.number_input("毎月の積立額 (万円)", value=10, min_value=0)
        investment_period = st.number_input("積立期間 (ヶ月)", value=60, min_value=0) # 新設
    else:
        monthly_investment = 0
        investment_period = 0
        
    total_months = st.number_input("シミュレーション期間/運用期間 (ヶ月)", value=120, min_value=1)
    
    # バリデーション
    if "Accumulation" in mode and investment_period > total_months:
        st.warning("⚠️ 積立期間が運用期間を超えています。運用期間終了まで積み立てられます。")

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
            
            # ブラックスワン判定
            if use_bs and bs_prob > 0 and np.random.rand() < m_bs_prob:
                growth *= (1 + bs_impact)
                bs_events[i].append(m)
            
            current *= growth
            
            # 積立ロジック：積立期間内であれば加算
            if "Accumulation" in mode:
                if m <= investment_period:
                    current += monthly_investment
            else:
                current -= (withdrawal * (1 + m_inf)**m)
            
            val = current / ((1 + m_inf)**m) if inf_rate > 0 else current
            all_results[i, m] = max(0, val)
            
    return all_results, bs_events

# --- メインロジック ---
if run_button:
    results, bs_logs = run_simulation(sim_count, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, investment_period, mode, inf_rate, bs_prob, bs_impact)
    
    time_axis = np.arange(total_months + 1)
    p_50 = np.median(results, axis=0)
    p_97_5, p_2_5 = np.percentile(results, [97.5, 2.5], axis=0)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("中央値（最終資産）", f"{int(p_50[-1]):,} 万円")
    col2.metric("成功率（残高 > 0）", f"{(np.sum(results[:, -1] > 0) / sim_count)*100:.1f} %")
    col3.metric("シミュレーション回数", f"{sim_count:,}")

    # --- グラフ描画 ---
    st.subheader("Interactive Monthly Projection")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_axis, y=p_97_5, line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=time_axis, y=p_2_5, fill='tonexty', fillcolor='rgba(255,165,0,0.1)', name='95%信頼区間', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=time_axis, y=p_50, line=dict(color='#007bff', width=3), name='全体の中央値'))

    if use_bs:
        bs_indices = [i for i, log in enumerate(bs_logs) if len(log) > 0]
        idx = np.random.choice(bs_indices) if bs_indices else np.random.randint(0, sim_count)
        sample_path = results[idx, :]
        sample_bs = bs_logs[idx]
        fig.add_trace(go.Scatter(x=time_axis, y=sample_path, line=dict(color='red', width=2), name='暴落遭遇サンプルの軌跡'))
    
    # 積立終了ラインの表示（積立モードのみ）
    if "Accumulation" in mode and 0 < investment_period < total_months:
        fig.add_vline(x=investment_period, line_dash="dot", line_color="gray", annotation_text="積立終了")

    st.plotly_chart(fig, use_container_width=True)

    # --- 個別診断レポート（ブラックスワンON時） ---
    if use_bs:
        st.subheader(f"🧐 暴落シミュレーション詳細診断（パスID: {idx}）")
        r1, r2 = st.columns([2, 1])
        with r1:
            if not sample_bs:
                st.success("✨ 幸運なことに、このサンプルでは暴落は発生しませんでした。")
            else:
                st.warning(f"⚠️ この人物は期間中に **{len(sample_bs)}回** の暴落に直撃しました。")
                st.write(f"**発生月:** {', '.join([f'{m}ヶ月目' for m in sample_bs])}")
        with r2:
            final_v = sample_path[-1]
            st.info(f"**サンプルの最終資産: {int(final_v):,} 万円**")

    # --- 分布図 ---
    st.subheader("Final Asset Distribution & Targets")
    fig_hist = go.Figure(data=[go.Histogram(x=results[:, -1], nbinsx=80, marker_color='#6c757d', opacity=0.5)])
    targets_vals = [initial_asset, initial_asset * 1.5, initial_asset * 2, 10000]
    target_names = ['Initial', '1.5x', '2.0x', '100M']
    for v, n in zip(targets_vals, target_names):
        fig_hist.add_vline(x=v, line_dash="dash", line_color="red", annotation_text=n)
    fig_hist.update_layout(xaxis_title="最終資産 (万円)", template="plotly_white", height=400)
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("条件を入力し、実行ボタンを押してください。")
    