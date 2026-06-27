"""ツイート候補を作って、ブラウザ（localhost）で選んでストックに追加する。

  python generate.py

【0円モード】API は使いません。代わりに:
  1) このツールが「Claudeへのお願い文」を素材付きで作る
  2) それを claude.ai（あなたのMAXプラン）に貼り付けて20案を出してもらう
  3) 返ってきた20案をこのツールに貼り戻す
  4) 気に入ったカードをクリックして stock.json に追加
"""
import threading
import webbrowser

from flask import Flask, jsonify, render_template_string, request

from common import LOG_DIR, READING_DIR, load_stock, read_materials, save_stock

NUM_TWEETS = 20
HOST = "127.0.0.1"
PORT = 5000

# claude.ai に貼り付けてもらう「お願い文」のテンプレート
PROMPT_TEMPLATE = """あなたは「囃子米（はやしまい）」さん本人としてXに投稿するツイートを書きます。
アカウントのコンセプトは「悩みをアプリにする」。
日々の気づきや読書から生まれた考えを、悩んでいる人にそっと効く形で発信します。

文体・トーンの条件:
- 軽め。自分の言葉で、肩の力が抜けた話し方。
- 説教くさくしない。断定しすぎず、自分の実感として書く。
- 悩みに効く考え方・視点の転換が伝わるようにする。
- 1ツイートは日本語140文字以内。
- ハッシュタグや絵文字は使いすぎない（基本なし〜1個まで）。
- 素材の言い回しをそのままコピーせず、囃子米さんの言葉として再構成する。

以下がわたしの素材です。

# 日々のログ（メイン素材）
{log}

# 読書記録 / Kindleハイライト（サブ素材）
{reading}

この素材をもとにツイート案を「ちょうど{n}個」作ってください。
出力ルール:
- 1行に1ツイート、合計{n}行。
- 行頭に番号・記号・「・」などは付けず、ツイート本文だけを書く。
- ツイートの途中で改行しない（1案＝1行）。
- 前置き・説明・まとめは書かず、ツイートだけを出力する。"""


def build_prompt():
    """素材を読み込んで、claude.ai に貼り付ける「お願い文」を作る。"""
    log_text = read_materials(LOG_DIR)
    reading_text = read_materials(READING_DIR)
    return PROMPT_TEMPLATE.format(
        log=log_text or "（ログなし）",
        reading=reading_text or "（読書記録なし）",
        n=NUM_TWEETS,
    ), bool(log_text or reading_text)


def parse_tweets(text):
    """claude.ai から貼り付けられたテキストを、1行1ツイートとして分解する。"""
    tweets = []
    for line in text.splitlines():
        # 行頭の番号や記号（1. / 1) / - / ・ / ＊ など）を取り除く
        cleaned = line.strip().lstrip("0123456789.)）、・-－*＊●○•　 ").strip()
        if cleaned:
            tweets.append(cleaned)
    return tweets


# ---- ブラウザUI（Flask） -------------------------------------------------

app = Flask(__name__)
CANDIDATES = []  # 貼り付けから分解した候補（メモリ上）

PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ツイート候補づくり</title>
<style>
  body{font-family:system-ui,-apple-system,"Hiragino Sans",sans-serif;
       background:#15202b;color:#e7e9ea;margin:0;padding:24px;max-width:900px;margin:0 auto;}
  h2{font-size:16px;border-left:4px solid #1d9bf0;padding-left:8px;}
  .step{background:#1e2732;border:1px solid #38444d;border-radius:14px;padding:18px;margin-bottom:18px;}
  textarea{width:100%;box-sizing:border-box;background:#0e151c;color:#e7e9ea;
           border:1px solid #38444d;border-radius:10px;padding:12px;font-size:14px;line-height:1.6;}
  button,a.btn{background:#1d9bf0;color:#fff;border:0;border-radius:999px;
         padding:9px 18px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block;}
  a.btn.open{background:#2f3b47;}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px;}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;margin-top:12px;}
  .card{background:#1e2732;border:1px solid #38444d;border-radius:14px;padding:16px;
        cursor:pointer;transition:.15s;white-space:pre-wrap;line-height:1.6;}
  .card:hover{border-color:#1d9bf0;}
  .card.added{border-color:#00ba7c;opacity:.55;cursor:default;}
  .len{font-size:12px;color:#8b98a5;margin-top:10px;}
  .len.over{color:#f4212e;}
  .count{color:#8b98a5;font-size:14px;}
  .hint{color:#8b98a5;font-size:13px;margin:6px 0;}
  .warn{color:#ffd060;font-size:13px;}
</style></head>
<body>
  <h1>ツイート候補づくり（0円モード）</h1>
  <p class="count">いまのストック: <b id="stock">{{stock}}</b> 件</p>
  {% if not has_material %}<p class="warn">⚠ 素材フォルダが読めませんでした。.env の LOG_DIR / READING_DIR を確認してください（今は空のまま進められます）。</p>{% endif %}

  <div class="step">
    <h2>① このお願い文をコピーして claude.ai に貼る</h2>
    <p class="hint">下の文をコピー → 「claude.aiを開く」→ チャットに貼って送信 → 20個の案が返ってきます。</p>
    <textarea id="prompt" rows="10" readonly>{{prompt}}</textarea>
    <div class="row">
      <button onclick="copyPrompt()">お願い文をコピー</button>
      <a class="btn open" href="https://claude.ai/new" target="_blank">claude.aiを開く</a>
      <span id="copied" class="hint"></span>
    </div>
  </div>

  <div class="step">
    <h2>② Claudeの返事（20個）を、ここに貼り付ける</h2>
    <p class="hint">claude.ai が出した案を全部コピーして、下に貼り付け →「読み込む」を押す。</p>
    <textarea id="paste" rows="10" placeholder="ここに貼り付け"></textarea>
    <div class="row"><button onclick="parsePaste()">読み込む</button>
      <span id="parsed" class="hint"></span></div>
  </div>

  <div class="step">
    <h2>③ 気に入ったカードをクリックしてストックに追加</h2>
    <p class="hint">クリックすると緑になり、stock.json に保存されます。何個でもOK。</p>
    <div class="grid" id="grid"></div>
  </div>

<script>
function copyPrompt(){
  const t=document.getElementById('prompt'); t.select();
  navigator.clipboard.writeText(t.value).then(()=>{document.getElementById('copied').textContent='コピーしました';});
}
async function parsePaste(){
  const text=document.getElementById('paste').value;
  const r=await fetch('/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  const d=await r.json();
  document.getElementById('parsed').textContent=d.tweets.length+' 個 読み込みました';
  const grid=document.getElementById('grid'); grid.innerHTML='';
  d.tweets.forEach((t,i)=>{
    const el=document.createElement('div'); el.className='card';
    const over=t.length>140?' over':'';
    el.innerHTML=t.replace(/</g,'&lt;')+'<div class="len'+over+'">'+t.length+' 文字</div>';
    el.onclick=()=>add(el,i); grid.appendChild(el);
  });
}
async function add(el,i){
  if(el.classList.contains('added'))return;
  const r=await fetch('/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:i})});
  const d=await r.json();
  if(d.ok){el.classList.add('added');document.getElementById('stock').textContent=d.count;}
}
</script>
</body></html>"""


@app.route("/")
def index():
    prompt, has_material = build_prompt()
    return render_template_string(
        PAGE, prompt=prompt, has_material=has_material, stock=len(load_stock())
    )


@app.route("/parse", methods=["POST"])
def parse():
    global CANDIDATES
    text = (request.get_json(silent=True) or {}).get("text", "")
    CANDIDATES = parse_tweets(text)
    return jsonify(tweets=CANDIDATES)


@app.route("/add", methods=["POST"])
def add():
    idx = (request.get_json(silent=True) or {}).get("index")
    if not isinstance(idx, int) or not (0 <= idx < len(CANDIDATES)):
        return jsonify(ok=False, error="invalid index"), 400
    text = CANDIDATES[idx]
    stock = load_stock()
    if text not in stock:
        stock.append(text)
        save_stock(stock)
    return jsonify(ok=True, count=len(stock))


def main():
    url = f"http://{HOST}:{PORT}/"
    print("ブラウザでツイート候補づくりの画面を開きます。")
    print(f"開かない場合はこのURLをブラウザに貼ってください: {url}")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
