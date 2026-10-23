# batch_research_worker.py
import os
import sys
import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, Any, List

HERE = Path(__file__).parent.resolve()
DB_FILE = HERE / "keywords_db.json"
CACHE_FILE = HERE / "verified_volume_cache.json"
PROGRESS_FILE = HERE / "progress_status.json"

from engine_star_evaluator import evaluate_keyword_stars, get_ubersuggest_token

def update_progress(status: str, current: int, total: int, current_kw: str, msg: str = ""):
    try:
        data = {
            "status": status,
            "current": current,
            "total": total,
            "percent": int((current / total * 100)) if total > 0 else 0,
            "current_keyword": current_kw,
            "message": msg,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

def fetch_keyword_overview(kw: str, token: str) -> Dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "keyword_overview",
            "arguments": {
                "keyword": kw,
                "locId": 2392,
                "language": "ja"
            }
        }
    }
    req = urllib.request.Request(
        "https://ubersuggest-mcp.neilpatelapi.com/mcp",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            for line in content.split("\n"):
                if line.startswith("data:"):
                    raw = json.loads(line[5:].strip())
                    if "result" in raw and "content" in raw["result"]:
                        for c in raw["result"]["content"]:
                            if c.get("type") == "text":
                                return json.loads(c.get("text", "{}"))
    except Exception as e:
        pass
    return {}

def run_batch_research(query_file: str):
    q_path = Path(query_file)
    if not q_path.exists():
        update_progress("ERROR", 0, 0, "", f"Query file not found: {query_file}")
        return

    with open(q_path, "r", encoding="utf-8") as f:
        q_data = json.load(f)

    keywords = q_data.get("keywords", [])
    seed = q_data.get("seed_keyword", "")
    total = len(keywords)

    if total == 0:
        update_progress("ERROR", 0, 0, "", "No keywords in query file")
        return

    token = get_ubersuggest_token()
    update_progress("STARTING", 0, total, "", "リサーチ処理を開始します...")

    # DBとキャッシュのロード
    db = {"updated_at": "", "keywords": []}
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

    existing_items = {it.get("keyword"): it for it in db.get("keywords", [])}

    for i, kw in enumerate(keywords, 1):
        msg = f"[{i}/{total}] Ubersuggest Vol & Google SERP 実測調査中..."
        update_progress("RUNNING", i, total, kw, msg)

        # 1. Vol / SD 取得
        item_entry = existing_items.get(kw, {
            "keyword": kw,
            "seed_keyword": seed,
            "expansion_type": "MEGA_BATCH",
            "volume": None,
            "sd": None,
            "star_rating": "-",
            "search_intent": "",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        # Vol / SD が未取得なら Ubersuggest API で取得
        if item_entry.get("volume") is None or item_entry.get("sd") is None:
            if token:
                ov = fetch_keyword_overview(kw, token)
                if ov:
                    vol = ov.get("search_volume", ov.get("volume"))
                    sd = ov.get("seo_difficulty", ov.get("sd"))
                    if vol is not None: item_entry["volume"] = int(vol)
                    if sd is not None: item_entry["sd"] = int(sd)
                    item_entry["search_intent"] = ov.get("search_intent", "")

        # 2. 星判定 (Google SERP 実測パイプライン)
        stars, meta = evaluate_keyword_stars(kw, token=token)
        item_entry["star_rating"] = stars
        item_entry["da_meta"] = meta
        item_entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        existing_items[kw] = item_entry

        # 各キーワードごとに即座にDBを保存してUI反映
        db["keywords"] = list(existing_items.values())
        db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)

    update_progress("COMPLETED", total, total, "", "全件のメガバッチ実測調査が完了しました！")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_batch_research(sys.argv[1])
    else:
        print("Usage: python batch_research_worker.py <query_json_file>")
