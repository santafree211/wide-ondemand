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

from engine_star_evaluator import evaluate_keyword_stars, evaluate_keyword_stars_preflight, get_ubersuggest_token

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
    def _do_call(tk: str):
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
                "Authorization": f"Bearer {tk}"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            for line in content.split("\n"):
                if line.startswith("data:"):
                    raw = json.loads(line[5:].strip())
                    if raw.get("result", {}).get("isError"):
                        err_txt = raw.get("result", {}).get("content", [{}])[0].get("text", "")
                        if "401" in err_txt or "invalid token" in err_txt.lower():
                            return "401"
                    if "result" in raw and "content" in raw["result"]:
                        for c in raw["result"]["content"]:
                            if c.get("type") == "text":
                                return json.loads(c.get("text", "{}"))
        return {}

    try:
        res = _do_call(token)
        if res == "401":
            # Auto-refresh and retry once
            from ubersuggest_token_manager import refresh_access_token
            ok, new_tk, _ = refresh_access_token()
            if ok and new_tk:
                res = _do_call(new_tk)
        if isinstance(res, dict):
            return res
    except urllib.error.HTTPError as e:
        if e.code == 401:
            try:
                from ubersuggest_token_manager import refresh_access_token
                ok, new_tk, _ = refresh_access_token()
                if ok and new_tk:
                    res = _do_call(new_tk)
                    if isinstance(res, dict):
                        return res
            except Exception:
                pass
    except Exception:
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
        msg = f"[{i}/{total}] 【予選】SERP星判定中: '{kw}'"
        update_progress("RUNNING", i, total, kw, msg)

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

        # ========================================================
        # STEP 1: 【予選】SERPによる星（ライバルの弱さ）の判定
        # ※Ubersuggestの100枠を温存するため、まずSERPで星を高速チェック (API消費0)
        # ========================================================
        stars, meta = evaluate_keyword_stars_preflight(kw)
        item_entry["star_rating"] = stars
        item_entry["da_meta"] = meta
        item_entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        has_stars = bool(stars and stars != "-" and ("★" in stars or meta.get("total_stars", 0) > 0))

        # ========================================================
        # SERP単体実行モード (API消費ゼロ)
        # ========================================================
        is_serp_only = (q_data.get("mode") == "serp_only")
        if is_serp_only:
            if has_stars:
                msg_star = f"[{i}/{total}] 🌟 星あり合格！({stars}): '{kw}' (API消費: 0)"
                item_entry["status"] = "SERP_QUALIFIED (星★合格)"
            else:
                msg_star = f"[{i}/{total}] ❌ 星0（強豪独占）: '{kw}' (API消費: 0)"
                item_entry["status"] = "FILTERED_OUT (星0・強豪独占)"
            update_progress("RUNNING", i, total, kw, msg_star)
            existing_items[kw] = item_entry
            db["keywords"] = list(existing_items.values())
            db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            time.sleep(0.2)
            continue

        # ========================================================
        # STEP 2: 【足切り排除】星なし（星0 / "-"）の場合は即脱落！
        # ========================================================
        has_stars = bool(stars and stars != "-" and ("★" in stars or meta.get("total_stars", 0) > 0))

        if not has_stars:
            # 星がつかない（強豪独占・勝てないKW）は、Ubersuggestの枠を一切使わずに排除！
            msg_skip = f"[{i}/{total}] ❌ 星0（勝算なし）のため足切り排除（API枠温存）: '{kw}'"
            print(msg_skip)
            update_progress("RUNNING", i, total, kw, msg_skip)
            item_entry["volume"] = 0
            item_entry["sd"] = None
            item_entry["status"] = "FILTERED_OUT (星0・勝算なし)"
            existing_items[kw] = item_entry

            # DB保存
            db["keywords"] = list(existing_items.values())
            db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            time.sleep(0.3)
            continue

        # ========================================================
        # STEP 3: 【本試験】星★以上の精鋭KWのみ、Ubersuggest APIでボリューム実測！
        # ========================================================
        msg_hit = f"[{i}/{total}] 🌟 星あり合格！({stars}) 【本試験】Ubersuggest Vol実測中: '{kw}'"
        print(msg_hit)
        update_progress("RUNNING", i, total, kw, msg_hit)

        if item_entry.get("volume") is None or item_entry.get("volume") == 0:
            if token:
                ov = fetch_keyword_overview(kw, token)
                if ov:
                    vol = ov.get("search_volume", ov.get("volume"))
                    sd = ov.get("seo_difficulty", ov.get("sd"))
                    if vol is not None: item_entry["volume"] = int(vol)
                    if sd is not None: item_entry["sd"] = int(sd)
                    item_entry["search_intent"] = ov.get("search_intent", "")

        existing_items[kw] = item_entry

        # 各キーワードごとに即座にDBを保存してUI反映
        db["keywords"] = list(existing_items.values())
        db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)

    if q_data.get("mode") == "serp_only":
        update_progress("COMPLETED", total, total, "", "【完了】全件のSERP星判定が完了しました！(Ubersuggest API消費: 0回)")
    else:
        update_progress("COMPLETED", total, total, "", "全件のメガバッチ実測調査が完了しました！")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_batch_research(sys.argv[1])
    else:
        print("Usage: python batch_research_worker.py <query_json_file>")
