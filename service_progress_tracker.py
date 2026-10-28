# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: service_progress_tracker.py
■ カテゴリ: Service / バックグラウンド処理リアルタイム進捗トラッカー
■ 責務・役割（Single Responsibility）:
  - リサーチ処理の進行状況（現在KW、完了件数、総件数、パーセント、ステータス、メッセージ）の
    進捗ファイル（progress_status.json）へのアトミック書き出しに専任。
  - フロントエンドUIがポーリングして進捗バーを描画するためのデータソースを提供する。

■ 入出力仕様:
  - update_progress(status: str, current: int, total: int, current_kw: str, msg: str = "") -> None
==============================================================================
"""

import json
import time
from pathlib import Path

HERE = Path(__file__).parent.resolve()
PROGRESS_FILE = HERE / "progress_status.json"

def update_progress(status: str, current: int, total: int, current_kw: str, msg: str = "") -> None:
    """
    リサーチ処理の進捗状態を progress_status.json に即時保存する
    """
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
    except Exception:
        pass
