# X自動投稿ツール 仕様書

## コンセプト

「悩みをアプリにする」というXアカウントのコンセプトに合わせ、
自分の読書・日々の気づきから生まれた考えを発信する。

## 素材（入力）

- **メイン**: `C:\Users\yuxin\Documents\囃子米\log\` （日々の感じたこと・核となる考え）
- **サブ**: `C:\Users\yuxin\Documents\囃子米\読書記録\` （Kindleハイライト）

> パスは `.env` の `LOG_DIR` / `READING_DIR` で上書きできます（未設定なら上記が既定値）。

## ツイート生成

> **実装メモ（0円モード）**: Claude API は別課金（MAXプランに含まれない）ため、
> 追加費用ゼロで使えるよう **コピペ方式** に変更している。
> `generate.py` が素材入りの「お願い文」を作る → それを claude.ai（MAXプラン）に
> 貼って20案を出してもらう → 返事をツールに貼り戻す、という流れ。

- log/ と 読書記録/ を読み込み、囃子米さんの言葉として自然なツイートを生成
- 1回の生成で **20パターン** 作成
- トーン：軽め・自分の言葉・悩みに効く考え方として

## 選択UI

- **ブラウザで表示**（localhost）
- 候補一覧をカード形式で表示
- 気に入ったものをクリックしてストックに追加
- ストックはローカルのJSONファイルで管理（`stock.json`）

## 自動投稿

- ストックから毎朝 **9時** に1本自動投稿
- X API（無料プラン）を使用
- 投稿済みのものはストックから削除

## 実行方法

```bash
# ツイート候補を生成してブラウザで選択
python generate.py

# 自動投稿（cronで毎朝9時に実行）
python post.py
```

毎朝9時の自動実行（cron例）:

```cron
0 9 * * * cd /path/to/x-auto-post && /usr/bin/python post.py >> post.log 2>&1
```

## 必要なAPIキー（.envファイルで管理）

（0円モードのため `ANTHROPIC_API_KEY` は不要）

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

## ファイル構成

```
x-auto-post/
├── generate.py       # 候補生成 + ブラウザUI起動
├── post.py           # 毎朝の自動投稿
├── stock.json        # 選んだツイートのストック
├── .env              # APIキー（Gitに含めない）
├── requirements.txt  # 必要なライブラリ
└── SPEC.md           # この仕様書
```
