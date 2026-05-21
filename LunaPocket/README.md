# LunaPocket β（仮）

ご主人とルナで開発している、「胸ポケットサイズの相棒 AI」 **LunaPocket** の実験用プロジェクトです。

## フォルダ構成（WIP）

- `emotion_log/`  
  感情ログアプリ。毎日の気分や一言メモを記録して、後から振り返るコア機能。

- `char_growth/`  
  キャラクター育成・親密度システム（予定）。

- `decision_engine/`  
  今日の迷いごとを整理して、AIが選択をサポートするモジュール（予定）。

- `fortune_core/`  
  タロット・四柱推命・五行などをまとめた占いエンジン（予定）。

- `voice_assistant/`  
  音声で話しかけて操作できる簡易 AI アシスタント（予定）。

- `common/`  
  共通で使う `utils` や設定ファイルを置く予定の場所。

## セットアップ

```bash
# 仮想環境の作成（任意）
python -m venv venv
venv\Scripts\activate  # Windows の場合

# ライブラリのインストール
pip install -r requirements.txt
