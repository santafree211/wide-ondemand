# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: batch_research_worker.py
■ カテゴリ: Worker / バックグラウンドメガバッチ実行ワーカー
■ 責務・役割（Single Responsibility）:
  - リサーチクエリファイル（temp_sidecar_query.json）を受け取り、バックグラウンドで実測パイプラインを実行する。
  - Google公式SERP実測による星判定（engine_star_evaluator）と進捗トラッカー（service_progress_tracker）の連携。
  - Ubersuggest API実行時における★星付き精鋭キーワードのみのVol実測（api_overview_client）およびDB即時更新。
  - 進捗ファイル書き込みと単体API通信処理を別モジュールへ外出しし、本ファイルはループ実行専任とする。

■ 設計思想・背景:
  - Webサーバー（main.py）のスレッドをブロックせず、重い外部API連続呼び出しを安全に非同期処理する。
  - 1キーワード処理ごとに keywords_db.json と progress_status.json をアトミックに即時保存し、
    UI側でのリアルタイムストリーミング表示を担保する。

■ 入出力仕様:
  - Input: sys.argv[1] (クエリJSONファイルパス)
  - Output: keywords_db.json, progress_status.json の更新
==============================================================================
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

HERE = Path(__file__).parent.resolve()
DB_FILE = HERE / "keywords_db.json"

# 分離した進捗トラッカーモジュール
from service_progress_tracker import update_progress

# 分離した単体Vol/SD取得APIクライアント
from api_overview_client import fetch_keyword_overview
from api_batch_volume_client import fetch_mega_batch_volumes

# Google公式SERP星判定エンジン＆トークン
from engine_star_evaluator import evaluate_keyword_stars, get_ubersuggest_token

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

    # DBのロード
    db = {"updated_at": "", "keywords": []}
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

    # 前回の結果を完全に分離（今回の対象キーワードはDB内の古い判定を引き継がず新規実測）
    existing_items = {it.get("keyword"): it for it in db.get("keywords", []) if it.get("keyword") not in keywords}

    # mode == "ubersuggest" (500KW/1API メガバッチ一括実行モード)
    if q_data.get("mode") == "ubersuggest":
        update_progress("RUNNING", 0, total, "一括Vol取得中", f"Ubersuggest 1-Shotメガバッチ送信中（対象: {total} 件）...")
        vol_results = fetch_mega_batch_volumes(keywords, token)
        
        # 既存DBレコードにVol・SDを一括マージ
        db_keywords = db.get("keywords", [])
        updated_count = 0
        for it in db_keywords:
            k = it.get("keyword")
            if k in vol_results:
                v_data = vol_results[k]
                if v_data.get("volume") is not None:
                    it["volume"] = v_data["volume"]
                if v_data.get("sd") is not None:
                    it["sd"] = v_data["sd"]
                it["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                updated_count += 1
        
        db["keywords"] = db_keywords
        db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

        update_progress("COMPLETED", total, total, "", f"【完了】1-Shotメガバッチ成功！{updated_count}件のボリュームを一括更新しました (API消費: わずか1回)")
        return

    # mode == "serp_only" の場合（Google公式SERP星判定ループ）
    for i, kw in enumerate(keywords, 1):
        msg = f"[{i}/{total}] Google公式SERP星判定中: '{kw}'"
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

        # STEP 1: Google公式実測SERPによる星（ライバルの弱さ）の判定
        stars, meta = evaluate_keyword_stars(kw, token=token)
        item_entry["star_rating"] = stars
        item_entry["da_meta"] = meta
        item_entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        has_stars = bool(stars and stars != "-" and ("★" in stars or meta.get("total_stars", 0) > 0))

        # SERP単体実行モード (Google公式実測SERPの星判定のみ)
        is_serp_only = (q_data.get("mode") == "serp_only")
        if is_serp_only:
            if has_stars:
                msg_star = f"[{i}/{total}] 🌟 Google星あり合格！({stars}): '{kw}'"
                item_entry["status"] = "SERP_QUALIFIED (星★合格)"
            else:
                msg_star = f"[{i}/{total}] ❌ 星0（強豪独占）: '{kw}'"
                item_entry["status"] = "FILTERED_OUT (星0・強豪独占)"
            update_progress("RUNNING", i, total, kw, msg_star)
            existing_items[kw] = item_entry
            db["keywords"] = list(existing_items.values())
            db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            time.sleep(0.3)
            continue

        # STEP 2: 【足切り排除】星なし（星0 / "-"）の場合は即脱落！
        if not has_stars:
            msg_skip = f"[{i}/{total}] ❌ 星0（勝算なし）のため足切り排除（API枠温存）: '{kw}'"
            print(msg_skip)
            update_progress("RUNNING", i, total, kw, msg_skip)
            item_entry["volume"] = 0
            item_entry["sd"] = None
            item_entry["status"] = "FILTERED_OUT (星0・勝算なし)"
            existing_items[kw] = item_entry
            db["keywords"] = list(existing_items.values())
            db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            time.sleep(0.3)
            continue

        # STEP 3: 【本試験】星★以上の精鋭KWのみ、Ubersuggest APIでボリューム実測！
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
