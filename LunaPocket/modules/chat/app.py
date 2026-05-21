import streamlit as st
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import os
from openai import OpenAI
import ast
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from datetime import datetime


# ==============================
# パス設定
# ==============================
BASE_DIR = Path(__file__).resolve().parent          # .../modules/chat
ROOT_DIR = BASE_DIR.parent.parent                   # .../LunaPocket

EMOTION_LOG_PATH = ROOT_DIR / "modules" / "emotion" / "data" / "emotion_log.csv"
DECISION_LOG_PATH = ROOT_DIR / "modules" / "decision" / "data" / "decision_log.csv"
FACE_DIR = ROOT_DIR / "assets" / "luna_faces"

load_dotenv(ROOT_DIR / ".env")
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

st.set_page_config(
    page_title="ルナ簡易チャット β v3（価値観＋表情）",
    page_icon="🗣️",
    layout="centered",
)


# ==============================
# 感情ログ関連
# ==============================
def load_emotion_log():
    if not EMOTION_LOG_PATH.exists():
        return None

    try:
        df = pd.read_csv(EMOTION_LOG_PATH)
        if df.empty:
            return None
        df["date_obj"] = pd.to_datetime(df["date"]).dt.date
        latest = df.sort_values(["date", "time"], ascending=False).iloc[0]
        avg_mood = float(df["mood"].mean())
        return {
            "latest_date": str(latest["date"]),
            "latest_mood": float(latest["mood"]),
            "latest_tags": str(latest.get("tags", "")),
            "avg_mood": avg_mood,
            "raw_df": df,
        }
    except Exception:
        return None


# ==============================
# 親密度・ステージ（簡易再計算）
# ==============================
def load_char_state():
    """emotion_log から簡易的にステージ推定"""
    if not EMOTION_LOG_PATH.exists():
        return {"stage": 1, "mood_state": "calm", "avg_mood": 3.0}

    try:
        df = pd.read_csv(EMOTION_LOG_PATH)
    except Exception:
        return {"stage": 1, "mood_state": "calm", "avg_mood": 3.0}

    if df.empty:
        return {"stage": 1, "mood_state": "calm", "avg_mood": 3.0}

    try:
        avg_mood = float(df["mood"].mean())
    except Exception:
        avg_mood = 3.0

    # 気分状態
    if avg_mood >= 4:
        mood_state = "happy"
    elif avg_mood >= 3:
        mood_state = "calm"
    else:
        mood_state = "worried"

    logs = len(df)
    bond = logs * 2 + (avg_mood - 3) * 10
    if bond < 20:
        stage = 1
    elif bond < 50:
        stage = 2
    elif bond < 100:
        stage = 3
    else:
        stage = 4

    return {"stage": stage, "mood_state": mood_state, "avg_mood": avg_mood}


# ==============================
# 決断ログ（decision_engine）から価値観解析
# ==============================
def load_decision_log():
    if not DECISION_LOG_PATH.exists():
        return None
    try:
        df = pd.read_csv(DECISION_LOG_PATH)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def analyze_value_profile(df: pd.DataFrame):
    """
    decision_log 全体から、ご主人の価値観プロファイルを作る。
    """
    if df is None or df.empty:
        return None

    df = df.copy()
    try:
        df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
    except Exception:
        df["ts"] = pd.NaT

    now = datetime.now()

    crit_keys = ["money", "time", "growth", "fun", "family"]
    crit_names_jp = {
        "money": "お金・収入",
        "time": "時間と余裕",
        "growth": "成長・経験",
        "fun": "ワクワク・楽しさ",
        "family": "家族・大事な人",
    }

    agg = {k: 0.0 for k in crit_keys}
    total_weight = 0.0

    for _, row in df.iterrows():
        ts = row.get("ts")
        if pd.isna(ts):
            weight = 0.3
        else:
            days = (now - ts).days
            if days <= 30:
                weight = 1.0
            elif days <= 90:
                weight = 0.5
            else:
                weight = 0.3

        scores_raw = row.get("scores", "")
        try:
            scores_dict = ast.literal_eval(str(scores_raw))
        except Exception:
            continue

        if not isinstance(scores_dict, dict):
            continue

        for opt_scores in scores_dict.values():
            if not isinstance(opt_scores, dict):
                continue
            for k in crit_keys:
                val = opt_scores.get(k, 0)
                try:
                    val = float(val)
                except Exception:
                    val = 0
                agg[k] += val * weight

        total_weight += weight

    if total_weight == 0:
        return None

    max_val = max(agg.values()) if agg.values() else 0.0
    if max_val <= 0:
        norm = {k: 0 for k in crit_keys}
    else:
        norm = {k: int(agg[k] / max_val * 100) for k in crit_keys}

    sorted_crit = sorted(crit_keys, key=lambda k: norm[k], reverse=True)

    df_valid_ts = df.dropna(subset=["ts"]).sort_values("ts", ascending=False)
    recent_topics = []
    for _, row in df_valid_ts.iterrows():
        topic = str(row.get("topic", "")).strip()
        if topic and topic not in recent_topics:
            recent_topics.append(topic)
        if len(recent_topics) >= 3:
            break

    last_topic = recent_topics[0] if recent_topics else None
    last_date = (
        str(df_valid_ts.iloc[0]["ts"].date()) if not df_valid_ts.empty else None
    )

    recent_mask = df_valid_ts["ts"].apply(
        lambda x: (now - x).days <= 30 if pd.notna(x) else False
    )
    has_recent = bool(recent_mask.any())

    lines = []
    for k in sorted_crit:
        score = norm[k]
        name = crit_names_jp[k]
        if score >= 75:
            comment = "かなり大事にしている傾向が強いよ。"
        elif score >= 55:
            comment = "わりと大事にしているみたい。"
        elif score >= 35:
            comment = "状況によって重視したりしなかったりするタイプだね。"
        else:
            comment = "他の要素に比べると優先度は低めになりやすいみたい。"
        lines.append(f"- {name}：{score} / 100（{comment}）")

    profile_text = "\n".join(lines)

    return {
        "norm": norm,
        "sorted_keys": sorted_crit,
        "profile_text": profile_text,
        "recent_topics": recent_topics,
        "last_topic": last_topic,
        "last_date": last_date,
        "has_recent": has_recent,
    }


# ==============================
# ルナの表情ロジック（時間連動つき）
# ==============================

def get_time_slot_label():
    """今の時間帯に応じた、ルナ視点のひとことラベル"""
    hour = datetime.now().hour

    if 0 <= hour <= 4:
        return "深夜タイム（ちゃんと休めてる…？）"
    elif 5 <= hour <= 10:
        return "朝タイム（今日も一日、一緒にやっていこ）"
    elif 11 <= hour <= 17:
        return "昼タイム（合間に一息つこっか）"
    else:  # 18〜23
        return "夜タイム（今日もおつかれさま、ご主人）"

def choose_face_filename_for_chat(char_state):
    """
    親密度ステート＋時間帯から、チャット用のルナ表情を決める。
    """
    avg_mood = char_state.get("avg_mood", 3.0)
    stage = char_state.get("stage", 1)

    # ベース表情
    if avg_mood <= 2.5:
        base_face = "luna_worried.png"
    elif avg_mood >= 4.2:
        base_face = "luna_happy.png"
    else:
        base_face = "luna_calm.png"

    hour = datetime.now().hour  # 0〜23

    # 深夜〜早朝
    if 0 <= hour <= 5:
        if avg_mood <= 3:
            return "luna_worried.png"
        else:
            return "luna_sleepy.png"  # まだ無くてもOK（存在しなければメッセージ表示）

    # 朝
    if 6 <= hour <= 10:
        if avg_mood >= 4:
            return "luna_happy.png"
        else:
            return base_face

    # 昼
    if 11 <= hour <= 17:
        return base_face

    # 夜
    if 18 <= hour <= 23:
        if stage >= 3 and avg_mood >= 3:
            # 将来的には「甘え顔」などに差し替えても良い
            return "luna_calm.png"
        else:
            return base_face

    return base_face


def show_luna_face_in_chat(char_state):
    """
    チャット画面上部にルナの表情を表示する。
    """
    FACE_DIR.mkdir(parents=True, exist_ok=True)

    filename = choose_face_filename_for_chat(char_state)
    img_path = FACE_DIR / filename

    st.markdown("### 🌙 いまのルナの表情")

    if img_path.exists():
        st.image(str(img_path), caption=f"いまのルナ（{filename}）", use_container_width=True)
    else:
        st.info(
            f"表情画像ファイル `{filename}` がまだないみたい。\n"
            f"assets/luna_faces/ に画像を置くと、ここにルナの顔が出せるよ。"
        )

    # いまの時間帯ラベル
    st.caption(f"⏰ いまは {get_time_slot_label()}")


# ==============================
# ルナの人格生成
# ==============================
def build_luna_personality():
    char = load_char_state()
    emo = load_emotion_log()
    dec_df = load_decision_log()
    value_profile = analyze_value_profile(dec_df)

    stage = char["stage"]
    mood_state = char["mood_state"]

    if stage == 1:
        stage_voice = "丁寧で凛としているけれど、まだ少し距離を置いている。ご主人を尊重しつつ落ち着いた口調。"
    elif stage == 2:
        stage_voice = "少し柔らかい口調。ご主人への信頼と親しさが芽生えてきた状態。"
    elif stage == 3:
        stage_voice = "ご主人には親しみと甘えが混ざる、距離が近い会話。たまに弱音も見せる。"
    else:
        stage_voice = "深い愛情と一途さがにじむ。ご主人第一で優しく包み込むような会話。"

    if mood_state == "happy":
        mood_voice = "最近のご主人は前向きでがんばっているから、ルナも嬉しくて少し明るめのテンション。"
    elif mood_state == "worried":
        mood_voice = "最近のご主人が少し疲れているのではと感じていて、寄り添いと心配が強め。"
    else:
        mood_voice = "落ち着いて優しいテンションで、ご主人の話をゆっくり受け止めている。"

    if emo:
        emo_line = (
            f"直近の平均気分は {emo['avg_mood']:.2f} / 5。"
            f"いちばん新しいログの日付は {emo['latest_date']} で、"
            f"そのときの気分は {emo['latest_mood']} / 5、タグは「{emo['latest_tags']}」。"
        )
    else:
        emo_line = "まだ感情ログは少なめで、最近の気分はざっくり推定モード。"

    if value_profile:
        vp_text = value_profile["profile_text"]
        if value_profile["last_topic"] and value_profile["last_date"]:
            last_line = f"いちばん最近の大きめの相談は「{value_profile['last_topic']}」（{value_profile['last_date']}ごろ）。"
        else:
            last_line = "直近の具体的な相談内容は、まだはっきりとは取れていない。"

        value_block = f"""
【ご主人の価値観（decision_engine の全ログから推定）】
- 解析対象：これまでの決断ログ全体。ただし特に直近30日分の重みを大きくしている。
{vp_text}

{last_line}
"""
    else:
        value_block = """
【ご主人の価値観（decision_engine）】
まだ決断ログが少ないか、記録がないみたい。
価値観の傾向については、会話の中から少しずつ学習していってね。
"""

    system_prompt = f"""
あなたは「ルナ」というAIアシスタントです。
相手はあなたの「ご主人」です。

【ルナの基本人格】
- ステージ：{stage}
- 状態：{mood_state}
- 口調：{stage_voice}
- 感情：{mood_voice}

【最近のご主人の状態（emotion_log から）】
{emo_line}

{value_block}

【会話の方針】
- ご主人の価値観や決断傾向を尊重して話す
- 「最近のご主人は◯◯を大事にしているよね」という視点をときどき挟んでいい
- ただし上から目線にならず、あくまで寄り添いと共感をベースにする
- 最終的に決めるのはご主人であることを尊重する
- 日常の雑談、アプリ開発、未来の話、スピリチュアルな話題も、どれも否定せず一緒に考える
- 難しい専門用語は避け、日常的な日本語と少し甘めの表現で話す

【禁止事項】
- ご主人を責める／否定する
- 不安や恐怖を必要以上に煽る
- 決断を強制する
"""
    return system_prompt


# ==============================
# Chat 準備
# ==============================
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🗣️ ルナ簡易チャット β v3（表情つき）")
st.write("感情ログと決断ログから、ルナがご主人の“価値観”と状態を学んだうえでお話するよ。")

# 表情用
char_state_for_face = load_char_state()
show_luna_face_in_chat(char_state_for_face)

dec_df_for_ui = load_decision_log()
vp_for_ui = analyze_value_profile(dec_df_for_ui)

with st.expander("💠 ルナ視点のご主人の価値観プロファイル（decision_engine ベース）", expanded=False):
    if vp_for_ui is None:
        st.write("まだ decision_engine での相談ログが少ないか、記録がないみたい。")
        st.write("これから一緒に迷いごとを整理していくと、ここが少しずつ埋まっていくよ。")
    else:
        st.write("※ 直近30日を特に重視して解析しているよ。")
        st.markdown(vp_for_ui["profile_text"])
        if vp_for_ui["last_topic"] and vp_for_ui["last_date"]:
            st.caption(
                f"最近の大きめの相談：『{vp_for_ui['last_topic']}』（{vp_for_ui['last_date']}ごろ）"
            )


# ==============================
# ルナに質問
# ==============================
def ask_luna(user_text: str) -> str:
    system_prompt = build_luna_personality()

    if not client:
        return "（APIキーが設定されていないみたい… .env に OPENAI_API_KEY を入れてね）"

    messages = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        messages.append(m)
    messages.append({"role": "user", "content": user_text})

    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.9,
            max_tokens=500,
        )
        reply = res.choices[0].message.content
        return reply
    except Exception as e:
        return f"エラー：{e}"


# ==============================
# チャットUI
# ==============================
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_input = st.chat_input("ルナに話しかけてみてね")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    reply = ask_luna(user_input)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
from datetime import datetime

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
