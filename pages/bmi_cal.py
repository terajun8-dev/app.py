import streamlit as st

st.title("BMI Checker")

# ユーザー入力を受け取る
h = st.number_input("身長(cm)を入力してください", value=170.0)
w = st.number_input("体重(kg)を入力してください", value=60.0)

# 計算ボタン
if st.button("判定！"):
    bmi = w / ((h / 100) ** 2)
    st.write(f"あなたのBMIは **{bmi:.2f}** です。")
    
    if bmi < 18.5:
        st.info("少し痩せ気味ですね。しっかり食べましょう！")
    elif 18.5 <= bmi < 25:
        st.success("標準的な体型です。キープしましょう！")
    else:
        st.warning("肥満気味です。適度な運動を！")
