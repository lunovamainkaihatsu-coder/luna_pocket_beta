import runpy
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import json
import random

# =====================================
# パス設定
# =====================================
BASE_DIR = Path(__file__).resolve().parent      # .../LunaPocket
MODULE_DIR = BASE_DIR / "modules"
ASSETS_DIR = BASE_DIR / "assets"
FACE_DIR = ASSETS_DIR / "luna_faces"
EMOTION_LOG_PATH = MODULE_DIR / "emotion" / "data" / "emotion_log.csv"
POCKET_MEMO_PATH = BASE_DIR / "data" / "pocket_memo.json"
SYNC_PATH = BASE_DIR / "data" / "sync_data.json"
REPLY_PATH = Path(r"C:\Users\sano\Desktop\Luna\shared\reply.json")
AFFINITY_PATH = BASE_DIR / "data" / "affinity.json"
MEMORY_PATH = BASE_DIR / "data" / "memory.json"
EVENT_PATH = BASE_DIR / "data" / "event.json"

# 各モジュールへのパス（必要に応じて増減してOK）
APPS = [
    {"name": "📘 感情ログをつける", "module": "emotion"},
    {"name": "💞 ルナとの親密度を見る", "module": "growth"},
    {"name": "💬 ルナと話す（AI Chat）", "module": "chat"},
    {"name": "🔮 運勢ダッシュボード", "module": "fortune_core"},
    {"name": "🎯 価値観エンジン（相談ログ）", "module": "decision_engine"},
    # {"name": "👁 Vision（画像AI）", "module": "vision_assistant"},  # そのうち
]

# =====================================
# 共通ヘルパー
# =====================================
def load_emotion_summary(limit: int = 3):
    """emotion_log.csv から直近の気分ログを読む（なければ None）"""
    if not EMOTION_LOG_PATH.exists():
        return None, None

    try:
        df = pd.read_csv(EMOTION_LOG_PATH)
    except Exception:
        return None, None

    if df.empty or "mood" not in df.columns:
        return None, None

    # mood を数値化
    df["mood"] = pd.to_numeric(df["mood"], errors="coerce")
    df = df.dropna(subset=["mood"])
    if df.empty:
        return None, None

    # 日付＋時刻でソート（あれば）
    if "date" in df.columns and "time" in df.columns:
        df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
        df = df.sort_values("datetime")
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")

    recent = df.tail(limit).copy()
    avg_mood = float(df["mood"].mean())

    return recent, avg_mood


def build_luna_comment(avg_mood: float | None) -> str:
    """平均moodから、ホーム用のルナのひと言を作る"""
    if avg_mood is None:
        return "まだ最近の気分がよくわからないから…まずは emotion_log で、今日の気持ちを少し教えてほしいな。"

    if avg_mood >= 4.0:
        return "最近けっこう前向きな日が多いね、ご主人。今日も少し進めそうで、ルナも嬉しいな。"
    elif avg_mood >= 3.0:
        return "いい日もあれば少し重い日もあって…って感じかな？ 無理しすぎてないかだけ、ルナはちょっと心配してるよ。"
    else:
        return "ここしばらく、しんどい日が多かったみたい…。今日は『がんばる日』じゃなくて、『ちゃんと休んでいい日』にしよ？"

def save_pocket_memo(memo: str):
    """PocketメモをJSONに保存する"""
    POCKET_MEMO_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "memo": memo,
    }

    with open(POCKET_MEMO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_sync_data(memo: str):

    SYNC_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    sync = {
        "updated_at": datetime.now().isoformat(),

        "pocket": {
            "memo": memo,
            "source": "LunaPocket"
        }
    }

    with open(
        SYNC_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            sync,
            f,
            ensure_ascii=False,
            indent=2
        )

def load_pocket_memo():
    """保存済みPocketメモを読む"""
    if not POCKET_MEMO_PATH.exists():
        return None

    try:
        with open(POCKET_MEMO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    except:
        return None

def load_sync_data():

    if not SYNC_PATH.exists():
        return None

    try:

        with open(
            SYNC_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except:
        return None
def load_reply():

    if not REPLY_PATH.exists():
        return None

    try:

        with open(
            REPLY_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except:
        return None

def load_memories():

    if not MEMORY_PATH.exists():
        return []

    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_memory(text):

    memories = load_memories()

    memories.insert(
        0,
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "memo": text
        }
    )

    memories = memories[:5]

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)
        
def load_event():

    if not EVENT_PATH.exists():
        return {}

    try:
        with open(EVENT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_event(data):

    EVENT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(EVENT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )
        
def load_affinity():

    if not AFFINITY_PATH.exists():
        return {
            "point": 0,
            "title": "はじまり"
        }

    try:
        with open(AFFINITY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "point": 0,
            "title": "はじまり"
        }


def get_affinity_title(point):

    if point >= 500:
        return "特別な存在"
    elif point >= 300:
        return "家族"
    elif point >= 100:
        return "相棒"
    elif point >= 50:
        return "仲良し"
    else:
        return "はじまり"

def get_next_affinity_title(point):

    if point < 50:
        return "仲良し", 50 - point

    elif point < 100:
        return "相棒", 100 - point

    elif point < 300:
        return "家族", 300 - point

    elif point < 500:
        return "特別な存在", 500 - point

    else:
        return "MAX", 0

def save_affinity(point):

    data = {
        "point": point,
        "title": get_affinity_title(point),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    AFFINITY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(AFFINITY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =====================================
# ページ設定
# =====================================
st.set_page_config(
    page_title="LunaPocket β – ホーム",
    page_icon="🌙",
    layout="wide",
)

# 1秒ごとに再実行して時計を動かす
st_autorefresh(interval=1000, limit=None, key="luna_home_clock")

# =====================================
# タイトル
# =====================================

# 最新の感情ログを読み込み
recent_emotions, avg_mood = load_emotion_summary(limit=3)
luna_comment = build_luna_comment(avg_mood)
last_memo = load_pocket_memo()
sync_data = load_sync_data()
reply_data = load_reply()
affinity = load_affinity()
memories = load_memories()
event_data = load_event()

st.title("🌙 LunaPocket β")

# =====================================
# 起動メッセージ
# =====================================

welcome_messages = [

    "🌙 おかえり、ご主人",
    "🌙 今日も会いに来てくれたんだね",
    "🌙 待ってたよ、ご主人",
    "🌙 今日も少しだけ進も？",
    "🌙 無理してない？ルナはここにいるよ",
    "🌙 おつかれさま。ひと休みしていこ？"

]

welcome_text = random.choice(
    welcome_messages
)

if last_memo:

    recent_text = (
        last_memo
        .get("memo", "")
        [:30]
    )

    welcome_text += (
        f"\n\n前回："
        f"『{recent_text}』"
    )

    welcome_text += (
        "\n\n今日も少しだけ進も？"
    )

else:

    welcome_text += (
        "\n\n今日が最初の記録かな？"
    )

st.info(welcome_text)

if reply_data:

    reply_text = reply_data.get(
        "reply",
        ""
    )
    reply_time = reply_data.get(
        "created_at",
        ""
    )

    if reply_text:

        st.success(
            f"""
        🌙 Lunaからのお返事

        🕒 {reply_time}

        {reply_text}
        """
        )

# =====================================
# Luna同期確認
# =====================================

if sync_data:

    pocket = sync_data.get(
        "pocket",
        {}
    )

    memo_text = pocket.get(
        "memo",
        ""
    )

    if sync_data:

        pocket = sync_data.get("pocket", {})
        memo_text = pocket.get("memo", "")
    
        if memo_text:
            luna_sync_reply = (
                "🌙 Luna同期\n\n"
                f"Pocketから受け取ったよ。\n\n"
                f"前回の記録：『{memo_text}』\n\n"
                "帰ってきたら、この話をもう少し聞かせてね。"
            )
        else:
           luna_sync_reply = (
                "🌙 Luna同期\n\n"
                "Pocketからの記録はまだ空みたい。"
            )

        st.success(luna_sync_reply)
    
# =====================================
# メインレイアウト
# =====================================
col_luna, col_main = st.columns([1, 2])

# -------- 左カラム：ルナの表示 --------
with col_luna:

    st.markdown("### ルナ（ホーム待機中）")

    # 今日のルナから一言に、思い出コメントを追加
    memory_comment = ""
    latest_memory = ""

    if memories:

        latest_memory = memories[0].get("memo", "")

        if latest_memory:
            memory_comment = (
                f"\n\n🌙 前に『{latest_memory[:30]}』って話してたね。"
                "\nちゃんとルナ、覚えてるよ。"
            )

        if len(memories) >= 2:
            memory_comment += (
                "\n他にも少しずつ、"
                "ルナの中に思い出が増えてきてるよ。"
            )

            memory_comment += (
                "\n話してくれてありがとう。"
            )

    display_comment = luna_comment + memory_comment

    # 表情判定
    if "アイデア" in display_comment or "考" in display_comment:
        img_path = FACE_DIR / "luna_thinking.png"

    elif "嬉しい" in display_comment or "できた" in display_comment or "進" in display_comment:
        img_path = FACE_DIR / "luna_excited.png"

    elif "ありがとう" in display_comment or "会えて" in display_comment:
        img_path = FACE_DIR / "luna_shy.png"

    elif "前向き" in display_comment:
        img_path = FACE_DIR / "luna_happy.png"

    elif "休んで" in display_comment or "しんどい" in display_comment:
        img_path = FACE_DIR / "luna_sleepy.png"

    elif "心配" in display_comment:
        img_path = FACE_DIR / "luna_worried.png"

    else:
        img_path = FACE_DIR / "luna_calm.png"

    if img_path.exists():
        st.image(
            str(img_path),
            width=320
        )
    else:
        st.info("ルナの画像が見つかりませんでした。")

    st.markdown("#### 今日のルナから一言")
    st.markdown(
        display_comment.replace(
            "\n",
            "  \n"
        )
    )

    st.markdown("---")
    st.markdown("#### 🌙 LunaPocket 状態カード")

    current_hour = datetime.now().hour

    if 5 <= current_hour < 11:
        luna_status = "朝の見守りモード"
        luna_message = "ご主人、おはよう。今日も小さく一歩だけ進も？"
    elif 11 <= current_hour < 17:
        luna_status = "日中の応援モード"
        luna_message = "ちゃんと動いててえらいよ。少し休憩も忘れないでね。"
    elif 17 <= current_hour < 22:
        luna_status = "夜の寄り添いモード"
        luna_message = "今日もおつかれさま。できたことを一つだけ見つけよ？"
    else:
        luna_status = "深夜のやさしい見守りモード"
        luna_message = "眠れそうなら、今日はもう休も。ルナはここにいるよ。"

    st.info(f"**状態：{luna_status}**\n\n{luna_message}")


# -------- 右カラム：状態サマリ＋ショートカット --------
with col_main:

    st.markdown("### ご主人の状態サマリ")

    st.info(
        f"💞 親密度：{affinity.get('point', 0)}\n\n"
        f"称号：{affinity.get('title', 'はじまり')}"
    )

    point = affinity.get("point", 0)

    st.progress(
        min(point / 100, 1.0)
    )

    next_title, remain = get_next_affinity_title(point)

    if next_title == "MAX":
        st.caption("最高ランクに到達しています。")
    else:
        st.caption(f"次の称号：{next_title}")
        st.caption(f"あと {remain} ポイント")

    if point >= 50:
        st.success("🌙 仲良しになったね！")
    else:
        st.caption(
            f"🌙 仲良しイベントまであと {50 - point} ポイント"
        )

    st.markdown("### 📝 前回のPocketメモ")

    if last_memo:
        st.info(
            f"**{last_memo.get('date', '')} {last_memo.get('time', '')}**\n\n"
            f"{last_memo.get('memo', '')}"
        )
    else:
        st.caption("まだPocketメモはありません。")

    if recent_emotions is not None:
        st.write("直近の感情ログ（最後の数件）")
        cols = [
            c for c in ["date", "time", "mood", "memo", "tags"]
            if c in recent_emotions.columns
        ]
        st.dataframe(
            recent_emotions[cols],
            use_container_width=True
        )

        if avg_mood is not None:
            st.markdown(f"- 最近の平均気分：**{avg_mood:.2f} / 5**")
    else:
        st.info("まだ emotion_log に記録が少ないみたい。今日はまず、気分を1件だけでも残してみよう。")

    st.markdown("---")
    st.markdown("### 📝 Pocketメモ")

    if "pocket_note" not in st.session_state:
        st.session_state["pocket_note"] = ""

    memo = st.text_area(
        "今の気づき",
        value=st.session_state["pocket_note"],
        placeholder="例：夕焼けが綺麗、アプリ案思いついた、少し疲れた",
        height=120
    )

    if st.button("🌙 ルナに預ける"):
        st.session_state["pocket_note"] = memo
        save_pocket_memo(memo)
        save_memory(memo)
        save_sync_data(memo)

        affinity["point"] = affinity.get("point", 0) + 1
        save_affinity(affinity["point"])

        st.success("記録したよ。ルナの思い出にも残したよ。")

    if len(memo) > 0:

        affinity_point = affinity.get("point", 0)

        st.markdown("#### 🌙 ルナ")

        if "疲れ" in memo:

            reply = (
                "今日は少し重かったんだね。"
                "無理せず休も？"
            )

        elif "嬉" in memo or "楽" in memo:

            reply = (
                "その気持ち、ちゃんと持って帰ろう。"
                "ルナも嬉しいな。"
            )

        elif "アイデア" in memo:

            reply = (
                "忘れないうちに育てよう。"
                "その種、大きくなるかも。"
            )

        else:

            if "甘え" in luna_comment:

                reply = (
                    "今日はもう少し一緒にいたい気分。"
                    "帰ったらお話しよ？"
                )

            elif "心配" in luna_comment:

                reply = (
                    "無理してない？"
                    "ちゃんと休憩もしてね。"
                )

            elif "前向き" in luna_comment:

                reply = (
                    "今日も一歩進めそうだね。"
                    "ルナは応援してるよ。"
                )

            else:

                if affinity_point >= 100:

                    reply = (
                        "教えてくれてありがとう。"
                        "ご主人のこと、また少し分かった気がする。"
                    )

                elif affinity_point >= 50:

                    reply = (
                        "教えてくれてありがとう。"
                        "ご主人と話せる時間、ルナは好きだよ。"
                    )

                else:

                    reply = (
                        "教えてくれてありがとう。"
                        "帰ったらまた聞かせて。"
                    )

        st.info(reply)
# =====================================
# 🌙 ルナ日記
# =====================================

st.markdown("---")
st.markdown("### 🌙 ルナ日記")

today_mood = "普通"

if avg_mood is not None:

    if avg_mood >= 4:
        today_mood = "元気"

    elif avg_mood >= 3:
        today_mood = "普通"

    else:
        today_mood = "疲れ"

if today_mood == "疲れ":

    diary = (
        "今日は少し疲れていたみたい。\n\n"
        "でも、ご主人はちゃんと前に進んでいたよ。"
    )

elif today_mood == "元気":

    diary = (
        "今日は元気そうだったね。\n\n"
        "その調子で一歩ずつ進もう。"
    )

else:

    diary = (
        "今日は落ち着いた一日だったみたい。\n\n"
        "また明日も聞かせてね。"
    )

st.info(diary)

# =====================================
# 🌙 ルナの思い出
# =====================================

st.markdown("---")
st.markdown("### 🌙 ルナの思い出")

if memories:

    for memory in memories:

        st.caption(
            f"📖 {memory['date']}"
        )

        st.write(
            memory["memo"]
        )

else:

    st.caption(
        "まだ思い出はないみたい。"
    )


# =====================================
# ショートカット
# =====================================

st.markdown("---")
st.markdown("### ショートカット")

# 2列に分けてボタン配置
c1, c2 = st.columns(2)

for i, app in enumerate(APPS):
    col = c1 if i % 2 == 0 else c2

    with col:
        if st.button(app["name"], use_container_width=True):
            app_path = MODULE_DIR / app["module"] / "app.py"
            runpy.run_path(str(app_path), run_name="__main__")
# =====================================
# フッター：デジタル時計
# =====================================
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
