"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: core_config.py
   - カテゴリ: core (基盤・設定)
   - 責務: wide-オンデマンド全体のパス解決、wideエンジン側スクリプト・データストアの
     パス集中管理、UIウィンドウ設定、配色テーマの定義。

2. 入出力・依存関係:
   - 入力: なし (静的定数定義)
   - 出力: 各種パス定数、UI設定定数 (他全モジュールから参照される)
   - 外部依存: os モジュールのみ

3. AI改修時の指針・注意点:
   - wide側のディレクトリ構造やスクリプト名が変更された場合は、このファイルのみを保守すること。
================================================================================
"""

import os

# --- パス解決 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = CURRENT_DIR

# wide リサーチエンジン側のベースディレクトリ
BASE_DIR = os.path.abspath(os.path.join(APP_ROOT, "..", "wide"))

# wide側のスクリプトパス
SCRIPT_PIPELINE = os.path.join(BASE_DIR, "workflow_keyword_pipeline.ps1")
SCRIPT_SYNTAX = os.path.join(BASE_DIR, "syntax_keyword_analyzer.ps1")
SCRIPT_EXPANSION = os.path.join(BASE_DIR, "expansion_keyword_builder.ps1")
SCRIPT_VALIDATOR = os.path.join(BASE_DIR, "validator_keyword_threshold.ps1")
SCRIPT_ENGINE = os.path.join(BASE_DIR, "engine_keyword_search.ps1")
SCRIPT_API = os.path.join(BASE_DIR, "api_ubersuggest_client.ps1")
SCRIPT_REPORTER = os.path.join(BASE_DIR, "reporter_markdown_output.ps1")
SCRIPT_DB_MANAGER = os.path.join(BASE_DIR, "db_keyword_manager.ps1")

# wide側のデータストアパス
FILE_RAW_ARCHIVE = os.path.join(BASE_DIR, "raw_api_archive.json")
FILE_KEYWORDS_DB = os.path.join(BASE_DIR, "keywords_db.json")
FILE_KEYWORDS_CSV = os.path.join(BASE_DIR, "keywords.csv")
FILE_CACHE = os.path.join(BASE_DIR, "verified_volume_cache.json")
DIR_REPORTS = os.path.join(BASE_DIR, "reports")

# wide-オンデマンド側のログディレクトリ
DIR_LOGS = os.path.join(APP_ROOT, "logs")
if not os.path.exists(DIR_LOGS):
    os.makedirs(DIR_LOGS, exist_ok=True)

# --- 業務ルール定数 ---
MIN_THRESHOLD_DEFAULT = 25  # Rule 04: 25件未満APIコール完全抑止

# --- ウィンドウ・UI共通設定 ---
APP_TITLE = "wide-オンデマンド | キーワード縦横展開＆Ubersuggest当たり判定コントローラー"
WINDOW_SIZE = "1100x820"
WINDOW_MIN_SIZE = (960, 680)
DEFAULT_THEME = "vista"

# --- UIカラーパレット (Tailwind / モダンカラースタイル) ---
COLOR_IDLE_BG = "#e0f2fe"       # 待機中バッジ背景 (薄水色)
COLOR_IDLE_FG = "#0369a1"       # 待機中バッジ文字 (濃い青)
COLOR_RUNNING_BG = "#dcfce7"    # 稼働中バッジ背景 (薄緑)
COLOR_RUNNING_FG = "#15803d"    # 稼働中バッジ文字 (濃い緑)

COLOR_ALERT_BG = "#fee2e2"      # 警告・不足バッジ背景 (薄赤)
COLOR_ALERT_FG = "#b91c1c"      # 警告・不足バッジ文字 (濃い赤)
COLOR_SUCCESS_BG = "#ecfdf5"    # 達成バッジ背景 (エメラルド)
COLOR_SUCCESS_FG = "#047857"    # 達成バッジ文字 (濃いエメラルド)

COLOR_BTN_PRIMARY = "#2563eb"   # メインアクション青
COLOR_BTN_SUCCESS = "#16a34a"   # 実行・完了緑
COLOR_BTN_DANGER = "#dc2626"    # 中断・停止赤
COLOR_BTN_SECONDARY = "#475569" # サブ灰色

COLOR_CONSOLE_BG = "#0f172a"    # コンソール背景 (ダークスレート)
COLOR_CONSOLE_FG = "#f8fafc"    # コンソール文字 (白)
COLOR_SUB_BG = "#1e293b"        # サブコンソール背景
COLOR_SUB_FG = "#e2e8f0"        # サブコンソール文字
