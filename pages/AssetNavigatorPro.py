import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("Monte Carlo Simulation: Individual Path & Black Swan Analysis")

# --- 設定ガイド ---
with st.expander("📚 設定のヒント（ここをクリック）"):
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("""
        ### 市場リスク（通常のゆれ）
        - **全世界株式**: 期待 5~7% / リスク 15~20%
        - **米国S&P500**: 期待 7~9% / リスク 18~22%
        """)
    with col_h2:
        st.markdown("""
        ### ブラックスワン（突発的な暴落）
        - **4.0%**: 25年に一度（リーマン・コロナ級）
        - **10.0%**: 10年に一度（必ず一度は経験する嵐）
        """)

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. 基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000, step=100)
    mode = st.radio("モード選択", ["Accumulation (積立)", "4% Rule Withdrawal (取崩)"])
    monthly_investment = st.number_input("毎月の積立額 (万円)", value=10, min_value=0) if "Accumulation" in mode else 0
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
def run_simulation(n_sim, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, inf_rate, bs_prob, bs_impact):
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
            # 通常の市場変動（ボラティリティ）
            growth = np.exp((annual_return - 0.5 * annual_volatility**2) * dt + annual_volatility * np.sqrt(dt) * noise)
            
            # ブラックスワン（暴落）の判定
            if bs_prob > 0 and np.random.rand() < m_bs_prob:
                growth *= (1 + bs_impact)
                bs_events[i].append(m)
            
            current *= growth
            if "Accumulation" in mode:
                current += monthly_investment
            else:
                current -= (withdrawal * (1 + m_inf)**m)
            
            val = current / ((1 + m_inf)**m) if inf_rate > 0 else current
            all_results[i, m] = max(0, val)
            
    return all_results, bs_events

# --- メインロジック ---
if run_button:
    results, bs_logs = run_simulation(sim_count, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, inf_rate, bs_prob, bs_impact)
    
    time_axis = np.arange(total_months + 1)
    p_50 = np.median(results, axis=0)
    p_97_5, p_2_5 = np.percentile(results, [97.5, 2.5], axis=0)
    
    # 指標
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

    # 赤い線（サンプル）の選択
    # 暴落が起きたシナリオがあれば優先的に表示、なければランダム
    bs_indices = [i for i, log in enumerate(bs_logs) if len(log) > 0]
    idx = np.random.choice(bs_indices) if bs_indices else np.random.randint(0, sim_count)
    
    sample_path = results[idx, :]
    sample_bs = bs_logs[idx]
    
    fig.add_trace(go.Scatter(x=time_axis, y=sample_path, line=dict(color='red', width=2), name='個別サンプルの軌跡'))
    st.plotly_chart(fig, use_container_width=True)

    # --- ブラックスワン・レポート ---
    st.subheader(f"🧐 個別サンプルの詳細診断（パスID: {idx}）")
    r1, r2 = st.columns([2, 1])
    
    with r1:
        if not use_bs:
            st.info("ℹ️ ブラックスワン設定がOFFです。赤い線は通常の市場リスク（ボラティリティ）による変動のみを示しています。")
        elif not sample_bs:
            st.success("✨ 幸運なことに、このサンプルの期間中にはブラックスワンは発生しませんでした。")
        else:
            st.warning(f"⚠️ 期間中に **{len(sample_bs)}回** の暴落に直撃しました。")
            st.write(f"**発生時期:** {', '.join([f'{m}ヶ月目' for m in sample_bs])}")
            # 最初の下落の大きさを計算
            m0 = sample_bs[0]
            loss = sample_path[m0-1] - sample_path[m0]
            st.write(f"特に{m0}ヶ月目の下落では、実質価値が **約{int(loss)}万円** 急減しました。これが現実ならメンタルが試されます。")

    with r2:
        final_v = sample_path[-1]
        if final_v <= 0:
            st.error(f"**【破綻】** \n資産が尽きました。暴落のタイミングが悪かったか、リスクの取りすぎです。")
        elif final_v > initial_asset:
            st.info(f"**【目標達成】** \n暴落を乗り越え、最終的に元本以上の **{int(final_v)}万円** を確保しました。")
        else:
            st.warning(f"**【停滞】** \n元本を割り込む **{int(final_v)}万円** で終了。回復が間に合いませんでした。")

    # --- 分布図 ---
    st.subheader("Final Asset Distribution")
    fig_hist = go.Figure(data=[go.Histogram(x=results[:, -1], nbinsx=80, marker_color='#6c757d', opacity=0.5)])
    targets = [initial_asset, initial_asset * 2, 10000]
    names = ['Initial', '2.0x', '100M']
    for v, n in zip(targets, names):
        fig_hist.add_vline(x=v, line_dash="dash", line_color="red", annotation_text=n)
    fig_hist.update_layout(xaxis_title="最終資産 (万円)", template="plotly_white", height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("サイドバーで条件を設定し、実行ボタンを押してください。")