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
from datetime import datetime
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
    def check_ubersuggest_auth_status() -> Dict[str, Any]:
        """Ubersuggestの認証トークン検出状態および直近のクォータ状況を検査"""
        user_home = os.environ.get("USERPROFILE", "")
        candidate_tokens = [
            os.path.join(user_home, ".gemini", "antigravity", "mcp_oauth_tokens.json"),
            os.path.join(user_home, ".gemini", "antigravity-cli", "mcp_oauth_tokens.json")
        ]
        candidate_configs = [
            os.path.join(user_home, ".gemini", "antigravity", "mcp_config.json"),
            os.path.join(user_home, ".gemini", "config", "mcp_config.json"),
            os.path.join(user_home, ".gemini", "antigravity-cli", "mcp_config.json")
        ]

        token_found = False
        token_preview = ""
        source_file = ""

        # 1. トークンファイルの走査
        for tf in candidate_tokens:
            if os.path.exists(tf):
                try:
                    with open(tf, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        if data.get("access_token"):
                            token_found = True
                            token_preview = str(data["access_token"])[:8] + "..."
                            source_file = os.path.basename(tf)
                            break
                        for k, v in data.items():
                            if isinstance(v, dict):
                                if v.get("token") and isinstance(v["token"], dict) and v["token"].get("access_token"):
                                    token_found = True
                                    token_preview = str(v["token"]["access_token"])[:8] + "..."
                                    source_file = os.path.basename(tf)
                                    break
                                elif v.get("access_token"):
                                    token_found = True
                                    token_preview = str(v["access_token"])[:8] + "..."
                                    source_file = os.path.basename(tf)
                                    break
                    if token_found:
                        break
                except Exception:
                    pass

        # 2. config ファイルの走査 (Authorization ヘッダー)
        if not token_found:
            for cf in candidate_configs:
                if os.path.exists(cf):
                    try:
                        with open(cf, "r", encoding="utf-8-sig") as f:
                            cfg = json.load(f)
                        uber = cfg.get("mcpServers", {}).get("ubersuggest", {})
                        auth_hdr = uber.get("headers", {}).get("Authorization", "")
                        if auth_hdr:
                            token_found = True
                            tok = auth_hdr.replace("Bearer ", "").strip()
                            token_preview = tok[:8] + "..."
                            source_file = os.path.basename(cf)
                            break
                    except Exception:
                        pass

        # 3. 直近のAPIアーカイブからクォータ枯渇状況を検知
        quota_status = "NORMAL"
        quota_msg = "認証済み (利用可能)"
        archives = DataManager.load_raw_archive()
        if archives:
            latest_arc = archives[-1]
            resp_str = str(latest_arc.get("response", ""))
            if "daily reports limit" in resp_str or "HTTP 403" in resp_str:
                quota_status = "EXHAUSTED"
                quota_msg = "無料枠上限(100回/日) 到達中"
            elif "HTTP 429" in resp_str or "Rate limited" in resp_str:
                quota_status = "RATE_LIMITED"
                quota_msg = "レート制限中"

        if not token_found:
            return {
                "authenticated": False,
                "status_code": "NO_TOKEN",
                "label": "未認証 (トークン未検出)",
                "color_bg": "#fef2f2",
                "color_fg": "#b91c1c",
                "details": "mcp_oauth_tokens.json または mcp_config.json にトークンが見つかりません。"
            }

        if quota_status == "EXHAUSTED":
            return {
                "authenticated": True,
                "status_code": "EXHAUSTED",
                "label": f"認証済: 本日枠枯渇 ({token_preview})",
                "color_bg": "#fffbeb",
                "color_fg": "#b45309",
                "details": f"ソース: {source_file}\n本日分のUbersuggest無料枠(100レポート)を消化済みです。\n明日リセットされるか、ローカルキャッシュによる判定はAPI消費0で即時可能です。"
            }
        elif quota_status == "RATE_LIMITED":
            return {
                "authenticated": True,
                "status_code": "RATE_LIMITED",
                "label": f"認証済: 一時制限中 ({token_preview})",
                "color_bg": "#fffbeb",
                "color_fg": "#d97706",
                "details": f"ソース: {source_file}\n短時間のAPIリクエスト制限がかかっています。少し時間をおいてください。"
            }
        else:
            return {
                "authenticated": True,
                "status_code": "OK",
                "label": f"認証済: 正常稼働 ({token_preview})",
                "color_bg": "#f0fdf4",
                "color_fg": "#15803d",
                "details": f"ソース: {source_file}\nUbersuggest MCP API接続準備完了。"
            }

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
        """Tier 1: raw_api_archive.json を読み込み、API監査履歴を返す（ネスト構造も自動平坦化）"""
        if not os.path.exists(FILE_RAW_ARCHIVE):
            return []
        try:
            with open(FILE_RAW_ARCHIVE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)

            # PowerShellの再帰シリアライズで "value": [...] がネストしている場合の再帰的平坦化
            flat_items = []
            def _flatten(node):
                if isinstance(node, list):
                    for elem in node:
                        _flatten(elem)
                elif isinstance(node, dict):
                    if "value" in node and isinstance(node["value"], (list, dict)):
                        _flatten(node["value"])
                    if "id" in node and "endpoint" in node:
                        flat_items.append(node)

            _flatten(data)
            return flat_items
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

    @staticmethod
    def load_latest_report_keywords() -> List[Dict[str, Any]]:
        """最新のMarkdownレポートから展開された全キーワードを抽出する"""
        latest = DataManager.get_latest_report()
        if not latest or not latest.get("content"):
            return []

        results = []
        in_table = False
        lines = latest["content"].splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("## 4. リサーチ結果テーブル"):
                in_table = True
                continue
            if in_table and line.startswith("## "):
                break
            if in_table and line.startswith("|") and not line.startswith("| :---") and not line.startswith("| 判定"):
                parts = [p.strip() for p in line.split("|")]
                # [ '', star, kw, typeLabel, vol, sd, intent, '' ]
                if len(parts) >= 6:
                    star = parts[1]
                    kw = parts[2]
                    t_lbl = parts[3]
                    vol_s = parts[4]
                    sd_s = parts[5]
                    vol = int(vol_s.replace(",", "")) if vol_s.isdigit() else None
                    sd = int(sd_s) if sd_s.isdigit() else None

                    results.append({
                        "star_rating": star,
                        "keyword": kw,
                        "expansion_type": t_lbl,
                        "volume": vol,
                        "sd": sd,
                        "seed_keyword": latest["file_name"].replace("report_", "").replace(".md", ""),
                        "updated_at": datetime.fromtimestamp(latest["modified_time"]).strftime("%Y-%m-%d %H:%M:%S")
                    })

        return results
