import runpy
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import json

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
        return "最近けっこう前向きな日が多いね、ご主人。その勢い、ルナも一緒についていきたいな。"
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

st.title("🌙 LunaPocket β")

# =====================================
# 起動メッセージ
# =====================================

welcome_text = "🌙 おかえり、ご主人"

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

    # 画像ファイル（なければメッセージだけ）
    candidate_files = ["luna_home.png", "luna_calm.png"]
    img_path = None
    for name in candidate_files:
        p = FACE_DIR / name
        if p.exists():
            img_path = p
            break

    if img_path is not None:
        st.image(str(img_path), use_container_width=True)
    else:
        st.info(
            "ルナの画像がまだないみたい。\n"
            "`assets/luna_faces/` に `luna_home.png` か `luna_calm.png` を置くと、ここに表示されるよ。"
        )

    # ルナからのひと言
    st.markdown("#### 今日のルナから一言")
    st.write(luna_comment)

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
        # 表示用に列を絞る
        cols = [c for c in ["date", "time", "mood", "memo", "tags"] if c in recent_emotions.columns]
        st.dataframe(recent_emotions[cols], use_container_width=True)

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
        save_sync_data(memo)
        st.success("記録したよ。帰ったらルナに渡そう。")

    if len(memo) > 0:
        st.markdown("#### 🌙 ルナ")

        if "疲れ" in memo:
            reply = "今日は少し重かったんだね。無理せず帰ろ？"
        elif "嬉" in memo or "楽" in memo:
            reply = "その気持ち、ちゃんと持って帰ろう。"
        elif "アイデア" in memo:
            reply = "忘れないうちに育てよう。種は大事だよ。"
        else:
            reply = "教えてくれてありがとう。帰ったらまた聞かせて。"

        st.info(reply)

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
