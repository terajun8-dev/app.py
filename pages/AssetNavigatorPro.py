import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 日本語表示の設定（環境に合わせて調整が必要な場合があります）
plt.rcParams['font.family'] = 'sans-serif' 

st.title("🛡️ 投資シミュレーター Pro")
st.caption("モンテカルロ法による標準偏差・ブラックスワン・4%ルール検証")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("基本設定")
    initial_asset = st.number_input("初期資産 (万円)", value=2000)
    mode = st.radio("モード選択", ["積立投資モード", "4%ルール取り崩しモード"])
    
    if mode == "積立投資モード":
        monthly_input = st.slider("毎月の積立額 (万円)", 0, 50, 10)
    else:
        monthly_input = 0 # 取り崩しモードでは積立は0
        
    years = st.slider("シミュレーション期間 (年)", 5, 50, 30)
    
    st.header("市場リスク設定")
    annual_return = st.slider("期待収益率 (%)", -5.0, 15.0, 5.0) / 100
    annual_volatility = st.slider("標準偏差/リスク (%)", 0.0, 30.0, 15.0) / 100
    
    st.header("オプション")
    use_inflation = st.checkbox("インフレ率を考慮（実質価値）", value=True)
    inflation_rate = st.slider("年間インフレ率 (%)", 0.0, 5.0, 2.0) / 100
    
    use_black_swan = st.checkbox("ブラックスワン（暴落）を考慮", value=True)
    if use_black_swan:
        bs_prob = st.slider("暴落発生確率 (年次 %)", 0.0, 10.0, 2.0) / 100
        bs_impact = st.slider("暴落時の下落率 (%)", -80, -10, -40) / 100

# --- シミュレーションロジック ---
def run_simulation():
    simulations = 2000 # Streamlitのレスポンス維持のため回数を調整
    months = years * 12
    dt = 1/12
    all_results = np.zeros((simulations, months + 1))
    all_results[:, 0] = initial_asset
    
    # 4%ルールの初期値
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
            if mode == "4%ルール取り崩しモード":
                current_asset -= current_withdrawal
                current_withdrawal *= (1 + inflation_rate)**(1/12)
            else:
                current_asset += monthly_input
            
            # インフレ調整
            val = current_asset
            if use_inflation:
                val /= (1 + inflation_rate)**(m/12)
            
            all_results[i, m] = max(0, val)
            
    return all_results

results = run_simulation()
time_axis = np.arange(years * 12 + 1) / 12

# --- メイン表示エリア ---
col1, col2 = st.columns(2)
median_final = np.median(results[:, -1])
failure_rate = np.sum(results[:, -1] <= 0) / len(results) * 100

with col1:
    st.metric("予測中央値 (最終)", f"{int(median_final)} 万円")
with col2:
    st.metric("資産枯渇確率", f"{failure_rate:.1f} %", delta_color="inverse")

# グラフ作成
fig, ax = plt.subplots(figsize=(10, 5))
median = np.median(results, axis=0)
ax.plot(time_axis, median, color='#1f77b4', lw=2, label='中央値')

# 標準偏差のバンド
ax.fill_between(time_axis, np.percentile(results, 16, axis=0), np.percentile(results, 84, axis=0), 
                color='#1f77b4', alpha=0.3, label='±1σ (確率68%)')
ax.fill_between(time_axis, np.percentile(results, 2.5, axis=0), np.percentile(results, 97.5, axis=0), 
                color='#1f77b4', alpha=0.1, label='±2σ (確率95%)')

ax.set_title(f"{mode} シミュレーション結果")
ax.set_xlabel("年数")
ax.set_ylabel("資産 (万円)")
ax.legend()
ax.grid(True, alpha=0.3)

st.pyplot(fig)

st.info("💡 **見方**: 中央の濃い線が最も可能性が高い推移です。薄い青色の範囲（±2σ）から下側に突き抜ける場合は、歴史的な暴落が重なったケースを意味します。")