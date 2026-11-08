# batch_serp_deep_evaluator.py
import json
import time
from pathlib import Path
from engine_star_evaluator import evaluate_keyword_stars

HERE = Path(__file__).parent.resolve()
QUERY_FILE = HERE / "temp_sidecar_query.json"
CACHE_FILE = HERE / "verified_volume_cache.json"
DB_FILE = HERE / "keywords_db.json"
CSV_FILE = HERE / "keywords.csv"

def run_deep_serp_evaluation():
    if not QUERY_FILE.exists():
        print("Query file not found.")
        return

    with open(QUERY_FILE, "r", encoding="utf-8") as f:
        query_data = json.load(f)

    keywords = query_data.get("keywords", [])
    seed = query_data.get("seed_keyword", "")

    print(f"=== STARTING DEEP SERP & DA EVALUATION FOR {len(keywords)} TERMS ===")
    print(f"Seed: {seed}")

    # Load cache
    cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    # Load DB
    db_items = []
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8-sig") as f:
                raw_db = json.load(f)
                db_items = raw_db.get("keywords", [])
        except Exception:
            db_items = []

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    results = []

    for idx, kw in enumerate(keywords, 1):
        kw_clean = kw.strip()
        print(f"\n[{idx}/{len(keywords)}] Evaluating SERP & DA for: '{kw_clean}'...")

        try:
            star, meta = evaluate_keyword_stars(kw_clean)
            print(f"  -> Result: {star} (DAs一桁: {meta['single_digit_count']}個, Q&A: {meta['qa_count']}個)")
        except Exception as e:
            print(f"  -> Error: {e}")
            star = "-"
            meta = {}

        # Update cache
        existing = cache.get(kw_clean, {})
        vol = existing.get("volume", None)
        sd = existing.get("sd", None)

        cache[kw_clean] = {
            "volume": vol,
            "sd": sd,
            "star_rating": star,
            "verified_at": now_str,
            "da_meta": meta
        }

        # Update DB
        found = False
        for it in db_items:
            if it.get("keyword") == kw_clean:
                it["star_rating"] = star
                it["updated_at"] = now_str
                it["da_meta"] = meta
                found = True
                break
        if not found:
            db_items.append({
                "keyword": kw_clean,
                "seed_keyword": seed,
                "expansion_type": "DEEP_SERP",
                "volume": vol,
                "sd": sd,
                "star_rating": star,
                "search_intent": "",
                "created_at": now_str,
                "updated_at": now_str,
                "da_meta": meta
            })

        # Save periodically
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"updated_at": now_str, "keywords": db_items}, f, ensure_ascii=False, indent=2)

        time.sleep(1) # respectful interval

    print("\n=== DEEP SERP EVALUATION FINISHED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_deep_serp_evaluation()
