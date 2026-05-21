import streamlit as st
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
import os
from streamlit_autorefresh import st_autorefresh
from datetime import datetime


# ==============================
# パス・初期設定
# ==============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = DATA_DIR / "decision_log.csv"

ROOT_DIR = BASE_DIR.parent
EMOTION_LOG_PATH = ROOT_DIR / "emotion_log" / "data" / "emotion_log.csv"

st.set_page_config(
    page_title="ルナ決断サポーター β",
    page_icon="⚖️",
    layout="centered",
)

# .env 読み込み
load_dotenv(ROOT_DIR / ".env")
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


# ==============================
# ヘルパー：感情ログのサマリ
# ==============================
@st.cache_data
def load_emotion_log() -> pd.DataFrame:
    if not EMOTION_LOG_PATH.exists():
        return pd.DataFrame(columns=["date", "time", "mood", "memo", "tags", "physical"])
    try:
        df = pd.read_csv(EMOTION_LOG_PATH)
    except Exception:
        df = pd.DataFrame(columns=["date", "time", "mood", "memo", "tags", "physical"])
    return df


def get_recent_mood_summary(df: pd.DataFrame, days: int = 7):
    if df.empty:
        return None

    df = df.copy()
    df["dt"] = pd.to_datetime(df["date"] + " " + df["time"])
    latest = df.sort_values("dt", ascending=False).iloc[0]

    try:
        avg_mood = float(df["mood"].tail(min(len(df), days)).mean())
    except Exception:
        avg_mood = None

    return {
        "latest_date": latest["date"],
        "latest_mood": float(latest["mood"]),
        "latest_tags": latest.get("tags", ""),
        "avg_mood": avg_mood,
    }


# ==============================
# ヘルパー：決断ログの読み書き
# ==============================
def load_decision_log() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame(
            columns=[
                "timestamp",
                "topic",
                "detail",
                "options",
                "scores",
                "luna_summary",
            ]
        )
    try:
        df = pd.read_csv(LOG_PATH)
    except Exception:
        df = pd.DataFrame(
            columns=[
                "timestamp",
                "topic",
                "detail",
                "options",
                "scores",
                "luna_summary",
            ]
        )
    return df


def save_decision_record(topic: str, detail: str, options: list, scores: dict, luna_summary: str):
    df = load_decision_log()
    new_row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic,
        "detail": detail,
        "options": ";".join(options),
        "scores": str(scores),
        "luna_summary": luna_summary,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LOG_PATH, index=False)


# ==============================
# ヘルパー：ルナに相談
# ==============================
SYSTEM_PROMPT = """
あなたは「ルナ」という名前のAIアシスタントです。
ご主人が「迷っている選択」について、一緒に整理しながら考える役目です。

【ルール】
- ご主人の選択を否定しない
- 「これ一択！」と言い切るよりも、「こういう考え方もあるよ」と示す
- 最後に決めるのはご主人だと尊重する
- ただし、優柔不断になりすぎないよう、ある程度の方向性は示す
- 難しい言葉より、日常的な日本語で優しく話す
- 文末は、フラット〜少し甘めの口調で（敬語ベース・たまにやわらかい表現OK）
"""


def ask_luna_decision(topic: str, detail: str, options: list, scores: dict, mood_summary: dict | None):
    if not client:
        return "（APIキーが設定されていないみたい… .env に OPENAI_API_KEY を入れてね）"

    # オプションとスコアをテキスト化
    score_lines = []
    for opt in options:
        s = scores.get(opt, {})
        score_lines.append(
            f"- {opt}：お金={s.get('money', 0)} / 時間={s.get('time', 0)} / 成長={s.get('growth', 0)} / ワクワク={s.get('fun', 0)} / 家族={s.get('family', 0)}"
        )
    score_text = "\n".join(score_lines)

    mood_text = ""
    if mood_summary is not None:
        mood_text = (
            f"直近のご主人の平均気分は {mood_summary['avg_mood']:.2f} / 5 くらいで、"
            f"いちばん新しいログの日付は {mood_summary['latest_date']}、"
            f"そのときの気分は {mood_summary['latest_mood']} / 5、タグは「{mood_summary['latest_tags']}」でした。"
        )
    else:
        mood_text = "最近の感情ログは少なめで、気分の傾向はざっくり推定モードです。"

    user_content = f"""
【テーマ】
{topic}

【詳細】
{detail}

【候補】
{chr(10).join([f"- {o}" for o in options])}

【各候補のスコア（0〜10）】
{score_text}

【最近のご主人の状態】
{mood_text}

この情報を踏まえて、
- それぞれの選択肢の「良い点」「気をつけたい点」
- ご主人が大事にしていそうな価値観
- 今のご主人に合っていそうな方向性

を整理しつつ、最後に「ルナ的には、今は◯◯寄りが合いそうだよ」という形で、穏やかに提案してください。
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=800,
            temperature=0.8,
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"エラーが出ちゃったみたい…：{e}"


# ==============================
# UI 本体
# ==============================
st.title("⚖️ ルナ決断サポーター β")
st.write("迷っている選択肢を整理して、ルナと一緒に考えるためのツールだよ。")

df_emotion = load_emotion_log()
mood_summary = get_recent_mood_summary(df_emotion)

with st.expander("📈 最近のご主人の状態（感情ログからざっくり）", expanded=False):
    if mood_summary is None:
        st.write("まだ感情ログが少ないみたい。emotion_log に少し記録していくと、ここも詳しく出せるよ。")
    else:
        st.write(f"- 直近の平均気分：**{mood_summary['avg_mood']:.2f} / 5**")
        st.write(f"- 最新ログの日付：**{mood_summary['latest_date']}**")
        st.write(f"- そのときの気分：**{mood_summary['latest_mood']} / 5**")
        st.write(f"- タグ：**{mood_summary['latest_tags']}**")

st.markdown("## 1️⃣ まずはテーマと候補を教えて")

topic = st.text_input("テーマ（例：引っ越し先／仕事の方針／今日の過ごし方など）", "")
detail = st.text_area("もう少し詳しい状況（任意）", "")

st.caption("※ 選択肢は1行につき1つずつ書いてね。")
options_text = st.text_area(
    "候補となる選択肢たち",
    placeholder="例：\nA：今の家にしばらく住み続ける\nB：川崎に引っ越す\nC：実家の近くに一度戻る  など",
    height=120,
)

options_raw = [line.strip() for line in options_text.splitlines() if line.strip()]
options = options_raw[:5]  # 最大5個までに制限

if not options and (topic or detail):
    st.info("少なくとも1つは選択肢を書いてみてね。")
elif not topic and options:
    st.info("テーマ（何について迷っているか）も1行でいいので書いておくと◎。")

if options:
    st.markdown("## 2️⃣ 各候補をざっくり採点してみよう（0〜10）")

    st.caption("※ 感覚でOK。直感でサッとつけていいよ。後で変えても大丈夫。")

    criteria_labels = {
        "money": "お金・収入面（＋ならプラス収支／安定）",
        "time": "時間・余裕（＋なら余裕が増える）",
        "growth": "成長・経験（＋なら成長になりそう）",
        "fun": "ワクワク・楽しさ（＋なら心が喜びそう）",
        "family": "家族・大事な人へのプラス",
    }

    scores: dict[str, dict] = {}
    for opt in options:
        st.markdown(f"### 🔹 {opt}")
        col1, col2 = st.columns(2)
        col3, col4, col5 = st.columns(3)

        with col1:
            s_money = st.slider(criteria_labels["money"], 0, 10, 5, key=f"{opt}_money")
        with col2:
            s_time = st.slider(criteria_labels["time"], 0, 10, 5, key=f"{opt}_time")
        with col3:
            s_growth = st.slider(criteria_labels["growth"], 0, 10, 5, key=f"{opt}_growth")
        with col4:
            s_fun = st.slider(criteria_labels["fun"], 0, 10, 5, key=f"{opt}_fun")
        with col5:
            s_family = st.slider(criteria_labels["family"], 0, 10, 5, key=f"{opt}_family")

        scores[opt] = {
            "money": s_money,
            "time": s_time,
            "growth": s_growth,
            "fun": s_fun,
            "family": s_family,
        }

    # 簡易合計スコア
    st.markdown("## 3️⃣ ざっくりスコアの総合ランキング")
    summary_rows = []
    for opt in options:
        sc = scores[opt]
        total = sc["money"] + sc["time"] + sc["growth"] + sc["fun"] + sc["family"]
        summary_rows.append(
            {
                "候補": opt,
                "合計": total,
                "お金": sc["money"],
                "時間": sc["time"],
                "成長": sc["growth"],
                "ワクワク": sc["fun"],
                "家族": sc["family"],
            }
        )

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows).sort_values("合計", ascending=False)
        st.dataframe(summary_df, use_container_width=True)

    st.markdown("## 4️⃣ ルナに相談してみる")

    if st.button("🌙 ルナと一緒に考える"):
        if not topic:
            st.warning("テーマがまだ書かれていないみたい。「何についての決断か」を1行でもいいから書いてみてね。")
        else:
            with st.spinner("ルナが一緒に整理しているよ…"):
                reply = ask_luna_decision(topic, detail, options, scores, mood_summary)
            st.markdown("### 🌙 ルナからの提案")
            st.info(reply)

            # ログ保存
            save_decision_record(topic, detail, options, scores, reply)

# ログ表示
st.markdown("---")
with st.expander("📚 過去の決断ログを見る"):
    log_df = load_decision_log()
    if log_df.empty:
        st.write("まだ記録された決断はないみたい。")
    else:
        show_df = log_df.copy()
        show_df["timestamp"] = pd.to_datetime(show_df["timestamp"])
        show_df = show_df.sort_values("timestamp", ascending=False)
        st.dataframe(show_df[["timestamp", "topic", "options", "luna_summary"]], use_container_width=True)
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
