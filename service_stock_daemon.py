# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: service_stock_daemon.py
■ カテゴリ: Background Service / 星付きキーワードDB自律監視＆500件メガバッチ自動発動デーモン
■ 責務・役割（Single Responsibility）:
  - keywords_db.json を定期監視（常駐スレッド）。
  - ★星1つ以上の重複排除済みキーワードで、Vol未取得（volume is None）の件数を集計。
  - 閾値（500件以上）に到達した瞬間、自動的にUbersuggest 1-Shotメガバッチジョブ（start_research_job）を発行。
  - 実行中フラグにより二重実行を防止。
==============================================================================
"""

import time
import threading
from typing import Dict, Any

from service_state_manager import get_starred_stock_summary
from service_research_runner import start_research_job

STOCK_TRIGGER_THRESHOLD = 500
CHECK_INTERVAL_SECONDS = 15

_daemon_running = False
_is_triggering = False

def check_and_trigger_auto_batch() -> Dict[str, Any]:
    """
    DBの星付き未取得件数を点検し、500件以上あれば自動でメガバッチを発動
    """
    global _is_triggering
    if _is_triggering:
        return {"status": "ALREADY_TRIGGERING"}

    summary = get_starred_stock_summary()
    unmeasured = summary.get("unmeasured_count", 0)

    if unmeasured >= STOCK_TRIGGER_THRESHOLD:
        _is_triggering = True
        try:
            print(f"[StockDaemon] 🌟 星付き未取得キーワードが {unmeasured} 件（閾値 {STOCK_TRIGGER_THRESHOLD} 件）に到達！自動メガバッチ（1API）を発動します...")
            payload = {
                "seed": "AUTO_STOCK_BATCH",
                "axis1": [],
                "axis2": [],
                "mode": "ubersuggest"
            }
            res = start_research_job(payload)
            print(f"[StockDaemon] 🚀 メガバッチジョブ起動完了 (PID: {res.get('pid')}, 対象件数: {res.get('total_count')})")
            return {"status": "TRIGGERED", "job": res}
        finally:
            # ジョブ起動後に少しクールダウン
            time.sleep(10)
            _is_triggering = False

    return {"status": "WAITING", "unmeasured_count": unmeasured, "threshold": STOCK_TRIGGER_THRESHOLD}

def _daemon_loop():
    print(f"[StockDaemon] 蓄積DB自動監視スレッド稼働中 (閾値: {STOCK_TRIGGER_THRESHOLD} 件, 監視間隔: {CHECK_INTERVAL_SECONDS} 秒)")
    while _daemon_running:
        try:
            check_and_trigger_auto_batch()
        except Exception as e:
            print(f"[StockDaemon] 監視エラー: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)

def start_stock_monitor_daemon():
    """バックグラウンド監視スレッドを起動"""
    global _daemon_running
    if _daemon_running:
        return
    _daemon_running = True
    t = threading.Thread(target=_daemon_loop, daemon=True, name="StockMonitorDaemon")
    t.start()
