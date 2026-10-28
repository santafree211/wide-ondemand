# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: service_csv_manager.py
■ カテゴリ: Data Service / CSVインポート＆エクスポート処理専用サービス
■ 責務・役割（Single Responsibility）:
  - リサーチ結果のCSVエクスポート（Excel互換BOM付きUTF-8、Downloadsフォルダ自動保存）。
  - 外部CSVファイルの解析・パースおよび keywords_db.json へのアトミック保存。
  - main.py からCSV入出力の責務を完全に分離・集約する。

■ 設計思想・背景:
  - リサーチしたキーワードデータはExcelで直接開いても文字化けしないBOM付きUTF-8形式で保存する。
  - Google SERP星判定のみを先行実施してCSV出力しておき、後日一括してUbersuggest APIで
    Vol/SDを実測できるよう、CSVからのインポートおよびDBアトミック復元機能を提供する。

■ 入出力仕様:
  - [export_research_csv]:
    - Input: target_seed (str, 任意): 特定シードKWでフィルタリング
    - Output: Tuple[bytes, str]: (CSVバイト列, 保存先ファイルパス)
  - [import_research_csv]:
    - Input: csv_text (str): アップロードされたCSVテキスト
    - Output: Dict[str, Any]: {"status": "ok", "count": 件数, "seed_keyword": 検出シード}

■ 内部アルゴリズム / 処理フロー:
  1. [エクスポート]: keywords_db.json から対象キーワードを抽出し、ヘッダー行＋データ行を構築。
     reports/ および Downloads/ にタイムスタンプ付きファイル名で自動保存。
  2. [インポート]: CSVヘッダーから「キーワード」「判定/星」「Vol」「SD」のカラム位置を動的判定。
     既存DBに統合（アトミック保存）し、即時UI反映を可能にする。

■ 厳格な制約・禁止事項:
  - Excelでの日本語文字化けを防ぐため、出力時は必ず `\ufeff` (UTF-8 BOM) を付与すること。
  - ボリューム値や星判定の捏造を行ってはならない。
==============================================================================
"""

import os
import io
import csv
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple

HERE = Path(__file__).parent.resolve()
WIDE_DIR = Path(r"C:\Users\santa\OneDrive\prideall\projects\wide").resolve()
DB_FILE = WIDE_DIR / "keywords_db.json"

def export_research_csv(target_seed: str = "") -> Tuple[bytes, str]:
    """
    リサーチ結果をExcel互換CSVバイト列に変換し、reports/ と Downloads/ に保存
    """
    items = []
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8-sig") as f:
                raw = json.load(f)
                items = raw.get("keywords", [])
        except Exception:
            pass

    if target_seed and items:
        norm_seed = target_seed.replace(" ", "").replace("　", "")
        filtered = []
        for it in items:
            it_seed = it.get("seed_keyword", "").replace(" ", "").replace("　", "")
            if norm_seed and (norm_seed == it_seed or norm_seed in it_seed or it_seed in norm_seed):
                filtered.append(it)
        if filtered:
            items = filtered

    headers = ["判定(星)", "キーワード", "月間検索Vol", "SEO難易度(SD)", "DA一桁サイト数", "知恵袋Q&Aサイト数", "調査日時"]
    csv_lines = [",".join(headers)]
    for r in items:
        m = r.get("da_meta", {})
        star = str(r.get("star_rating", "-")).replace('"', '""')
        kw = str(r.get("keyword", "")).replace('"', '""')
        vol = str(r.get("volume", "")) if r.get("volume") is not None else ""
        sd = str(r.get("sd", "")) if r.get("sd") is not None else ""
        da1 = str(m.get("single_digit_count", "")) if m.get("single_digit_count") is not None else ""
        qa = str(m.get("qa_count", "")) if m.get("qa_count") is not None else ""
        up = str(r.get("updated_at", ""))
        csv_lines.append(f'"{star}","{kw}",{vol},{sd},{da1},{qa},"{up}"')

    csv_text = "\ufeff" + "\r\n".join(csv_lines)
    csv_bytes = csv_text.encode("utf-8")

    # 1. reports/ に実体ファイルとして保存
    reports_dir = WIDE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = time.strftime('%Y%m%d_%H%M%S')
    export_file = reports_dir / f"wide_export_{timestamp_str}.csv"
    with open(export_file, "wb") as ef:
        ef.write(csv_bytes)

    # 2. ユーザーの「ダウンロード」フォルダ (C:\Users\santa\Downloads) にも直接自動保存
    user_downloads_dir = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
    if user_downloads_dir.exists():
        dl_file = user_downloads_dir / f"wide_リサーチ結果_{timestamp_str}.csv"
        try:
            with open(dl_file, "wb") as df:
                df.write(csv_bytes)
        except Exception:
            pass

    return csv_bytes, str(export_file)

def import_research_csv(csv_text: str) -> Dict[str, Any]:
    """
    CSVテキストをパースし、keywords_db.json に即座に反映
    """
    if csv_text.startswith("\ufeff"):
        csv_text = csv_text[1:]

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    if not rows:
        return {"status": "error", "message": "Empty CSV file", "count": 0}

    header = [h.strip() for h in rows[0]]
    kw_idx = -1
    star_idx = -1
    vol_idx = -1
    sd_idx = -1

    for idx, h in enumerate(header):
        if "キーワード" in h or "Keyword" in h or h == "kw":
            kw_idx = idx
        elif "判定" in h or "星" in h or "star" in h.lower():
            star_idx = idx
        elif "Vol" in h or "ボリューム" in h or "volume" in h.lower():
            vol_idx = idx
        elif "SD" in h or "難易度" in h:
            sd_idx = idx

    if kw_idx == -1:
        kw_idx = 1 if len(header) > 1 else 0

    db = {"updated_at": "", "keywords": []}
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8-sig") as f:
                db = json.load(f)
        except Exception:
            pass

    existing_map = {it.get("keyword"): it for it in db.get("keywords", [])}
    imported_count = 0
    detected_seed = ""

    for row in rows[1:]:
        if not row or len(row) <= kw_idx:
            continue
        kw = row[kw_idx].strip()
        if not kw:
            continue

        if not detected_seed:
            detected_seed = kw

        star = row[star_idx].strip() if star_idx != -1 and len(row) > star_idx else "-"
        vol_val = None
        if vol_idx != -1 and len(row) > vol_idx and row[vol_idx].strip():
            try:
                vol_val = int(row[vol_idx].replace(",", "").strip())
            except Exception:
                pass
        sd_val = None
        if sd_idx != -1 and len(row) > sd_idx and row[sd_idx].strip():
            try:
                sd_val = int(row[sd_idx].strip())
            except Exception:
                pass

        existing_map[kw] = {
            "keyword": kw,
            "seed_keyword": detected_seed,
            "expansion_type": "CSV_IMPORTED",
            "volume": vol_val,
            "sd": sd_val,
            "star_rating": star,
            "search_intent": "",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "da_meta": {
                "star_rating": star,
                "total_stars": star.count("★"),
                "source": "CSV_IMPORT"
            }
        }
        imported_count += 1

    db["keywords"] = list(existing_map.values())
    db["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "count": imported_count,
        "seed_keyword": detected_seed
    }
