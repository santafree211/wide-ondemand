"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: core_logger.py
   - カテゴリ: core (基盤・ロガー)
   - 責務: GUI操作やバックエンド実行プロセスの動作ログをファイル (logs/) および
     標準出力へ一元出力するロガーの提供。

2. 入出力・依存関係:
   - 入力: ログメッセージ文字列、ログレベル (INFO, WARNING, ERROR, DEBUG)
   - 出力: logs/wide_ondemand_YYYYMMDD.log ファイル追記、標準出力
   - 外部依存: logging, datetime, core_config

3. AI改修時の指針・注意点:
   - GUIのコンソールウィジェットに文字を流す際は、このロガー経由または
     service_runner のコールバックを利用すること。
================================================================================
"""

import os
import sys
import logging
from datetime import datetime
from core_config import DIR_LOGS

_logger = None

def get_logger():
    """シングルトンロガーインスタンスを返す"""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger("wide_ondemand")
    _logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # コンソール出力ハンドラ
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    _logger.addHandler(ch)

    # 日付別ファイル出力ハンドラ
    today_str = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(DIR_LOGS, f"wide_ondemand_{today_str}.log")
    try:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        _logger.addHandler(fh)
    except Exception as e:
        print(f"Warning: Failed to setup file logger: {e}", file=sys.stderr)

    return _logger

def log_info(msg: str):
    get_logger().info(msg)

def log_warn(msg: str):
    get_logger().warning(msg)

def log_error(msg: str):
    get_logger().error(msg)

def log_debug(msg: str):
    get_logger().debug(msg)
