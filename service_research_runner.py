# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: service_research_runner.py
■ カテゴリ: Execution / リサーチ実行・プロセス管理サービス
■ 責務・役割（Single Responsibility）:
  - リサーチ実行パラメータ（seed, axes, mode）の検証とクエリJSONの生成。
  - バックグラウンドワーカー（batch_research_worker.py）の非同期プロセス起動とログ管理。
  - 前回の不要なDBレコードの安全な事前クリア（クリーンスタート制御）。

■ 設計思想・背景:
  - UIからの「Google実測SERP実行」および「Ubersuggest API実行」のリクエストを受け、
    外部プロセス（batch_research_worker.py）を安全かつ独立して非同期実行する。
  - Ubersuggest API実行時は、貴重な日次枠を浪費しないよう、直前のSERP判定で★がついた精鋭KWのみを
    自動抽出してクエリにセットする。

■ 入出力仕様:
  - [start_research_job]:
    - Input: payload (Dict[str, Any]): {"seed": str, "axis1": list, "axis2": list, "mode": "serp_only" | "ubersuggest"}
    - Output: Dict[str, Any]: {"status": "RUNNING", "pid": プロセスID, "total_count": 対象KW総数}

■ 内部アルゴリズム / 処理フロー:
  1. smart_split_seedによりシードを構文分解（slot_a, slot_b）。
  2. mode == "ubersuggest" の場合は、keywords_db.jsonから「★」付きKWのみを全件走査して抽出。
  3. mode == "serp_only" の場合は、シードおよび軸①・軸②の全KWをマージ（重複排除）。
  4. temp_sidecar_query.json を作成し、前回不要レコードをDBからアトミック除去。
  5. subprocess.Popenにより別プロセスとして batch_research_worker.py を非同期起動。

■ 厳格な制約・禁止事項:
  - UIのHTTPスレッドをブロックしないよう、ワーカーは必ず非同期（Popen）で起動すること。
  - 星のないキーワードを Ubersuggest 実行モードの対象に含めてはならない。
==============================================================================
"""

import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

HERE = Path(__file__).parent.resolve()
WIDE_DIR = Path(r"C:\Users\santa\OneDrive\prideall\projects\wide").resolve()
DB_FILE = WIDE_DIR / "keywords_db.json"
QUERY_FILE = WIDE_DIR / "temp_sidecar_query.json"
LOG_FILE = WIDE_DIR / "reports" / "sidecar_latest_run.log"

def start_research_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    リサーチジョブを初期化し、バックグラウンドワーカーを起動する
    """
    seed = payload.get("seed", "").strip()
    axis1_terms = payload.get("axis1", [])
    axis2_terms = payload.get("axis2", [])
    mode = payload.get("mode", "full")

    from generator_ai_expansion import smart_split_seed
    slot_a, slot_b = smart_split_seed(seed)

    all_kw = set()

    if mode == "ubersuggest":
        # 蓄積された★星1つ以上の全キーワードから、Vol未取得（または最新の精鋭）を最大500件抽出
        if DB_FILE.exists():
            try:
                with open(DB_FILE, "r", encoding="utf-8-sig") as f:
                    raw = json.load(f)
                unmeasured_kws = []
                for it in raw.get("keywords", []):
                    star = it.get("star_rating", "-")
                    kw = it.get("keyword")
                    if star and star != "-" and "★" in star and kw:
                        # まだVolが取得されていないものを優先
                        if it.get("volume") is None:
                            unmeasured_kws.append(kw)
                # 重複排除して先頭最大500件
                seen = set()
                for k in unmeasured_kws:
                    if k not in seen:
                        seen.add(k)
                        all_kw.add(k)
                    if len(all_kw) >= 500:
                        break
                # もし未取得が少なければ、星付き全般からも補充（最大500件）
                if len(all_kw) < 500:
                    for it in raw.get("keywords", []):
                        star = it.get("star_rating", "-")
                        kw = it.get("keyword")
                        if star and star != "-" and "★" in star and kw:
                            all_kw.add(kw)
                            if len(all_kw) >= 500:
                                break
            except Exception as e:
                print("Error reading starred keywords from db:", e)
    else:
        if seed: all_kw.add(seed)
        if slot_a: all_kw.add(slot_a)
        if slot_b: all_kw.add(slot_b)
        for t in axis1_terms:
            ct = t.strip()
            if ct: all_kw.add(ct)
        for t in axis2_terms:
            ct = t.strip()
            if ct: all_kw.add(ct)

    q_data = {
        "mode": mode,
        "seed_keyword": seed,
        "seed_keywords": [s for s in [slot_a, slot_b] if s],
        "axis1_terms": [],
        "axis2_terms": [],
        "keywords": sorted(list(all_kw))
    }

    with open(QUERY_FILE, "w", encoding="utf-8") as f:
        json.dump(q_data, f, ensure_ascii=False, indent=2)

    # 前回の結果をクリア（SERP実行時のみクリア。Ubersuggest実行時は直前の星判定結果を活かしてVolを更新する）
    if mode != "ubersuggest":
        norm_seed = seed.replace(" ", "").replace("　", "")
        if DB_FILE.exists():
            try:
                with open(DB_FILE, "r", encoding="utf-8-sig") as f:
                    raw = json.load(f)
                retained = []
                for it in raw.get("keywords", []):
                    it_seed = it.get("seed_keyword", "").replace(" ", "").replace("　", "")
                    it_kw = it.get("keyword", "")
                    if norm_seed and (norm_seed == it_seed or norm_seed in it_seed or it_seed in norm_seed):
                        continue
                    if it_kw in all_kw:
                        continue
                    retained.append(it)
                raw["keywords"] = retained
                raw["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(raw, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Error clearing previous results:", e)

    # バックグラウンドリサーチワーカーを実行
    worker_py = WIDE_DIR / "batch_research_worker.py"
    cmd = [
        sys.executable,
        "-u",
        str(worker_py),
        str(QUERY_FILE)
    ]

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, text=True, cwd=str(WIDE_DIR))

    return {
        "status": "RUNNING",
        "pid": proc.pid,
        "total_count": len(all_kw)
    }
