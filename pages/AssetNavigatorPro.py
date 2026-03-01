import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("Monte Carlo Simulation: Individual Path & Black Swan Analysis")

# --- 使い方ガイド（前回の内容を維持） ---
with st.expander("📚 設定の目安と用語解説"):
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("""
        ### 市場リスク設定のヒント
        | 資産タイプ | 期待収益率 | 標準偏差 |
        | :--- | :---: | :---: |
        | **定期預金** | 0.2% | 0% |
        | **全世界株式** | 5~7% | 15~20% |
        """)
    with col_h2:
        st.markdown("""
        ### ブラックスワン確率の目安
        - **2.0%**: 50年に一度（超稀）
        - **4.0%**: 25年に一度（現実的な警戒）
        - **10.0%**: 10年に一度（必ず遭遇する前提）
        """)

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. 基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000, step=100)
    mode = st.radio("モード選択", ["Accumulation (積立)", "4% Rule Withdrawal (取崩)"])
    monthly_investment = st.number_input("毎月の積立額 (万円)", value=10, min_value=0) if "Accumulation" in mode else 0
    total_months = st.number_input("シミュレーション期間 (ヶ月)", value=120, min_value=1)
    
    st.header("2. 詳細設定")
    sim_count = st.selectbox("試行回数", options=[1000, 2000, 5000, 10000], index=1)
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

# --- シミュレーション関数 (暴落記録機能付き) ---
def run_simulation(n_sim, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, inf_rate, bs_prob, bs_impact):
    dt = 1/12
    all_results = np.zeros((n_sim, total_months + 1))
    all_results[:, 0] = initial_asset
    bs_events = [[] for _ in range(n_sim)] # 各試行の暴落発生月を記録
    
    m_inf = (1 + inf_rate)**(1/12) - 1
    m_bs_prob = bs_prob / 12
    withdrawal = (initial_asset * 0.04) / 12

    for i in range(n_sim):
        current = initial_asset
        for m in range(1, total_months + 1):
            noise = np.random.normal(0, 1)
            growth = np.exp((annual_return - 0.5 * annual_volatility**2) * dt + annual_volatility * np.sqrt(dt) * noise)
            
            # ブラックスワン判定
            if bs_prob > 0 and np.random.rand() < m_bs_prob:
                growth *= (1 + bs_impact)
                bs_events[i].append(m) # 発生月を記録
            
            current *= growth
            current = current + monthly_investment if "Accumulation" in mode else current - (withdrawal * (1 + m_inf)**m)
            all_results[i, m] = max(0, current / ((1 + m_inf)**m))
            
    return all_results, bs_events

# --- メインロジック ---
if run_button:
    results, bs_logs = run_simulation(sim_count, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, inf_rate, bs_prob, bs_impact)
    
    time_axis = np.arange(total_months + 1)
    p_50 = np.median(results, axis=0)
    p_97_5, p_2_5 = np.percentile(results, [97.5, 2.5], axis=0)
    p_84, p_16 = np.percentile(results, [84, 16], axis=0)
    
    # メトリクス
    col1, col2, col3 = st.columns(3)
    col1.metric("Median Final Asset", f"{int(p_50[-1]):,} 万円")
    col2.metric("Success Rate", f"{(np.sum(results[:, -1] > 0) / sim_count)*100:.1f} %")
    col3.metric("Simulation Paths", f"{sim_count:,}")

    # --- 時系列グラフ ---
    st.subheader("Interactive Monthly Projection")
    fig = go.Figure()
    # 統計帯
    fig.add_trace(go.Scatter(x=time_axis, y=p_97_5, line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=time_axis, y=p_2_5, fill='tonexty', fillcolor='rgba(255,165,0,0.1)', name='95% Range', line=dict(width=0)))
    fig.add_trace(go.Scatter(x=time_axis, y=p_50, line=dict(color='#007bff', width=3), name='Median (Overall)'))

    # ランダムサンプルの抽出
    idx = np.random.randint(0, sim_count)
    sample_path = results[idx, :]
    sample_bs = bs_logs[idx]
    
    fig.add_trace(go.Scatter(x=time_axis, y=sample_path, line=dict(color='red', width=2), name='Sample Individual Path'))
    fig.update_layout(xaxis_title="Months", yaxis_title="Asset (万円)", template="plotly_white", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # --- ブラックスワン・個別レポート ---
    st.subheader(f"🧐 Sample Path Analysis (Path ID: {idx})")
    rep_col1, rep_col2 = st.columns([2, 1])
    
    with rep_col1:
        if not sample_bs:
            st.success("✨ このシナリオの人物は、期間中に一度もブラックスワン（暴落）に遭遇しませんでした。非常に幸運な一生です。")
        else:
            st.warning(f"⚠️ この人物は期間中に **{len(sample_bs)}回** のブラックスワンに遭遇しました。")
            events_str = ", ".join([f"{m}ヶ月目" for m in sample_bs])
            st.write(f"**発生時期:** {events_str}")
            
            # 暴落の影響解説
            first_bs = sample_bs[0]
            drop_val = sample_path[first_bs-1] - sample_path[first_bs]
            st.write(f"特に{first_bs}ヶ月目の暴落では、一瞬で実質 **約{int(drop_val)}万円** の価値が失われました。")

    with rep_col2:
        final_val = sample_path[-1]
        diff = final_val - initial_asset
        if final_val <= 0:
            st.error(f"**結果: 破綻** \n資産が底をつきました。暴落のタイミングが悪く、回復不能なダメージを受けました。")
        elif diff > 0:
            st.info(f"**結果: 勝利** \n暴落に遭いながらも、最終的に元本を **{int(diff)}万円** 上回って完走しました。")
        else:
            st.warning(f"**結果: 停滞** \n暴落の影響で、最終資産は元本を **{int(abs(diff))}万円** 下回りました。")

    # --- 分布図 ---
    st.subheader("Final Asset Distribution")
    fig_hist = go.Figure(data=[go.Histogram(x=results[:, -1], nbinsx=80, marker_color='#6c757d', opacity=0.5)])
    targets = [initial_asset, initial_asset * 2, 10000]
    names = ['Initial', '2.0x', '100M']
    for v, n in zip(targets, names):
        fig_hist.add_vline(x=v, line_dash="dash", line_color="red", annotation_text=n)
    fig_hist.update_layout(xaxis_title="Final Asset (万円)", template="plotly_white", height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("サイドバーで条件を設定し、実行ボタンを押してください。赤い線（個別サンプル）が暴落に遭うまで何度か試してみるのがおすすめです。")