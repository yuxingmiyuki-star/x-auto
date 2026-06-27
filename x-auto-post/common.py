"""generate.py と post.py で共有する設定・ユーティリティ。"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STOCK_PATH = BASE_DIR / "stock.json"

# SPEC.md の既定パス。.env の LOG_DIR / READING_DIR で上書きできる。
DEFAULT_LOG_DIR = r"C:\Users\yuxin\Documents\囃子米\log"
DEFAULT_READING_DIR = r"C:\Users\yuxin\Documents\囃子米\読書記録"

LOG_DIR = os.environ.get("LOG_DIR", DEFAULT_LOG_DIR)
READING_DIR = os.environ.get("READING_DIR", DEFAULT_READING_DIR)

# テキストとして読み込む拡張子
TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".text"}


def load_stock():
    """stock.json を読み込んでリストで返す。無ければ空リスト。"""
    if not STOCK_PATH.exists():
        return []
    try:
        data = json.loads(STOCK_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def save_stock(stock):
    """ストックを stock.json に書き戻す。"""
    STOCK_PATH.write_text(
        json.dumps(stock, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def read_materials(directory, max_chars=20000):
    """指定フォルダ内のテキストファイルを読み込んで結合した文字列を返す。"""
    root = Path(directory)
    if not root.exists():
        return ""

    chunks = []
    total = 0
    # 新しいファイルを優先（更新日時の降順）
    files = sorted(
        (p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        if not text:
            continue
        block = f"--- {path.name} ---\n{text}\n"
        chunks.append(block)
        total += len(block)
        if total >= max_chars:
            break

    return "\n".join(chunks)[:max_chars]
