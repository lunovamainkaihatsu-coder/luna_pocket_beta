import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import random

# =====================================
# パス設定（emotion_log を読む）
# =====================================
BASE_DIR = Path(__file__).resolve().parent        # .../modules/fortune_core
ROOT_DIR = BASE_DIR.parent.parent                 # .../LunaPocket

EMOTION_LOG_PATH = ROOT_DIR / "modules" / "emotion" / "data" / "emotion_log.csv"


# =====================================
# 共通：感情ログの読み込み
# =====================================
def load_emotion_log(days: int = 7):
    """直近days日分の感情ログを読み込む。なければ None"""
    if not EMOTION_LOG_PATH.exists():
        return None

    try:
        df = pd.read_csv(EMOTION_LOG_PATH)
    except Exception:
        return None

    if df.empty or "mood" not in df.columns:
        return None

    # mood を数値に
    df["mood"] = pd.to_numeric(df["mood"], errors="coerce")
    df = df.dropna(subset=["mood"])
    if df.empty:
        return None

    # 日付処理
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        except Exception:
            df["date"] = datetime.now()
    else:
        df["date"] = datetime.now()

    # 直近 days 日に絞る
    border = datetime.now().date() - timedelta(days=days - 1)
    df = df[df["date"].dt.date >= border]

    if df.empty:
        return None

    return df


# =====================================
# ① 感情ログベース占い
# =====================================
def analyze_mood_fortune(df: pd.DataFrame | None):
    if df is None:
        return {
            "has_log": False,
            "level": "情報不足",
            "rank": "⛅",
            "summary": "直近の感情ログがほとんどないから、まだ詳しい運勢が読みきれない…。",
            "theme": "今日はまず、emotion_log で今の気分を1件だけでも残してみよう。",
            "advice_mind": "頭の中にあるモヤモヤを、そのままメモに書き出してみて。",
            "advice_body": "水分をとって、5〜10分だけでも目を閉じて休む時間を。",
            "advice_action": "「今日はここだけやる」と決めて、小さなタスクだけを片づけよう。",
            "stats": None,
        }

    log_count = len(df)
    avg_mood = float(df["mood"].mean())
    pos_ratio = float((df["mood"] >= 4).sum()) / log_count
    neg_ratio = float((df["mood"] <= 2).sum()) / log_count

    # 連続記録日数
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

    # ざっくり “運勢スコア”
    score = avg_mood * 10 + streak_days * 1.5 + (pos_ratio - neg_ratio) * 10

    # ルナ式・5段階
    if score >= 55:
        rank = "🌈 超好調"
        level = "エネルギーMAX期"
        summary = "流れが一気に加速しそうな日。『やる』と決めたことに宇宙の追い風がついている感じ。"
        theme = "遠慮せず、やりたいことに素直に舵を切る。"
        advice_mind = "「こうなったら最高」を具体的にイメージして、ノートかメモに書き出してみて。"
        advice_body = "テンションが上がりすぎてオーバーヒートしないよう、適度な休憩と深呼吸を忘れずに。"
        advice_action = "今日はひとつ『大きめの一歩』を踏み出してみよう（発信・応募・連絡など）。"
    elif score >= 45:
        rank = "☀ 好調"
        level = "着実に進める日"
        summary = "静かにだけど、ちゃんと前に進む流れ。小さな努力が積み上がりやすい。"
        theme = "コツコツ積み上げたものを、少しだけ“形”にしてみる。"
        advice_mind = "「今日1日でできたこと」に意識を向けて、自分をちゃんと褒めてあげて。"
        advice_body = "軽く体を動かしたり、短い散歩でリフレッシュすると集中力が続きやすいよ。"
        advice_action = "ToDoを3つ以内に絞って、ひとつずつ片づけていこう。"
    elif score >= 35:
        rank = "⛅ 静観"
        level = "様子見モード"
        summary = "良くも悪くもフラットな雰囲気。無理して動くより、整えるほうが向いている日。"
        theme = "『整える』と『準備する』に時間を使う。"
        advice_mind = "気になっていることをリストアップして、『今やる／後で／手放す』に分けてみて。"
        advice_body = "肩・首まわりをほぐしたり、ぬるめのお風呂でゆるっと緩めてあげよう。"
        advice_action = "資料整理・フォルダ整理・メモ整頓など、“土台づくり”に少し時間を使ってみて。"
    elif score >= 25:
        rank = "🌧 低調"
        level = "ペースダウン期"
        summary = "エネルギーがやや落ちぎみ。がんばり続けるより、少しブレーキを踏んでもいいサイン。"
        theme = "『やらなきゃ』より『今は休んでいい』を優先してみる。"
        advice_mind = "今抱えている心配ごとを1つだけ選んで、『今日はここまで考えたら休む』と線を引こう。"
        advice_body = "温かい飲み物を飲んだり、少し長めに眠るなど、身体を最優先にしてあげて。"
        advice_action = "タスクは“最低限”だけに絞って、残りは明日の自分にバトンタッチしよう。"
    else:
        rank = "🛌 充電日"
        level = "完全チャージデー"
        summary = "がんばりの蓄積や疲れが出やすいタイミング。今日は『サボる勇気』が必要な日かも。"
        theme = "自分を責める代わりに、とことん甘やかす。"
        advice_mind = "「ここまでよくやった」と、過去の自分に向けて感謝の言葉をかけてみて。"
        advice_body = "スマホ時間を少し減らして、布団やソファーに沈み込む時間を確保しよう。"
        advice_action = "大きな決断や重要な約束は、できれば今日は保留にしておくのが吉。"

    stats = {
        "log_count": log_count,
        "avg_mood": avg_mood,
        "pos_ratio": pos_ratio,
        "neg_ratio": neg_ratio,
        "streak_days": streak_days,
        "score": score,
    }

    return {
        "has_log": True,
        "level": level,
        "rank": rank,
        "summary": summary,
        "theme": theme,
        "advice_mind": advice_mind,
        "advice_body": advice_body,
        "advice_action": advice_action,
        "stats": stats,
    }


# =====================================
# ② 12星座占い
# =====================================

ZODIAC_MESSAGES = {
    "牡羊座": "直感と行動力がカギの日。『やってから考える』くらいでちょうどいいかも。",
    "牡牛座": "五感を満たすことが運気アップに直結。美味しいものや心地よいものを味わって。",
    "双子座": "情報運が強め。気になることはどんどん調べて、アウトプットしていこう。",
    "蟹座": "身近な人との時間が心の栄養に。安心できる場所を大切にしてみて。",
    "獅子座": "自己表現のチャンス。少し目立つくらいの行動が吉。",
    "乙女座": "細かいところを整えるほど運気が安定。整理整頓や見直しにツキあり。",
    "天秤座": "人とのバランス感覚が光る日。対話や交渉ごとに良い流れ。",
    "蠍座": "一つのことを深堀りすると成果が出やすい日。没頭OK。",
    "射手座": "視野を広げるほど運が味方する。新しい分野や場所に触れてみて。",
    "山羊座": "現実的な一歩が大事な日。長期目標に向けた小さな行動を。",
    "水瓶座": "新しい発想やマニアックなアイデアがひらめきやすい。『普通じゃない』を大事にして。",
    "魚座": "感性が冴える日。音楽・物語・イラストなど、心が震えるものに触れてみて。",
}

ZODIAC_EXTRA = [
    "タイミングを急がず、『今の自分』を一度受け入れてあげると、次の流れが見えやすくなるよ。",
    "スマホから少し離れて、空や街の景色を眺める時間を作ると、心がふっと軽くなりそう。",
    "昔好きだったことを思い出して、少しだけ再開してみるのもおすすめ。",
    "『やらなきゃ』じゃなくて『やりたい』でスケジュールを組んでみると、エネルギーが戻ってくるよ。",
    "今日は“完璧”じゃなくて“70点でOK”を合言葉にしてみて。",
]


def get_zodiac_fortune(sign: str):
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{today}-{sign}"
    rnd = random.Random(key)

    base = ZODIAC_MESSAGES.get(
        sign,
        "今日は自分らしさを大事にしたい日。周りと比べるより、自分のペースを守ってね。",
    )
    extra = rnd.choice(ZODIAC_EXTRA)

    luck_items = [
        "好きだった飲み物",
        "ふと目に入った色",
        "昔から持っている小物",
        "メモ帳やノート",
        "お気に入りのアプリ",
    ]
    lucky = rnd.choice(luck_items)

    return base, extra, lucky


# =====================================
# ③ タロット一枚引き
# =====================================

TAROT_CARDS = [
    ("愚者", "0", "新しい旅立ち・自由・直感"),
    ("魔術師", "I", "スタート・ひらめき・コミュニケーション"),
    ("女教皇", "II", "静かな知恵・直感・心の声"),
    ("女帝", "III", "豊かさ・愛情・創造性"),
    ("皇帝", "IV", "責任・リーダーシップ・安定"),
    ("法王", "V", "学び・伝統・信頼できる人"),
    ("恋人", "VI", "選択・ときめき・心のつながり"),
    ("戦車", "VII", "前進・勢い・突破"),
    ("力", "VIII", "内なる強さ・優しさ・忍耐"),
    ("隠者", "IX", "内省・一人の時間・探求"),
    ("運命の輪", "X", "転機・チャンス・流れの変化"),
    ("正義", "XI", "バランス・決断・公正さ"),
    ("吊るされた男", "XII", "視点の変化・一時停止・手放し"),
    ("死神", "XIII", "終わりと始まり・刷新・大きな変化"),
    ("節制", "XIV", "調整・中庸・流れを整える"),
    ("悪魔", "XV", "執着・誘惑・パターンに気づく"),
    ("塔", "XVI", "崩壊・ショック・目覚め"),
    ("星", "XVII", "希望・インスピレーション・癒し"),
    ("月", "XVIII", "不安・想像・夢と現実のあいだ"),
    ("太陽", "XIX", "成功・喜び・自己肯定感"),
    ("審判", "XX", "復活・評価・過去からのメッセージ"),
    ("世界", "XXI", "完成・達成・新しいステージ"),
]

TAROT_UPRIGHT = "正位置："
TAROT_REVERSED = "逆位置："


def draw_tarot_card(topic: str = "今日のメッセージ"):
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{today}-{topic}"
    rnd = random.Random(key)

    card = rnd.choice(TAROT_CARDS)
    is_reversed = rnd.choice([True, False])

    name, num, keywords = card
    position_label = TAROT_REVERSED if is_reversed else TAROT_UPRIGHT

    if is_reversed:
        message = (
            f"{position_label}"
            " いったん立ち止まって、流れを見直すタイミングかも。"
            " 無理に進めるより、『今は何を手放すか』に目を向けてみて。"
        )
    else:
        message = (
            f"{position_label}"
            " 素直に動き出すことで流れが開く日。"
            " 小さな一歩でいいから、気になっていたことに手を伸ばしてみて。"
        )

    return {
        "name": name,
        "num": num,
        "keywords": keywords,
        "is_reversed": is_reversed,
        "message": message,
        "topic": topic,
    }


# =====================================
# ④ ざっくり星読み（ライト占星術風）
# =====================================

ASTRO_THEMES = {
    "overall": [
        "今の流れを受け入れて、無理なくできる範囲で進めることが大事な日。",
        "少し先の未来を見据えて、準備や仕込みに時間を使うと良さそう。",
        "過去を振り返りつつ『ここからどうしたいか』を描き直すタイミング。",
    ],
    "work": [
        "一気に結果を出すより、信頼を積み重ねる動きにツキあり。",
        "細かい部分の見直しや修正に力を入れると、後々大きな差になるよ。",
        "思い切って相談や質問をすると、意外なサポートが入りそう。",
    ],
    "love": [
        "自分の気持ちを丁寧な言葉で伝えることが、関係性をあたためるカギ。",
        "相手よりもまず自分の心と体を整えることで、自然といい流れが戻ってくる。",
        "新しい出会いよりも、今ある縁を少しだけ深めてみると◎。",
    ],
}


def get_astro_reading(sign: str):
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"astro-{today}-{sign}"
    rnd = random.Random(key)

    overall = rnd.choice(ASTRO_THEMES["overall"])
    work = rnd.choice(ASTRO_THEMES["work"])
    love = rnd.choice(ASTRO_THEMES["love"])

    return overall, work, love


# =====================================
# UI 本体
# =====================================
st.set_page_config(
    page_title="ルナの運勢ダッシュボード β+",
    page_icon="🔮",
    layout="centered",
)

st.title("🔮 ルナの運勢ダッシュボード β+")

st.caption("感情ログと星のイメージから、ルナがいくつかの角度で今日の運勢を見ていくよ。")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 感情ログ占い", "⭐ 12星座占い", "🃏 タロット一枚引き", "🌌 ざっくり星読み"]
)

# ---------- タブ1：感情ログ占い ----------
with tab1:
    df = load_emotion_log(days=7)
    fortune = analyze_mood_fortune(df)

    st.subheader("✨ 今日のルナ式・5段階運勢")
    st.markdown(f"**{fortune['rank']}  {fortune['level']}**")
    st.write(fortune["summary"])

    st.markdown("### 今日のテーマ")
    st.write(fortune["theme"])

    st.markdown("### 今日の過ごし方ヒント")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🧠 心のケア**")
        st.write(fortune["advice_mind"])
    with col2:
        st.markdown("**💪 身体のケア**")
        st.write(fortune["advice_body"])
    with col3:
        st.markdown("**🎯 行動のヒント**")
        st.write(fortune["advice_action"])

    if not fortune["has_log"]:
        st.info(
            "直近の感情ログが少ないから、今日はざっくりめの占いだよ。\n"
            "emotion_log でここ数日の気分を少し記録してからまた見に来てね。"
        )

    with st.expander("最近の傾向と詳細データ（確認用）", expanded=False):
        if fortune["stats"] is None:
            st.write("まだ統計を出せるほどのデータがないみたい。")
        else:
            s = fortune["stats"]
            st.write(f"- 直近7日間のログ件数：**{s['log_count']}件**")
            st.write(f"- 平均 mood：**{s['avg_mood']:.2f} / 5**")
            st.write(f"- ポジティブな日（mood≧4）の割合：**{s['pos_ratio']*100:.1f}%**")
            st.write(f"- ネガティブな日（mood≦2）の割合：**{s['neg_ratio']*100:.1f}%**")
            st.write(f"- 連続記録日数：**{s['streak_days']}日**")
            st.write(f"- 内部スコア：**{s['score']:.1f}**（運勢判定用）")

            if df is not None:
                st.markdown("#### 直近の感情ログ（最後の10件）")
                cols = [
                    c
                    for c in ["date", "time", "mood", "memo", "tags"]
                    if c in df.columns
                ]
                st.dataframe(
                    df.sort_values("date").tail(10)[cols],
                    use_container_width=True,
                )

# ---------- タブ2：12星座占い ----------
with tab2:
    st.subheader("⭐ 12星座占い")

    default_sign = "水瓶座"  # ご主人デフォルト
    sign = st.selectbox("あなたの星座を選んでね", list(ZODIAC_MESSAGES.keys()), index=list(ZODIAC_MESSAGES.keys()).index(default_sign))

    base, extra, lucky = get_zodiac_fortune(sign)

    st.markdown(f"### 今日の {sign} のメッセージ")
    st.write(base)
    st.write(extra)

    st.markdown("#### ラッキーのヒント")
    st.write(f"・今日のラッキーアイテムのヒント：**{lucky}**")

# ---------- タブ3：タロット一枚引き ----------
with tab3:
    st.subheader("🃏 タロット一枚引き")

    topic = st.text_input("聞いてみたいテーマ（空欄でもOK）", value="今日のメッセージ")
    if st.button("カードを引く"):
        result = draw_tarot_card(topic=topic or "今日のメッセージ")

        st.markdown("### 今日のカード")
        pos = "逆位置" if result["is_reversed"] else "正位置"
        st.write(f"**{result['num']} {result['name']} （{pos}）**")
        st.caption(f"キーワード：{result['keywords']}")
        st.write(result["message"])

        st.info("※ 同じ日付・同じテーマなら、何度引いても同じカードになるようにしてあるよ。")

# ---------- タブ4：ざっくり星読み ----------
with tab4:
    st.subheader("🌌 ざっくり星読み")

    default_sign = "水瓶座"
    sign2 = st.selectbox(
        "基準にする星座",
        list(ZODIAC_MESSAGES.keys()),
        index=list(ZODIAC_MESSAGES.keys()).index(default_sign),
        key="astro_sign",
    )

    overall, work, love = get_astro_reading(sign2)

    st.markdown(f"### {sign2} さんの、ざっくり星模様")
    st.markdown("**✨ 全体運**")
    st.write(overall)

    st.markdown("**💼 仕事・お金まわり**")
    st.write(work)

    st.markdown("**💞 恋愛・人間関係**")
    st.write(love)

    st.caption("※ 本格的な天体配置ではなく、『星のイメージ』からルナが言語化したライトなメッセージだよ。")
