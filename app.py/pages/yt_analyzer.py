import streamlit as st
import yt_dlp
import pandas as pd
import plotly.express as px
from collections import Counter
import re

# 1. ページ構成（一番上に配置）
st.set_page_config(page_title="YouTube Insights", layout="wide")

# 2. UIデザインの適用
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stButton>button {
        width: 100%; border-radius: 2px; background-color: #1e293b; color: white;
        height: 3em; border: none; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎥 YouTube Content Insights")

# 3. データ取得関数
def get_stable_data(url):
    url = url.strip()
    if "@" in url and not url.endswith("/videos"):
        url = f"{url.split('?')[0].rstrip('/')}/videos"
    
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'force_json': True,
        'quiet': True,
        'playlist_items': '1-50',
        'ignoreerrors': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'entries' in info:
                # 取得できたデータのみをリスト化
                valid_entries = [e for e in info['entries'] if e]
                return valid_entries, info.get('title', 'Channel')
    except Exception as e:
        st.error(f"Error fetching data: {e}")
    return [], "Unknown"

# 4. メイン画面の構築
target_url = st.text_input("Channel URL", placeholder="https://www.youtube.com/@...")

if st.button("RUN 50-VIDEO ANALYSIS"):
    with st.spinner('Fetching data...'):
        entries, channel_name = get_stable_data(target_url)
        
        if entries:
            df = pd.DataFrame(entries)
            
            # 再生数のクレンジング
            if 'view_count' in df.columns:
                df['view_count'] = pd.to_numeric(df['view_count'], errors='coerce').fillna(0)
            else:
                df['view_count'] = 0
            
            # 古い順に並び替え
            df = df.iloc[::-1].reset_index(drop=True)
            df['Order'] = df.index + 1

            st.header(f"Results: {channel_name}")

            # --- 折れ線グラフ ---
            st.subheader("📈 Performance Trend (Views)")
            fig_line = px.line(df, x='Order', y='view_count', markers=True, 
                              hover_name='title', template="plotly_white", 
                              color_discrete_sequence=['#475569'])
            fig_line.update_layout(
                xaxis_title="Videos (Old → New)", 
                yaxis_title="Views",
                hovermode="x unified"
            )
            st.plotly_chart(fig_line, use_container_width=True)

            # --- キーワード分析 ---
            st.subheader("📊 Top Keywords")
            all_titles = " ".join(df['title'].astype(str).tolist()).lower()
            words = re.findall(r'\b\w{4,}\b', all_titles)
            stop = {'this','that','with','from','video','sulek','day','part','workout','about'}
            filtered_words = [w for w in words if w not in stop]
            
            if filtered_words:
                w_counts = Counter(filtered_words).most_common(20)
                w_df = pd.DataFrame(w_counts, columns=['Keyword', 'Count'])
                fig_bar = px.bar(w_df, x='Count', y='Keyword', orientation='h',
                                 color='Count', color_continuous_scale='Greys',
                                 template="plotly_white")
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- 動画リンク ---
            st.markdown("---")
            st.subheader("🔗 Video Links (Latest 50)")
            for _, row in df.iloc[::-1].iterrows():
                v_id = row.get('id')
                v_title = row.get('title', 'No Title')
                st.markdown(f"• [{v_title}](https://www.youtube.com/watch?v={v_id})")
        else:
            st.error("No data found or access blocked. Please wait 15 minutes.")

st.caption("v11.1 | Fixed Syntax for Python 3.13")