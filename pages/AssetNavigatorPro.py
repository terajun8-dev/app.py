import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("Monte Carlo Simulation: Distribution-Focused Analysis")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. 基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000, step=100)
    mode = st.radio("モード選択", ["Accumulation (積立)", "4% Rule Withdrawal (取崩)"])
    
    if "Accumulation" in mode:
        monthly_investment = st.number_input("毎月の積立額 (万円)", value=10, min_value=0, step=1)
    else:
        monthly_investment = 0
        
    total_months = st.number_input("シミュレーション期間 (ヶ月)", value=120, min_value=1, step=1)
    
    st.header("2. シミュレーション設定")
    sim_count = st.selectbox("試行回数", options=[1000, 2000, 3000, 5000, 10000, 20000], index=1)
    
    st.header("3. 市場リスク・インフレ")
    annual_return = st.number_input("期待収益率 (年利 %)", value=5.0, step=0.1) / 100
    annual_volatility = st.number_input("標準偏差 / リスク (年次 %)", value=15.0, min_value=0.0, step=0.1) / 100
    
    use_inflation = st.checkbox("インフレ率を考慮 (実質価値)", value=True)
    inflation_rate_annual = st.number_input("年間インフレ率 (%)", value=2.0, step=0.1) / 100 if use_inflation else 0.0
    
    st.header("4. ブラックスワン設定")
    use_black_swan = st.checkbox("暴落イベントを考慮", value=True)
    if use_black_swan:
        bs_prob_annual = st.number_input("発生確率 (年次 %)", value=2.0, min_value=0.0, max_value=100.0, step=0.1) / 100
        bs_impact = st.number_input("下落率 (%)", value=-40.0, max_value=-0.1, step=1.0) / 100

    st.markdown("---")
    run_button = st.button("🚀 シミュレーションを実行", use_container_width=True, type="primary")

# --- シミュレーション関数 ---
def run_simulation(n_sim, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, use_inflation, inflation_rate_annual, use_black_swan, bs_prob_annual, bs_impact):
    dt = 1/12
    all_results = np.zeros((n_sim, total_months + 1))
    all_results[:, 0] = initial_asset
    
    initial_withdrawal_monthly = (initial_asset * 0.04) / 12
    monthly_inflation = (1 + inflation_rate_annual)**(1/12) - 1
    monthly_bs_prob = bs_prob_annual / 12

    for i in range(n_sim):
        current_asset = initial_asset
        current_withdrawal = initial_withdrawal_monthly
        for m in range(1, total_months + 1):
            noise = np.random.normal(0, 1)
            growth = np.exp((annual_return - 0.5 * annual_volatility**2) * dt + annual_volatility * np.sqrt(dt) * noise)
            
            if use_black_swan and np.random.rand() < monthly_bs_prob:
                growth *= (1 + bs_impact)
            
            current_asset *= growth
            if "Withdrawal" in mode:
                current_asset -= current_withdrawal
                current_withdrawal *= (1 + monthly_inflation)
            else:
                current_asset += monthly_investment
            
            val = current_asset / ((1 + monthly_inflation)**m) if use_inflation else current_asset
            all_results[i, m] = max(0, val)
    return all_results

# --- メインロジック ---
if run_button:
    with st.spinner(f"{sim_count:,} 回のシナリオを計算中..."):
        results = run_simulation(sim_count, initial_asset, annual_return, annual_volatility, total_months, monthly_investment, mode, use_inflation, inflation_rate_annual, use_black_swan, bs_prob_annual if use_black_swan else 0, bs_impact if use_black_swan else 0)
        
        time_axis = np.arange(total_months + 1)
        final_values = results[:, -1]
        p_50 = np.median(results, axis=0)
        p_84, p_16 = np.percentile(results, 84, axis=0), np.percentile(results, 16, axis=0)
        p_97_5, p_2_5 = np.percentile(results, 97.5, axis=0), np.percentile(results, 2.5, axis=0)
        p_5 = np.percentile(results, 5, axis=0)

        failure_rate = (np.sum(final_values <= 0) / len(results)) * 100
        prob_above_initial = (np.sum(final_values > initial_asset) / len(results)) * 100

        # メトリクス表示
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Median Final Asset", f"{int(p_50[-1])} 万円")
        col2.metric("Success Rate", f"{100 - failure_rate:.1f} %")
        col3.metric("Prob. > Initial", f"{prob_above_initial:.1f} %")
        col4.metric("Simulation Paths", f"{len(results):,}")

        # --- 時系列グラフ (Y軸の視認性向上) ---
        st.subheader("Interactive Monthly Projection")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time_axis, y=p_97_5, line=dict(color='rgba(255,165,0,0)', width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=time_axis, y=p_2_5, line=dict(color='rgba(255,165,0,0)', width=0), fill='tonexty', fillcolor='rgba(255,165,0,0.05)', name='2-sigma (95%)'))
        fig.add_trace(go.Scatter(x=time_axis, y=p_84, line=dict(color='rgba(40,167,69,0)', width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=time_axis, y=p_16, line=dict(color='rgba(40,167,69,0)', width=0), fill='tonexty', fillcolor='rgba(40,167,69,0.15)', name='1-sigma (68%)'))
        fig.add_trace(go.Scatter(x=time_axis, y=p_50, line=dict(color='#007bff', width=4), name='Median'))
        
        fig.update_layout(
            xaxis_title="Months", yaxis_title="Asset (10k JPY)", 
            hovermode="x unified", template="plotly_white", height=500,
            yaxis=dict(autorange=True, fixedrange=False) # ズームしやすく設定
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- 分布図 (ベルカーブ側) にターゲット線を表示 ---
        st.subheader("Final Asset Distribution & Targets")
        c1, c2 = st.columns([3, 1])
        
        with c1:
            fig_hist = go.Figure(data=[go.Histogram(x=final_values, nbinsx=100, marker_color='#6c757d', opacity=0.4, name='Distribution')])
            
            # ターゲット垂直線の設定
            targets_vals = [initial_asset, initial_asset * 1.5, initial_asset * 2, 10000]
            target_colors = ['#6f42c1', '#dc3545', '#fd7e14', '#20c997']
            target_names = ['Initial', '1.5x', '2.0x', '100M']
            
            for val, color, name in zip(targets_vals, target_colors, target_names):
                fig_hist.add_vline(x=val, line_dash="dash", line_color=color, 
                                   annotation_text=name, annotation_position="top right")
            
            # 中央値も太線で追加
            fig_hist.add_vline(x=p_50[-1], line_width=3, line_color="#007bff", annotation_text="Median")

            fig_hist.update_layout(xaxis_title="Final Asset (10k JPY)", yaxis_title="Count", template="plotly_white", height=450)
            st.plotly_chart(fig_hist, use_container_width=True)

        with c2:
            st.markdown("### Achievability")
            t_probs = [(np.sum(final_values >= t) / len(results)) * 100 for t in targets_vals]
            df_res = pd.DataFrame({"Target": target_names, "Prob (%)": [f"{p:.1f}%" for p in t_probs]})
            st.table(df_res)

        # リスク分析
        st.subheader("⚠️ Worst-Case Scenario Analysis")
        worst_final = int(p_5[-1])
        if worst_final <= 0:
            depletion_month = np.where(p_5 <= 0)[0][0]
            st.error(f"ワースト5%のシナリオでは、**{depletion_month}ヶ月目** に資産が底をつく可能性があります。")
        else:
            st.warning(f"最悪のケース（下位5%）でも、最終的に **{worst_final}万円** 残る計算です。")

else:
    st.info("サイドバーで数値を入力し、「シミュレーションを実行」ボタンを押してください。")