import streamlit as st

st.set_page_config(page_title="My Toolbox", layout="centered")

st.title("🧰 My Toolbox")
st.write("---")
st.write("Choose the tool you want to use from the menu on the left!")
st.info("New: `Digital Signage` を pages から開くと、天気・ニュース・株価・GitHub CLI ガイド演出の自動切替画面を開けます。")
st.caption("受付ディスプレイや情報ボード向けの本番デザイン案として追加しました。")
st.page_link("pages/digital_signage.py", label="Open Digital Signage", icon="🖥️")

# 作成日
st.info("Opened on 2026.02.15")
