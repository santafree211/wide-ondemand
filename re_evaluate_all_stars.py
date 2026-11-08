import sys
import json
import time
from pathlib import Path
from engine_star_evaluator import evaluate_keyword_stars

HERE = Path(__file__).parent.resolve()
DB_FILE = HERE / "keywords_db.json"

def main():
    if not DB_FILE.exists():
        print("keywords_db.json not found")
        return

    with open(DB_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    keywords = db.get("keywords", [])
    total = len(keywords)
    print(f"Starting Google SERP re-evaluation for {total} keywords...")

    for i, item in enumerate(keywords, 1):
        kw = item.get("keyword", "")
        old_stars = item.get("star_rating", "")
        try:
            new_stars, meta = evaluate_keyword_stars(kw)
            item["star_rating"] = new_stars
            item["da_meta"] = meta
            total_s = meta.get("total_stars", 0)
            src = meta.get("source", "")
            print(f"[{i}/{total}] {kw}: {old_stars} -> {new_stars} (stars: {total_s}, source: {src})")
        except Exception as e:
            print(f"[{i}/{total}] {kw} error: {e}")
        time.sleep(0.8)

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("All keywords successfully re-evaluated and saved to keywords_db.json!")

if __name__ == "__main__":
    main()
