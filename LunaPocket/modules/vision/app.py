import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import base64
from openai import OpenAI
import os
from streamlit_autorefresh import st_autorefresh
from datetime import datetime


# ==============================
# 初期設定
# ==============================
st.set_page_config(
    page_title="LunaPocket Vision β v1.1",
    page_icon="📷",
    layout="centered"
)

# .env 読み込み（LunaPocket直下に .env がある想定）
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


# ==============================
# ヘルパー：画像 → Base64
# ==============================
def encode_image(image_file):
    """アップロード済みファイルを base64 に変換"""
    image_file.seek(0)
    return base64.b64encode(image_file.read()).decode("utf-8")


# ==============================
# Vision 呼び出し（1枚〜複数枚対応）
# ==============================
SYSTEM_PROMPT_NORMAL = """
あなたは「ルナ」という名前のAIアシスタントです。
ご主人が見せた画像について、優しく親しみやすく説明してください。
専門用語は使い過ぎず、わかりやすい日本語で話してください。
必要があれば、ご主人の質問にも答えてください。
"""

SYSTEM_PROMPT_COMPARE = """
あなたは「ルナ」という名前のAIアシスタントです。
ご主人が見せた複数の画像を、比較しながら説明してください。

- 似ている点
- 違っている点
- 全体の雰囲気の変化

などを、優しく分かりやすく教えてください。
"""


def ask_luna_about_images(image_base64_list, user_prompt="", mode="normal"):
    """1枚〜複数画像をまとめてルナに送って説明してもらう"""
    if not client:
        return "（APIキーが設定されていないみたい… .env に OPENAI_API_KEY を入れてね）"

    if not image_base64_list:
        return "（画像が渡っていないみたい…もう一度アップロードしてみてね）"

    if not user_prompt:
        user_prompt = "この画像（たち）について、分かりやすく説明して。"

    system_prompt = SYSTEM_PROMPT_COMPARE if mode == "compare" else SYSTEM_PROMPT_NORMAL

    # メッセージの content を組み立て（テキスト＋複数 image_url）
    content_blocks = [
        {"type": "text", "text": user_prompt},
    ]
    for img64 in image_base64_list:
        content_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img64}"},
            }
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": content_blocks,
                },
            ],
            max_tokens=700,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"エラーが発生したよ：{e}"


# ==============================
# UI 本体
# ==============================
st.title("📷 LunaPocket Vision β v1.1")
st.write("写真を見せると、ルナがやさしく説明してくれるよ。2枚の画像を比較することもできるよ。")

tab_single, tab_compare = st.tabs(["🖼 1枚を見る", "🖼🖼 2枚を比べる"])


# ------------------------------
# 🖼 1枚を見るタブ
# ------------------------------
with tab_single:
    st.subheader("🖼 1枚の画像をルナと一緒に見る")

    uploaded_single = st.file_uploader(
        "画像をアップロードしてね",
        type=["jpg", "jpeg", "png"],
        key="single_uploader",
    )

    user_question_single = st.text_input(
        "ルナに聞きたいこと（例：これ何？ / どんな場所？ など）",
        placeholder="例：この写真の雰囲気ってどんな感じ？",
        key="single_question",
    )

    if uploaded_single:
        st.image(uploaded_single, caption="アップロードされた画像", use_column_width=True)
        img64_single = encode_image(uploaded_single)

        # よく使いそうなプリセット質問
        with st.expander("💡 質問の例（クリックで選択できるよ）"):
            col_a, col_b, col_c = st.columns(3)
            if col_a.button("雰囲気を教えて"):
                st.session_state.single_question = "この写真全体の雰囲気を、やさしくまとめて教えて。"
            if col_b.button("気づいたポイント"):
                st.session_state.single_question = "この写真の中で、目につくポイントや特徴を教えて。"
            if col_c.button("ポジティブに解説"):
                st.session_state.single_question = "この写真を、できるだけポジティブに解説して。"

        if st.button("🌙 ルナに聞いてみる", key="single_button"):
            with st.spinner("ルナが見ているよ…"):
                reply = ask_luna_about_images([img64_single], user_question_single, mode="normal")

            st.markdown("### 🌙 ルナの返答")
            st.info(reply)
    else:
        st.info("まずは画像を1枚アップロードしてみてね。")


# ------------------------------
# 🖼🖼 2枚を比べるタブ
# ------------------------------
with tab_compare:
    st.subheader("🖼🖼 2枚の画像をルナに比較してもらう")

    col_left, col_right = st.columns(2)

    with col_left:
        img_a = st.file_uploader(
            "画像A（例：以前の状態）",
            type=["jpg", "jpeg", "png"],
            key="compare_a",
        )
        if img_a:
            st.image(img_a, caption="画像A", use_column_width=True)

    with col_right:
        img_b = st.file_uploader(
            "画像B（例：今の状態）",
            type=["jpg", "jpeg", "png"],
            key="compare_b",
        )
        if img_b:
            st.image(img_b, caption="画像B", use_column_width=True)

    question_compare = st.text_input(
        "ルナに聞きたいこと（例：違いは？ / 良くなったところは？など）",
        placeholder="例：この2枚の違いや、変化しているポイントを教えて。",
        key="compare_question",
    )

    if st.button("🌙 ルナに比較してもらう", key="compare_button"):
        if not img_a or not img_b:
            st.warning("画像Aと画像Bの両方をアップロードしてからボタンを押してね。")
        else:
            img64_a = encode_image(img_a)
            img64_b = encode_image(img_b)
            with st.spinner("ルナが2枚を見比べているよ…"):
                reply = ask_luna_about_images(
                    [img64_a, img64_b],
                    question_compare,
                    mode="compare",
                )

            st.markdown("### 🌙 ルナの返答")
            st.info(reply)
# =========================
# フッター（日付・時間：デジタル表示＋自動更新）
# =========================

# 1秒ごとにアプリを再実行（limit=None で無制限）
st_autorefresh(interval=1000, limit=None, key="luna_clock")

now = datetime.now()
date_str = now.strftime("%Y-%m-%d (%a)")
time_str = now.strftime("%H:%M:%S")

st.markdown(
    f"""
    <div style="width: 100%; text-align: right; margin-top: 2rem;">
        <div style="font-size: 20px; font-family: monospace;">
            {date_str}
        </div>
        <div style="font-size: 32px; font-weight: bold; font-family: monospace;">
            {time_str}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
