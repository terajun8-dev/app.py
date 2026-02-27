import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re

st.set_page_config(page_title="PlotWizard: Final Master", layout="wide")
st.title("🧙‍♂️ PlotWizard: Master Visualizer")

uploaded_file = st.file_uploader("ファイルをドロップ", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    try:
        raw_bytes = uploaded_file.getvalue()
        if uploaded_file.name.endswith('.csv'):
            try: df_raw = pd.read_csv(io.BytesIO(raw_bytes), encoding='utf-8', header=None)
            except: df_raw = pd.read_csv(io.BytesIO(raw_bytes), encoding='cp932', header=None)
        else:
            engine = 'xlrd' if uploaded_file.name.endswith('.xls') else 'openpyxl'
            df_raw = pd.read_excel(io.BytesIO(raw_bytes), header=None, engine=engine)

        # --- 🛠️ サイドバー設定 ---
        st.sidebar.subheader("🛠️ データ読み込み設定")
        has_header = st.sidebar.radio("見出し（項目名）の有無", ["あり", "なし（1行目からデータ）"], index=0)
        
        if has_header == "あり":
            header_row = st.sidebar.number_input("見出しがある行番号", 0, len(df_raw)-1, 0)
            data_start_row = header_row + 1
        else:
            header_row = None
            data_start_row = 0

        st.sidebar.subheader("🧹 データクレンジング")
        skip_input = st.sidebar.text_input("除外する行番号", "")
        skip_rows = [int(x.strip()) for x in re.split(r'[,|，|\s]+', skip_input) if x.strip().isdigit()]
        
        exclude_kw_input = st.sidebar.text_area("除外するキーワード", height=100)
        exclude_keywords = [x.strip() for x in re.split(r'[,|，|\n]+', exclude_kw_input) if x.strip()]

        st.sidebar.subheader("🏷️ 補完・レポート設定")
        col_nan_rep = st.sidebar.text_input("見出しの空欄名", "項目名なし")
        data_nan_rep = st.sidebar.text_input("データの空欄名", "(データなし)")
        chart_title_input = st.sidebar.text_input("グラフタイトル", "分析結果")
        custom_x_label = st.sidebar.text_input("X軸のラベル名", "")
        custom_y_label = st.sidebar.text_input("Y軸のラベル名", "")
        custom_color_label = st.sidebar.text_input("凡例（色分け）のラベル名", "")
        data_source_input = st.sidebar.text_input("出典表示", "SSDSE-A-2025")

        # --- ⚙️ データ再構築 ---
        if header_row is not None:
            raw_cols = df_raw.iloc[header_row].tolist()
            clean_columns = []
            counts = {}
            for c in raw_cols:
                c_str = str(c).strip()
                if c_str.lower() in ['nan', '', 'none']: c_str = col_nan_rep
                c_str = c_str.replace('\n', ' ')
                if c_str in counts:
                    counts[c_str] += 1
                    clean_columns.append(f"{c_str}({counts[c_str]})")
                else:
                    counts[c_str] = 1
                    clean_columns.append(c_str)
        else:
            clean_columns = [f"列{i+1}" for i in range(df_raw.shape[1])]

        df = df_raw.iloc[data_start_row:].copy()
        df.columns = clean_columns
        df = df.reset_index(drop=False).rename(columns={'index': '元行'})
        
        if skip_rows: df = df[~df['元行'].isin(skip_rows)]
        if exclude_keywords:
            data_cols = [c for c in df.columns if c != '元行']
            for kw in exclude_keywords:
                df = df[~df[data_cols].apply(lambda row: row.astype(str).str.contains(kw).any(), axis=1)]

        df = df.fillna(data_nan_rep).replace(["nan", "NaN", ""], data_nan_rep)

        # --- 🛡️ データ型保護 ---
        for col in df.columns:
            if col == '元行': continue
            series = df[col].astype(str).str.strip()
            if series.str.contains(r'[-ー〜~—/:]').any():
                continue
            temp_numeric = pd.to_numeric(series.str.replace(',', ''), errors='coerce')
            if temp_numeric.notnull().sum() > len(df) * 0.8:
                df[col] = temp_numeric

        st.subheader("📝 データプレビュー")
        st.dataframe(df.head(100), height=200)

        # --- 📊 グラフ描画 ---
        st.divider()
        cols = df.columns.tolist()
        c1, c2 = st.columns(2)
        with c1:
            search_col = st.selectbox("分析の基準列", cols, index=min(1, len(cols)-1))
            selected_keywords = st.multiselect("🔍 絞り込み", options=df[search_col].unique().tolist())
        
        filtered_df = df[df[search_col].isin(selected_keywords)] if selected_keywords else df.copy()

        g1, g2, g3 = st.columns(3)
        with g1: x_col = st.selectbox("項目列", cols, index=cols.index(search_col))
        with g2: y_col = st.selectbox("数値列", ["(件数カウント)"] + cols, index=min(2, len(cols)))
        with g3: color_col = st.selectbox("色分け", [None] + cols, index=0)

        f1, f2, f3 = st.columns(3)
        with f1: chart_type = st.radio("形式", ["棒", "線", "点"], horizontal=True)
        with f2: barmode_choice = st.radio("表示オプション", ["並列", "積み上げ", "積み上げ(100%)"], horizontal=True)
        with f3: orient = st.radio("向き", ["縦", "横"], horizontal=True)

        if st.button("グラフを描画"):
            plot_data = filtered_df.copy()
            y_target = y_col
            if y_col == "(件数カウント)":
                group_cols = [x_col]
                if color_col: group_cols.append(color_col)
                plot_data = plot_data.groupby(group_cols).size().reset_index(name='件数')
                y_target = "件数"

            if orient == "横":
                x_lab, y_lab = (custom_y_label or y_target), (custom_x_label or x_col)
            else:
                x_lab, y_lab = (custom_x_label or x_col), (custom_y_label or y_target)
            
            labels_dict = {x_col: x_lab, y_target: y_lab}
            if color_col:
                labels_dict[color_col] = custom_color_label if custom_color_label else color_col

            # 共通引数の設定（barmode以外）
            fig_args = {
                "data_frame": plot_data, 
                "x": y_target if orient == "横" else x_col,
                "y": x_col if orient == "横" else y_target,
                "orientation": 'h' if orient == "横" else 'v',
                "color": color_col,
                "template": "plotly_dark",
                "title": chart_title_input,
                "labels": labels_dict
            }
            
            if chart_type == "棒": 
                # 棒グラフのみ barmode を適用
                mode = "group" if barmode_choice == "並列" else "stack"
                fig = px.bar(**fig_args, barmode=mode, text_auto=True)
                
                if barmode_choice == "積み上げ(100%)":
                    fig.update_layout(barnorm='percent')
                    fig.update_traces(texttemplate='%{value:.1f}%', textposition='inside')
            elif chart_type == "点": 
                fig = px.scatter(**fig_args)
            else: 
                fig = px.line(**fig_args, markers=True)

            fig.update_layout(
                margin=dict(b=120, t=80),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            if data_source_input:
                fig.add_annotation(
                    xref="paper", yref="paper", x=0.5, y=-0.3,
                    text=f"出典: {data_source_input}",
                    showarrow=False, font=dict(size=11, color="gray"), align="center"
                )

            st.plotly_chart(fig, use_container_width=True)

        # --- 💾 賢い保存 ---
        st.divider()
        export_df = filtered_df.drop(columns=['元行']) if '元行' in filtered_df.columns else filtered_df
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Sheet1')
        excel_data = output.getvalue()

        st.download_button(
            label="📥 データをExcelで保存",
            data=excel_data,
            file_name="wizard_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
else:
    st.info("ファイルをアップロードしてください。")