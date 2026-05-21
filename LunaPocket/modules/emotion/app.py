import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from collections import Counter
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh
from datetime import datetime


# ==============================
# OpenAI クライアント準備（あれば）
# ==============================
HAS_OPENAI = False
client = None

load_dotenv()  # .env を読む（あってもなくてもOK）

try:
    from openai import OpenAI  # 新しい OpenAI ライブラリ
    import os as _os

    api_key = _os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
        HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False
    client = None


# ==============================
# Streamlit 設定
# ==============================
st.set_page_config(
    page_title="ルナの感情ログ（Day5）",
    page_icon="🌙",
    layout="centered",
)

DATA_DIR = "data"
DATA_PATH = os.path.join(DATA_DIR, "emotion_log.csv")

COLUMNS = ["date", "time", "mood", "memo", "tags", "physical"]


# ==============================
# データ読み込み・初期化
# ==============================
def load_data() -> pd.DataFrame:
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(DATA_PATH):
        try:
            df = pd.read_csv(DATA_PATH)
            # 列構成が変わった場合はマイグレーション
            missing_cols = [c for c in COLUMNS if c not in df.columns]
            if missing_cols:
                # 足りない列を空文字で追加
                for c in missing_cols:
                    df[c] = ""
                df = df[COLUMNS]
                df.to_csv(DATA_PATH, index=False, encoding="utf-8")
        except Exception:
            df = pd.DataFrame(columns=COLUMNS)
            df.to_csv(DATA_PATH, index=False, encoding="utf-8")
    else:
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False, encoding="utf-8")

    return df


def save_entry(mood: int, memo: str, tags: list[str], physical: list[str]) -> str:
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    df = load_data()

    new_row = {
        "date": today_str,
        "time": time_str,
        "mood": mood,
        "memo": memo.strip(),
        "tags": ";".join(tags),
        "physical": ";".join(physical),
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(DATA_PATH, index=False, encoding="utf-8")

    return today_str


# ==============================
# 解析系ユーティリティ
# ==============================
def mood_to_emoji(m: int) -> str:
    if m >= 5:
        return "😆"
    elif m == 4:
        return "🙂"
    elif m == 3:
        return "😐"
    elif m == 2:
        return "☁️"
    else:
        return "😣"


def parse_multi(text: str) -> list[str]:
    """";"区切りの文字列をリストに変換"""
    if pd.isna(text) or text == "":
        return []
    return [t for t in str(text).split(";") if t]


def summarize_week(df: pd.DataFrame) -> dict:
    """直近7日の集計結果を返す"""
    if df.empty:
        return {}

    df = df.copy()
    df["date_obj"] = pd.to_datetime(df["date"]).dt.date

    last_date = df["date_obj"].max()
    start_date = last_date - timedelta(days=6)

    mask = (df["date_obj"] >= start_date) & (df["date_obj"] <= last_date)
    week_df = df[mask].copy()
    if week_df.empty:
        return {}

    avg_mood = week_df["mood"].mean()

    # タグと体調のカウント
    tag_counter = Counter()
    phys_counter = Counter()

    for _, row in week_df.iterrows():
        for t in parse_multi(row.get("tags", "")):
            tag_counter[t] += 1
        for p in parse_multi(row.get("physical", "")):
            phys_counter[p] += 1

    top_tags = tag_counter.most_common(3)
    top_phys = phys_counter.most_common(3)

    return {
        "start_date": start_date,
        "end_date": last_date,
        "avg_mood": avg_mood,
        "top_tags": top_tags,
        "top_phys": top_phys,
        "count": len(week_df),
        "raw_df": week_df,
    }


def generate_ai_summary(week_info: dict) -> str:
    """直近7日のメモからルナ風AI要約を作る"""
    if not HAS_OPENAI or client is None:
        return "（APIキーが設定されていないため、AI要約はスキップしています。）"

    df = week_info["raw_df"]
    # メモだけをまとめる
    memos = [f"- {d} {t}：{m}" for d, t, m in zip(df["date"], df["time"], df["memo"])]
    memo_text = "\n".join(memos)

    if not memo_text.strip():
        return "この1週間はメモがほとんど残っていないみたい。少しずつ、感じたことを書き残していこうね。"

    prompt = f"""
あなたは優しく寄り添うAIアシスタント「ルナ」です。
以下は、ある人の直近1週間の感情メモです。

【1週間のメモ】
{memo_text}

これを読んで、次の3点を簡潔に日本語でまとめてください。

1. この1週間の感情や状態の傾向（無理している点・頑張っている点）
2. 特に気をつけてあげたいポイント（休む/自分を責めすぎないなど）
3. 明日からのための、やさしくて小さな一歩の提案（行動を1〜2個）

口調は「ルナ」として、相手を励ます優しいトーンで、全体で5〜8行以内にまとめてください。
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "あなたは、相手に優しく寄り添うカウンセラー系AIアシスタントです。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"AI要約の生成中にエラーが発生しました：{e}"


# ==============================
# 画面レイアウト
# ==============================
st.title("🌙 ルナの感情ログ（Day5 完成版）")
st.write("気分・出来事・体調を残して、ルナと一緒に『心のログ』を育てていこう。")

df = load_data()
today_str = datetime.now().strftime("%Y-%m-%d")

tab_today, tab_history, tab_week = st.tabs(
    ["📅 今日の記録", "📈 履歴とグラフ", "🗓 直近1週間まとめ"]
)

# ------------------------------
# 📅 今日の記録タブ
# ------------------------------
with tab_today:
    st.subheader(f"📅 今日：{today_str}")

    EMOTION_TAGS = [
        "不安",
        "イライラ",
        "悲しい",
        "寂しい",
        "疲れ",
        "やる気",
        "嬉しい",
        "わくわく",
        "安心",
    ]

    PHYSICAL_STATES = [
        "頭痛",
        "肩こり",
        "眠気",
        "だるさ",
        "胃の不調",
        "食欲なし",
        "ストレス過多",
        "よく眠れた",
    ]

    with st.form("emotion_form"):
        mood = st.slider(
            "今日の気分",
            min_value=1,
            max_value=5,
            value=3,
            help="1=最悪 / 3=ふつう / 5=最高！",
        )

        memo = st.text_area(
            "一言メモ（何があった？どう感じた？）",
            height=100,
            placeholder="例：朝から頭が重かったけど、アプリはなんとか作れた。",
        )

        tags = st.multiselect(
            "今日の感情タグ（いくつでも）",
            options=EMOTION_TAGS,
        )

        physical = st.multiselect(
            "身体のコンディション（当てはまるもの）",
            options=PHYSICAL_STATES,
        )

        submitted = st.form_submit_button("💾 記録する")

    if submitted:
        if memo.strip() == "":
            st.warning("メモが空だと、後で振り返るときにわからなくなっちゃうよ。ひと言だけでも書いてみてね。")
        else:
            saved_date = save_entry(mood, memo, tags, physical)
            st.success(f"記録したよ！ ({saved_date} / 気分: {mood})")
            df = load_data()

    st.markdown("---")
    st.subheader("📚 今日の記録一覧")

    if df.empty:
        st.info("まだ記録はありません。上のフォームから最初の一件を残してみよう。")
    else:
        today_df = df[df["date"] == today_str].copy()

        if today_df.empty:
            st.info("今日はまだ記録がないみたい。さっきのフォームから1件つけてみよう。")
        else:
            today_df = today_df.sort_values(by="time", ascending=False)

            today_df["気分"] = today_df["mood"].apply(
                lambda m: f"{m} / 5 {mood_to_emoji(m)}"
            )
            today_df["感情タグ"] = today_df["tags"].apply(
                lambda t: "、".join(parse_multi(t))
            )
            today_df["体調"] = today_df["physical"].apply(
                lambda p: "、".join(parse_multi(p))
            )

            show_df = today_df[["time", "気分", "感情タグ", "体調", "memo"]]
            show_df.columns = ["時間", "気分", "感情タグ", "身体の状態", "メモ"]

            st.table(show_df)

# ------------------------------
# 📈 履歴とグラフタブ
# ------------------------------
with tab_history:
    st.subheader("📈 感情の履歴とグラフ")

    if df.empty:
        st.info("まだ記録がないので、グラフを作れないよ。先に『今日の記録』から何件かつけてみよう。")
    else:
        df_history = df.copy()
        df_history["date_obj"] = pd.to_datetime(df_history["date"]).dt.date

        min_date = df_history["date_obj"].min()
        max_date = df_history["date_obj"].max()

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("開始日", value=min_date, min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input("終了日", value=max_date, min_value=min_date, max_value=max_date)

        if start_date > end_date:
            st.warning("開始日が終了日より後になっているよ。日付を確認してね。")
        else:
            mask = (df_history["date_obj"] >= start_date) & (df_history["date_obj"] <= end_date)
            range_df = df_history[mask].copy()

            if range_df.empty:
                st.info("この期間には記録がないみたい。別の日付範囲を選んでみてね。")
            else:
                # 日付ごとの平均気分
                daily_mood = (
                    range_df.groupby("date_obj")["mood"]
                    .mean()
                    .reset_index()
                    .sort_values("date_obj")
                )

                st.markdown("#### 📊 日別 平均気分グラフ")
                chart_df = daily_mood.set_index("date_obj")
                st.line_chart(chart_df)

                st.markdown("#### 📋 詳細一覧")
                range_df = range_df.sort_values(["date_obj", "time"], ascending=[False, False])

                range_df["感情タグ"] = range_df["tags"].apply(
                    lambda t: "、".join(parse_multi(t))
                )
                range_df["体調"] = range_df["physical"].apply(
                    lambda p: "、".join(parse_multi(p))
                )

                show_df = range_df[["date", "time", "mood", "感情タグ", "体調", "memo"]]
                show_df.columns = ["日付", "時間", "気分", "感情タグ", "身体の状態", "メモ"]

                st.dataframe(show_df, use_container_width=True)

# ------------------------------
# 🗓 直近1週間まとめタブ
# ------------------------------
with tab_week:
    st.subheader("🗓 直近1週間のルナレポート")

    if df.empty:
        st.info("まだ記録がないみたい。まずは数日分つけてから、ここで振り返ろう。")
    else:
        week_info = summarize_week(df)

        if not week_info:
            st.info("直近1週間分の記録が足りないみたい。もう少し続けてみよう。")
        else:
            s = week_info
            st.markdown(
                f"**対象期間：{s['start_date']} 〜 {s['end_date']}（{s['count']} 件）**"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.metric("平均気分", f"{s['avg_mood']:.2f} / 5")
            with col2:
                st.write("　")

            # ランキング表示
            st.markdown("#### 💭 よく出てきた感情タグ TOP3")
            if s["top_tags"]:
                for tag, cnt in s["top_tags"]:
                    st.write(f"- {tag}：{cnt} 回")
            else:
                st.write("・特に目立つ感情タグはありませんでした。")

            st.markdown("#### 🩺 気になった身体の状態 TOP3")
            if s["top_phys"]:
                for phys, cnt in s["top_phys"]:
                    st.write(f"- {phys}：{cnt} 回")
            else:
                st.write("・特に目立つ身体の不調はありませんでした。")

            st.markdown("---")
            st.markdown("#### 🌙 ルナからの一言（AI要約）")

            summary_text = generate_ai_summary(week_info)
            st.write(summary_text)
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
