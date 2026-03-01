import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- ページ設定 ---
st.set_page_config(page_title="Asset Navigator Pro", layout="wide")

st.title("📈 Asset Navigator Pro")
st.caption("モンテカルロ法による標準偏差・ブラックスワン・4%ルール検証")

# --- サイドバー設定 (日本語) ---
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
    if use_inflation:
        inflation_rate = st.slider("年間インフレ率 (%)", 0.0, 5.0, 2.0) / 100
    else:
        inflation_rate = 0.0
    
    use_black_swan = st.checkbox("ブラックスワン (暴落) を考慮", value=True)
    if use_black_swan:
        bs_prob = st.slider("発生確率 (年次 %)", 0.0, 10.0, 2.0) / 100
        bs_impact = st.slider("下落率 (%)", -80, -10, -40) / 100

# --- シミュレーションロジック ---
def run_simulation():
    simulations = 3000  # 試行回数
    months = years * 12
    dt = 1/12
    all_results = np.zeros((simulations, months + 1))
    all_results[:, 0] = initial_asset
    
    # 4%ルールの初期取り崩し額
    initial_withdrawal_monthly = (initial_asset * 0.04) / 12

    for i in range(simulations):
        current_asset = initial_asset
        current_withdrawal = initial_withdrawal_monthly
        
        for m in range(1, months + 1):
            # 市場変動
            noise = np.random.normal(0, 1)
            growth = np.exp((annual_return - 0.5 * annual_volatility**2) * dt + 
                            annual_volatility * np.sqrt(dt) * noise)
            
            # ブラックスワン判定
            if use_black_swan and np.random.rand() < (bs_prob / 12):
                growth *= (1 + bs_impact)
            
            current_asset *= growth
            
            # 資金移動
            if "Withdrawal" in mode:
                current_asset -= current_withdrawal
                current_withdrawal *= (1 + inflation_rate)**(1/12)
            else:
                current_asset += monthly_investment
            
            # インフレ調整
            val = current_asset
            if use_inflation:
                val /= (1 + inflation_rate)**(m/12)
            
            all_results[i, m] = max(0, val)
            
    return all_results

results = run_simulation()
time_axis = np.arange(years * 12 + 1) / 12

# --- 指標表示 ---
median_final = np.median(results[:, -1])
failure_rate = (np.sum(results[:, -1] <= 0) / len(results)) * 100

col1, col2 = st.columns(2)
col1.metric("Median Final Asset (中央値)", f"{int(median_final)} 万円")
col2.metric("Failure Rate (資産枯渇確率)", f"{failure_rate:.1f} %", delta_color="inverse")

# --- グラフ表示 (視覚的な区別を強化) ---
fig, ax = plt.subplots(figsize=(10, 6))

# 各パーセンタイルの計算
p_50 = np.median(results, axis=0)
p_84 = np.percentile(results, 84, axis=0)
p_16 = np.percentile(results, 16, axis=0)
p_97_5 = np.percentile(results, 97.5, axis=0)
p_2_5 = np.percentile(results, 2.5, axis=0)

# 1. 最も外側の範囲 (±2σ / 95% 確率)
ax.plot(time_axis, p_97_5, color='#1f77b4', linestyle='--', lw=1, alpha=0.4)
ax.plot(time_axis, p_2_5, color='#1f77b4', linestyle='--', lw=1, alpha=0.4)
ax.fill_between(time_axis, p_2_5, p_97_5, color='#1f77b4', alpha=0.07, label='2-sigma Range (95% Prob.)')

# 2. 内側の範囲 (±1σ / 68% 確率) - 網掛け(hatch)を追加
ax.fill_between(time_axis, p_16, p_84, color='#1f77b4', alpha=0.2, 
                hatch='///', edgecolor='#1f77b4', linewidth=0, label='1-sigma Range (68% Prob.)')

# 3. 中央値 (最も太い実線)
ax.plot(time_axis, p_50, color='#1f77b4', lw=3, label='Median (Most Likely)')

# グラフのラベル設定 (英語)
ax.set_title(f"Asset Projection: {mode}", fontsize=14, pad=20)
ax.set_xlabel("Years", fontsize=10)
ax.set_ylabel("Asset Balance (10k JPY)", fontsize=10)
ax.axhline(0, color='black', lw=1.5, alpha=0.7)
ax.legend(loc='upper left', frameon=True, shadow=True)
ax.grid(True, linestyle=':', alpha=0.6)

st.pyplot(fig)

# --- ヒストグラム ---
st.subheader("Final Asset Distribution")
fig_hist, ax_hist = plt.subplots(figsize=(10, 3))
ax_hist.hist(results[:, -1], bins=50, color='skyblue', edgecolor='white', alpha=0.8)
ax_hist.axvline(median_final, color='red', linestyle='--', label='Median')
ax_hist.set_title("Distribution of Outcomes at Final Year")
ax_hist.set_xlabel("Asset Value (10k JPY)")
ax_hist.set_ylabel("Frequency")
ax_hist.legend()
st.pyplot(fig_hist)

st.info("💡 **Tips:** \n- **Median (濃い線)**: 半数のシナリオがこれより上、半数が下になります。\n- **1-sigma (斜線)**: 最も現実的に起こりうる範囲です。\n- **2-sigma (薄い範囲)**: 稀ですが、最悪・最良のケースを含みます。破線が0に触れている場合、破綻のリスクがあります。")
