"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: service_data_manager.py
   - カテゴリ: service (データアクセス・集計管理)
   - 責務: wideデータストア (keywords_db.json, verified_volume_cache.json,
     raw_api_archive.json, reports/) の読み取り、星別集計、検索フィルター、
     最新レポート検出などのデータ管理機能を提供。

2. 入出力・依存関係:
   - 入力: フィルタリング条件、検索クエリ
   - 出力: キーワード一覧 (リスト/辞書)、サマリー統計情報、最新レポートテキスト
   - 外部依存: json, os, glob, core_config, core_logger

3. AI改修時の指針・注意点:
   - JSONファイル読み取り時は UTF-8 を指定し、ファイル不存在や破損時は空データを
     安全に返却するフォールバック設計を徹底すること。
================================================================================
"""

import os
import json
import glob
from typing import Dict, List, Any, Optional
from core_config import (
    FILE_KEYWORDS_DB,
    FILE_CACHE,
    FILE_RAW_ARCHIVE,
    DIR_REPORTS,
    FILE_KEYWORDS_CSV
)
from core_logger import log_warn, log_error

class DataManager:
    """wideデータストア読み込み＆サマリー集計クラス"""

    @staticmethod
    def load_keywords_db() -> List[Dict[str, Any]]:
        """Tier 1: keywords_db.json を読み込み、リストとして返す"""
        if not os.path.exists(FILE_KEYWORDS_DB):
            return []
        try:
            with open(FILE_KEYWORDS_DB, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data.get("keywords", [])
        except Exception as e:
            log_error(f"Failed to load keywords_db.json: {e}")
            return []

    @staticmethod
    def load_cache() -> Dict[str, Any]:
        """Tier 2: verified_volume_cache.json を読み込み、辞書として返す"""
        if not os.path.exists(FILE_CACHE):
            return {}
        try:
            with open(FILE_CACHE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Failed to load verified_volume_cache.json: {e}")
            return {}

    @staticmethod
    def load_raw_archive() -> List[Dict[str, Any]]:
        """Tier 1: raw_api_archive.json を読み込み、API監査履歴を返す"""
        if not os.path.exists(FILE_RAW_ARCHIVE):
            return []
        try:
            with open(FILE_RAW_ARCHIVE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Failed to load raw_api_archive.json: {e}")
            return []

    @staticmethod
    def get_summary_stats() -> Dict[str, Any]:
        """マスターDB＆キャッシュの統計サマリーを計算して返す"""
        db_items = DataManager.load_keywords_db()
        cache_items = DataManager.load_cache()
        archive_items = DataManager.load_raw_archive()

        star_counts = {
            "3_star": 0,  # ☆☆☆
            "2_star": 0,  # ☆☆
            "1_star": 0,  # ☆
            "none": 0,    # -
            "unresolved": 0
        }

        for item in db_items:
            star = item.get("star_rating", "-")
            if "☆☆☆" in star:
                star_counts["3_star"] += 1
            elif "☆☆" in star:
                star_counts["2_star"] += 1
            elif "☆" in star:
                star_counts["1_star"] += 1
            elif star == "-":
                star_counts["none"] += 1
            else:
                star_counts["unresolved"] += 1

        return {
            "total_db_keywords": len(db_items),
            "total_cached_keywords": len(cache_items),
            "total_api_calls_logged": len(archive_items),
            "star_counts": star_counts,
            "last_updated": db_items[0].get("updated_at", "-") if db_items else "-"
        }

    @staticmethod
    def get_latest_report() -> Optional[Dict[str, Any]]:
        """reports/ ディレクトリから最新のMarkdownレポートを取得する"""
        if not os.path.exists(DIR_REPORTS):
            return None
        md_files = glob.glob(os.path.join(DIR_REPORTS, "*.md"))
        if not md_files:
            return None

        # 更新日時で最新順ソート
        md_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        latest_file = md_files[0]
        try:
            with open(latest_file, "r", encoding="utf-8-sig") as f:
                content = f.read()
            return {
                "file_path": latest_file,
                "file_name": os.path.basename(latest_file),
                "modified_time": os.path.getmtime(latest_file),
                "content": content
            }
        except Exception as e:
            log_error(f"Failed to read latest report: {e}")
            return None
