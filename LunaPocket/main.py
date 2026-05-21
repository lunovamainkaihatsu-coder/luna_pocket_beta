import runpy
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# =====================================
# パス設定
# =====================================
BASE_DIR = Path(__file__).resolve().parent      # .../LunaPocket
MODULE_DIR = BASE_DIR / "modules"
ASSETS_DIR = BASE_DIR / "assets"
FACE_DIR = ASSETS_DIR / "luna_faces"
EMOTION_LOG_PATH = MODULE_DIR / "emotion" / "data" / "emotion_log.csv"

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
st.title("🌙 LunaPocket β")

# 最新の感情ログを読み込み
recent_emotions, avg_mood = load_emotion_summary(limit=3)
luna_comment = build_luna_comment(avg_mood)

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

# -------- 右カラム：状態サマリ＋ショートカット --------
with col_main:
    st.markdown("### ご主人の状態サマリ")

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
