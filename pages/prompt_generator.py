import streamlit as st

# ==========================================
# 1. スキル定義データ
# ==========================================
SKILLS_LIBRARY = {
    "リサーチ・分析系": {
        "strategic_researcher": {
            "name": "多角的分離思考調査",
            "desc": "事実と解釈を厳格に分離し、多角的な視点でレポートを生成します。",
            "philosophy": "客観的事実と多角的解釈を厳格に分離・構造化する論理分析エンジン。",
            "workflow": [
                "キーワード展開（日本語・英語・派生語）",
                "情報収集と「事実」「見解」「解釈」への分類",
                "肯定的・否定的・中立的視点による多角的分析",
                "出典との1対1対応確認"
            ]
        },
        "market_analyzer": {
            "name": "市場動向・競合分析",
            "desc": "市場規模、主要プレイヤー、トレンドを事実ベースで整理します。",
            "philosophy": "ビジネス環境における数値データと定性情報の構造化。",
            "workflow": ["市場規模の特定", "競合プレイヤーの戦略分析", "PEST分析等のフレームワーク適用"]
        }
    },
    "リスク・評価系": {
        "risk_assessor": {
            "name": "多角的リスク分析",
            "desc": "プロジェクトや事象に潜むリスクと機会を対立軸で抽出します。",
            "philosophy": "不確実性に対する「リスク」と「機会」の対比構造の明示。",
            "workflow": ["リスク因子の特定", "機会（メリット）の特定", "影響度と発生確率の推計"]
        },
        "geopolitical_analyst": {
            "name": "地政学・政策分析",
            "desc": "国際情勢や政策動向を、公的情報の信頼度を重視して分析します。",
            "philosophy": "国家・政策レベルの動向における中立性と一次ソースの優先。",
            "workflow": ["公式発表・法令の確認", "域内メディアと国際メディアの比較", "シナリオ予測"]
        }
    },
    "技術・開発系": {
        "tech_fact_checker": {
            "name": "技術事実検証",
            "desc": "技術仕様やデータシートの事実確認と信頼度判定を行います。",
            "philosophy": "技術的エビデンスのクロスチェックと、ハルシネーションの排除。",
            "workflow": ["公式ドキュメントの参照", "ベンチマーク・検証データの比較", "技術적制約の特定"]
        },
        "env_architect": {
            "name": "環境構築・最適化",
            "desc": "実装手順を「最短・正確」のプロトコルで出力します。",
            "philosophy": "再現性と効率を重視した、ステップバイステップの実行指示。",
            "workflow": ["前提条件の整理", "最短ステップの設計", "トラブルシューティング案の提示"]
        }
    }
}

# ==========================================
# 2. プロンプト生成ロジック（継続指示付き）
# ==========================================
def generate_prompt(skill, topic):
    workflow_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(skill['workflow'])])
    
    return f"""# Role: {skill['name']}基盤 分析エンジン

# Topic: {topic}

# Instruction:
以下の「実装フィロソフィー」と「実行手順」を厳格に遵守し、指定の「出力テンプレート」に従って回答を生成してください。

## 1. 実装フィロソフィー
- {skill['philosophy']}
- 客観的事実 と 多角的解釈 を厳格に分離・構造化する。
- 特定の立場に依存しない中立性を保持する。
- 全ての主張に [N] 形式で出典番号を付与し、末尾のリストと1対1対応させる。

## 2. 実行手順
{workflow_str}

## 3. 禁止表現（中立性プロトコル）
「〜すべき」「〜に違いない」「明らかに〜」といった主観的断定を禁止します。

## 4. 出力テンプレート
以下のMarkdown構造で出力してください。

---
# 【サマリー】
[核心を1-2行で記述。出典番号必須]

# 【客観的事実（Facts）】
## [セクション名]
- 事実内容 [出典1][出典2]

# 【多角的分析（Multi-Angle Analysis）】
## [テーマ]に対する見方
### 【肯定的/推進派視点】
- 内容 [出典3]
### 【否定的/慎重派視点】
- 内容 [出典4]

# 【インプリケーション（Implications）】
- 論理的帰結と将来シナリオ

# 【詳細出典リスト】
| 出典 | URL | 信頼度 | 分類 |
|-----|-----|-------|------|
| [1] | ... | 高 | 公式 |
---

## 💡 継続的な制約の保持（重要）
**このセッション中に行われる全ての追加質問・修正依頼に対しても、上記の「実装フィロソフィー」「禁止表現」「出力テンプレート（出典リストの付与）」を常に適用し続けてください。** ユーザーが「指示を解除する」と明示的に述べるまで、このプロトコルを解除してはいけません。

それでは、上記手順を厳格に守り、{topic}について調査を開始してください。"""

# ==========================================
# 3. Streamlit UI
# ==========================================
st.set_page_config(page_title="Strategic Prompt Engine", layout="centered")

# カスタムCSS
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 14px; }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #0078d4;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Strategic Prompt Engine")

col1, col2 = st.columns(2)
with col1:
    selected_cat = st.selectbox("1. 分野を選択", options=list(SKILLS_LIBRARY.keys()))
with col2:
    skill_options = SKILLS_LIBRARY[selected_cat]
    selected_skill_id = st.selectbox(
        "2. スキルを選択", 
        options=list(skill_options.keys()),
        format_func=lambda x: skill_options[x]["name"]
    )

skill_data = skill_options[selected_skill_id]
st.info(f"**Skill Description:** {skill_data['desc']}")

topic = st.text_input("3. 調査テーマ（Topic）を入力", placeholder="例：欧州におけるAI規制動向")

st.markdown("---")

if st.button("Generate"):
    if topic:
        final_prompt = generate_prompt(skill_data, topic)
        st.subheader("📋 生成されたプロンプト")
        st.caption("右上のアイコンをクリックしてコピーし、Copilotへ貼り付けてください。")
        st.code(final_prompt, language="markdown")
        
        with st.expander("🔍 生成内容のプレビューを確認"):
            st.markdown(final_prompt)
    else:
        st.error("調査テーマを入力してからGenerateボタンを押してください。")

st.markdown("---")
st.caption("Powered by Multi-Angle Separation Protocol v1")