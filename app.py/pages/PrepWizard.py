import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="PrepWizard", layout="wide")
st.title("🪄 PrepWizard")

uploaded_file = st.file_uploader("ファイルをアップロード", type=["csv", "xlsx", "xls"])

# ファイルが変更されたら状態を完全にリセット
if uploaded_file:
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    if "current_file" not in st.session_state or st.session_state.current_file != file_key:
        st.session_state.current_file = file_key
        if 'step1_df' in st.session_state: del st.session_state.step1_df
        if 'final_df' in st.session_state: del st.session_state.final_df

    try:
        raw_bytes = uploaded_file.getvalue()
        if uploaded_file.name.endswith('.csv'):
            try: df_raw = pd.read_csv(io.BytesIO(raw_bytes), header=None)
            except: df_raw = pd.read_csv(io.BytesIO(raw_bytes), encoding='cp932', header=None)
        else:
            df_raw = pd.read_excel(io.BytesIO(raw_bytes), header=None)
        
        # 初期表示時の列名を強制連番にして重複エラーを物理的に回避
        df_raw.columns = [f"Col_{i}" for i in range(df_raw.shape[1])]
        df_raw = df_raw.fillna("nan")
        
    except Exception as e:
        st.error(f"読込エラー: {e}")
        st.stop()

    # --- ステップ1: 見出し行の確定 ---
    st.divider()
    st.subheader("🛠️ ステップ1: 見出し行の確定")
    
    col_a, col_b = st.columns([1, 2])
    header_idx = col_a.number_input("見出し（項目名）がある行番号", 0, len(df_raw)-1, 0)

    if st.button("この行を見出しとして確定"):
        row_values = df_raw.iloc[header_idx].astype(str).tolist()
        new_cols = []
        counts = {}
        for i, val in enumerate(row_values):
            clean_name = val.strip()
            # 空欄(nan)対策
            if clean_name.lower() in ["nan", ""]:
                clean_name = f"項目{i}"
            
            # 重複列名対策（連番付与）
            if clean_name in counts:
                counts[clean_name] += 1
                unique_name = f"{clean_name}_{counts[clean_name]}"
            else:
                counts[clean_name] = 0
                unique_name = clean_name
            new_cols.append(unique_name)
        
        # データの切り出し
        df_step1 = df_raw.iloc[header_idx + 1:].copy()
        df_step1.columns = new_cols
        # セッションに保存して画面更新
        st.session_state.step1_df = df_step1.replace("nan", "(空欄)").reset_index(drop=True)
        st.rerun()

    # 表示セクション（確定済みなら整形後、未確定なら生データを表示）
    if 'step1_df' in st.session_state:
        st.success("見出し確定済み")
        st.dataframe(st.session_state.step1_df.head(100), height=300)
    else:
        st.dataframe(df_raw.head(100), height=300)

    # --- ステップ2: アンピボット設定 ---
    if 'step1_df' in st.session_state:
        st.divider()
        st.subheader("🔄 ステップ2: アンピボット")
        df_work = st.session_state.step1_df.copy()
        current_cols = df_work.columns.tolist()

        c1, c2 = st.columns(2)
        # 固定する列の選択
        id_vars = c1.multiselect("固定する列（軸となる列）を選択", current_cols)
        
        # 固定列のリネーム設定（個別に名称変更可能）
        renamed_id_vars = {}
        if id_vars:
            st.info("固定列の名称を書き換える（例：項目2 → 相応しい名称）")
            id_rename_cols = st.columns(3)
            for i, col in enumerate(id_vars):
                new_name = id_rename_cols[i % 3].text_input(f"『{col}』の新名称", key=f"rename_{col}")
                if new_name:
                    renamed_id_vars[col] = new_name

        # 縦にまとめる数値列の選択
        remaining_cols = [c for c in current_cols if c not in id_vars]
        value_vars = c2.multiselect("縦にまとめる列を選択", remaining_cols, default=remaining_cols)

        # ラベルの設定（ユーザー提案の表現を採用）
        c3, c4 = st.columns(2)
        var_name = c3.text_input("縦にまとめる項目の名称", "項目")
        val_name = c4.text_input("数値列の名称（例：値、件数、金額）", "値")

        # オプション
        drop_empty = st.checkbox("数値が入っていない行（空行）を自動で削除する", value=True)

        if st.button("変換実行"):
            try:
                # 1. 軸のリネーム適用
                final_id_vars = []
                for v in id_vars:
                    if v in renamed_id_vars:
                        df_work = df_work.rename(columns={v: renamed_id_vars[v]})
                        final_id_vars.append(renamed_id_vars[v])
                    else:
                        final_id_vars.append(v)

                # 2. アンピボット（melt）
                df_final = df_work.melt(id_vars=final_id_vars, value_vars=value_vars, 
                                        var_name=var_name, value_name=val_name)
                
                # 3. 数値クレンジング（カンマ・空白を除去して数値化）
                df_final[val_name] = pd.to_numeric(
                    df_final[val_name].astype(str).str.replace(r'[,\s]', '', regex=True), 
                    errors='coerce'
                )
                
                # 4. 空行の削除
                if drop_empty:
                    df_final = df_final.dropna(subset=[val_name])
                
                st.session_state.final_df = df_final
                st.success("変換完了！ステップ3を確認してください。")
            except Exception as e:
                st.error(f"変換エラー: {e}")

    # --- ステップ3: 結果確認と保存 ---
    if 'final_df' in st.session_state:
        st.divider()
        st.subheader("📝 ステップ3: 結果確認と保存")
        st.write(f"変換後の総行数: {len(st.session_state.final_df)} 行")
        st.dataframe(st.session_state.final_df.head(100), height=300)

        # Excel出力バッファ作成
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.final_df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 縦持ち変換済みのExcelを保存",
            data=output.getvalue(), 
            file_name="prep_export.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )