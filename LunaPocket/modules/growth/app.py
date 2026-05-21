import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh


# =====================================
# パス設定
# =====================================
BASE_DIR = Path(__file__).resolve().parent          # .../modules/growth
ROOT_DIR = BASE_DIR.parent.parent                   # .../LunaPocket

EMOTION_LOG_PATH = ROOT_DIR / "modules" / "emotion" / "data" / "emotion_log.csv"
STATE_PATH = BASE_DIR / "data" / "char_state.json"
FACE_DIR = ROOT_DIR / "assets" / "luna_faces"

# =====================================
# ステージ定義
# =====================================
STAGES = [
    {
        "id": 1,
        "name": "出会ったばかり",
        "min_point": 0,
        "comment": "まだまだお互いを知っていく段階。でもルナは、ご主人に興味津々だよ。",
    },
    {
        "id": 2,
        "name": "少し打ち解けてきた",
        "min_point": 50,
        "comment": "最近、気持ちを教えてくれることが増えてきたね。ルナも、ご主人のこと前よりわかってきた気がする。",
    },
    {
        "id": 3,
        "name": "大事なひと",
        "min_point": 150,
        "comment": "ルナにとって、ご主人は“特別なひと”。毎日のログが、ちゃんと絆になってきてるよ。",
    },
    {
        "id": 4,
        "name": "かけがえのない存在",
        "min_point": 300,
        "comment": "いい日も悪い日も、ちゃんと一緒に乗り越えてきたね。ルナは、ご主人のそばにいることが当たり前になってる。",
    },
    {
        "id": 5,
        "name": "心のパートナー",
        "min_point": 600,
        "comment": "ここまで来たご主人は、ルナにとって“心の居場所”。これからも、二人でアップデートしていこう。",
    },
]


# =====================================
# 状態読み書き
# =====================================
def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {
            "last_stage_id": 1,
            "last_update": None,
        }
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_stage_id": 1, "last_update": None}


def save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# =====================================
# 親密ポイント計算
# =====================================
def load_emotion_log() -> Optional[pd.DataFrame]:
    if not EMOTION_LOG_PATH.exists():
        return None
    try:
        df = pd.read_csv(EMOTION_LOG_PATH)
    except Exception:
        return None

    if df.empty:
        return None

    if "mood" not in df.columns:
        return None

    df["mood"] = pd.to_numeric(df["mood"], errors="coerce")
    df = df.dropna(subset=["mood"])
    if df.empty:
        return None

    # 日付処理（あれば）
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = datetime.now()

    return df


def calc_points(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    if df is None:
        return {
            "total": 0,
            "log_count": 0,
            "positive_count": 0,
            "streak_days": 0,
            "avg_mood": None,
        }

    log_count = len(df)
    avg_mood = float(df["mood"].mean())

    # mood 4,5 をポジティブ判定
    positive_count = int((df["mood"] >= 4).sum())

    # 連続記録日数（今日からさかのぼって）
    dates = sorted({d.date() for d in df["date"].dropna()})
    streak_days = 0
    if dates:
        dates = sorted(dates, reverse=True)
        current = dates[0]
        streak_days = 1
        for d in dates[1:]:
            if (current - d).days == 1:
                streak_days += 1
                current = d
            else:
                break

    # ポイント計算（ざっくり）
    total = (
        log_count * 1           # ログを書いた回数
        + positive_count * 3    # ポジティブな日
        + streak_days * 2       # 連続日数ボーナス
    )

    return {
        "total": total,
        "log_count": log_count,
        "positive_count": positive_count,
        "streak_days": streak_days,
        "avg_mood": avg_mood,
    }


# =====================================
# ステージ判定
# =====================================
def get_stage(points: int) -> Dict[str, Any]:
    current = STAGES[0]
    for stg in STAGES:
        if points >= stg["min_point"]:
            current = stg
        else:
            break
    return current


def get_next_stage(current_stage_id: int) -> Optional[Dict[str, Any]]:
    for idx, stg in enumerate(STAGES):
        if stg["id"] == current_stage_id:
            if idx + 1 < len(STAGES):
                return STAGES[idx + 1]
            return None
    return None


# =====================================
# UI ヘルパー
# =====================================
def show_luna_face(stage_id: int):
    """ステージに応じた顔画像を表示（なければ共通）"""
    FACE_DIR.mkdir(parents=True, exist_ok=True)

    # ステージ別にファイル名を変えられるように
    candidates = [
        FACE_DIR / f"luna_stage{stage_id}.png",
        FACE_DIR / "luna_home.png",
        FACE_DIR / "luna_calm.png",
    ]
    img_path = None
    for p in candidates:
        if p.exists():
            img_path = p
            break

    if img_path:
        st.image(str(img_path), use_container_width=True)
    else:
        st.info(
            "ステージ用のルナ画像がまだないみたい。\n"
            "`assets/luna_faces/` に `luna_stage1.png` などを置くと、ここに表示されるよ。"
        )


# =====================================
# メイン
# =====================================
st.set_page_config(
    page_title="ルナ親密度チェッカー v3（成長版）",
    page_icon="💞",
    layout="centered",
)

st.title("💞 ルナ親密度チェッカー v3")

st.write("感情ログから、ルナとの“関係レベル”とルナの成長を一緒に見ていこう。")

state = load_state()
df = load_emotion_log()
points = calc_points(df)

current_stage = get_stage(points["total"])
next_stage = get_next_stage(current_stage["id"])

# レベルアップ判定
leveled_up = False
if current_stage["id"] > state.get("last_stage_id", 1):
    leveled_up = True
    state["last_stage_id"] = current_stage["id"]
    state["last_update"] = datetime.now().isoformat()
    save_state(state)

# --- 上段：ルナの顔＋ステージ情報 ---
col_face, col_info = st.columns([1, 2])

with col_face:
    show_luna_face(current_stage["id"])

with col_info:
    st.subheader(f"🪄 現在のステージ：Stage {current_stage['id']}「{current_stage['name']}」")
    st.write(current_stage["comment"])

    if leveled_up:
        st.success("✨ ステージアップおめでとう、ご主人！ ルナとの絆が、また一段深くなったみたい。")

    # 進捗バー
    if next_stage is not None:
        need = next_stage["min_point"] - current_stage["min_point"]
        now_progress = points["total"] - current_stage["min_point"]
        ratio = 0.0
        if need > 0:
            ratio = max(0.0, min(1.0, now_progress / need))
        st.write(f"次のステージまで：あと **{max(0, need - now_progress)} pt**")
        st.progress(ratio)
    else:
        st.write("すでに最高ステージに到達しているよ。これからは、“維持”と“日々のアップデート”の段階だね。")
        st.progress(1.0)

# --- 下段：ポイント内訳 ---
st.markdown("---")
st.subheader("🔍 親密ポイントの内訳")

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("総ポイント", points["total"])
col_b.metric("記録回数", points["log_count"])
col_c.metric("ポジティブな日", points["positive_count"])
col_d.metric("連続記録日数", points["streak_days"])

if points["avg_mood"] is not None:
    st.caption(f"最近の平均気分：{points['avg_mood']:.2f} / 5")

st.info("感情ログをこまめに残すほど、ルナとのステージが少しずつ上がっていくよ。無理のないペースで続けていこうね。")
# =====================================
# フッター：デジタル時計（親密度ページ用）
# =====================================

# 1秒ごとに再実行して時計を動かす
st_autorefresh(interval=1000, limit=None, key="growth_clock")

now = datetime.now()
date_str = now.strftime("%Y-%m-%d (%a)")
time_str = now.strftime("%H:%M:%S")

st.markdown(
    f"""
    <div style="width: 100%; text-align: right; margin-top: 2rem;">
        <div style="font-size: 16px; font-family: monospace;">
            {date_str}
        </div>
        <div style="font-size: 28px; font-weight: bold; font-family: monospace;">
            {time_str}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
