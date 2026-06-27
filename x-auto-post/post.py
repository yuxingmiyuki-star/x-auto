"""ストックから1本をXに自動投稿する。毎朝9時に cron で実行する想定。

  python post.py

stock.json の先頭（最も古い＝最初に選んだもの）を1件投稿し、
成功したらストックから削除する。
"""
import os
import sys

import tweepy

from common import load_stock, save_stock

REQUIRED_KEYS = [
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
]


def build_client():
    """X API v2 のクライアントを生成（無料プランの POST /2/tweets 用）。"""
    missing = [k for k in REQUIRED_KEYS if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"X APIキーが未設定です: {', '.join(missing)}")

    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def main():
    stock = load_stock()
    if not stock:
        print("ストックが空です。投稿するものがありません。")
        return 0

    tweet = stock[0]
    client = build_client()

    try:
        resp = client.create_tweet(text=tweet)
    except tweepy.TweepyException as exc:
        print(f"投稿に失敗しました: {exc}", file=sys.stderr)
        return 1

    tweet_id = resp.data.get("id") if getattr(resp, "data", None) else None
    print(f"投稿しました: id={tweet_id}\n  {tweet}")

    # 投稿済みをストックから削除して保存
    stock.pop(0)
    save_stock(stock)
    print(f"ストック残り: {len(stock)} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
