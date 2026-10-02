"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: view_main_window.py
   - カテゴリ: view (UI表示・統合エントリポイント)
   - 責務: wide-オンデマンド メインウィンドウ (Tkinter Tk) の生成、ライフサイクル管理、
     上部ヘッダーバッジ (稼働中/待機中) の描画、全4タブのNotebook統合、
     および直接起動時のエントリポイント。

2. 入出力・依存関係:
   - 入力: 起動イベント、各タブからの稼働ステータス変更・リサーチ完了イベント
   - 出力: アプリケーション全体のGUIウィンドウ
   - 依存先: core_config, view_tab_expand, view_tab_results, view_tab_database, view_tab_audit

3. AI改修時の指針・注意点:
   - タブ間のデータ連携 (例: リサーチ完了時に結果タブとDBタブを自動リフレッシュ) は
     このウィンドウクラスをメディエーターとして調停すること。
================================================================================
"""

import os
import sys
import glob
import tkinter as tk
from tkinter import ttk, messagebox
from core_config import (
    APP_TITLE,
    WINDOW_SIZE,
    WINDOW_MIN_SIZE,
    DEFAULT_THEME,
    COLOR_IDLE_BG,
    COLOR_IDLE_FG,
    COLOR_RUNNING_BG,
    COLOR_RUNNING_FG,
    FILE_KEYWORDS_DB,
    DIR_REPORTS,
)
from view_tab_expand import ExpandTab
from view_tab_results import ResultsTab
from view_tab_database import DatabaseTab
from view_tab_audit import AuditTab

class MainWindow(tk.Tk):
    """wide-オンデマンド メインウィンドウクラス"""

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(*WINDOW_MIN_SIZE)

        self._last_db_mtime = 0.0
        self._last_report_mtime = 0.0
        self._is_watcher_running = True

        self.style = ttk.Style(self)
        try:
            self.style.theme_use(DEFAULT_THEME)
        except Exception:
            pass

        self._build_header()
        self._build_tabs()
        self._init_file_watcher()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_header(self):
        """上部ヘッダーエリア（タイトル＆ステータスバッジ）"""
        header_frame = ttk.Frame(self, padding=(12, 10, 12, 6))
        header_frame.pack(fill=tk.X)

        # アプリタイトル
        title_box = ttk.Frame(header_frame)
        title_box.pack(side=tk.LEFT)

        lbl_app_name = ttk.Label(
            title_box,
            text="wide-オンデマンド",
            font=("Segoe UI", 15, "bold"),
            foreground="#0f172a"
        )
        lbl_app_name.pack(side=tk.LEFT)

        lbl_sub = ttk.Label(
            title_box,
            text=" | キーワード縦横展開 & 1-Shotメガバッチ当たり判定システム",
            font=("Segoe UI", 10),
            foreground="#64748b"
        )
        lbl_sub.pack(side=tk.LEFT, padx=(4, 0))

        # 右側: 自動同期バッジ & 稼働ステータスバッジ
        right_box = ttk.Frame(header_frame)
        right_box.pack(side=tk.RIGHT)

        self.lbl_sync_badge = tk.Label(
            right_box,
            text="🔄 自動同期: ON",
            font=("Segoe UI", 9, "bold"),
            bg="#f0fdf4",
            fg="#16a34a",
            padx=8,
            pady=4,
            relief=tk.FLAT
        )
        self.lbl_sync_badge.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_status_badge = tk.Label(
            right_box,
            text="● 待機中 (IDLE)",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_IDLE_BG,
            fg=COLOR_IDLE_FG,
            padx=12,
            pady=4,
            relief=tk.FLAT
        )
        self.lbl_status_badge.pack(side=tk.LEFT)

        # 区切り線
        sep = ttk.Separator(self, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, padx=8, pady=(4, 0))

    def _init_file_watcher(self):
        """wideデータストアの変更を監視し、外部更新時に自動リフレッシュ"""
        if os.path.exists(FILE_KEYWORDS_DB):
            self._last_db_mtime = os.path.getmtime(FILE_KEYWORDS_DB)

        self._last_report_mtime = self._get_latest_report_mtime()
        self.after(2500, self._check_external_updates)

    def _get_latest_report_mtime(self) -> float:
        if not os.path.exists(DIR_REPORTS):
            return 0.0
        md_files = glob.glob(os.path.join(DIR_REPORTS, "*.md"))
        if not md_files:
            return 0.0
        return max(os.path.getmtime(p) for p in md_files)

    def _check_external_updates(self):
        """定期ポーリングによるデータ自動同期チェック"""
        if not self._is_watcher_running:
            return

        need_refresh = False

        # 1. keywords_db.json の更新チェック
        if os.path.exists(FILE_KEYWORDS_DB):
            curr_db_mtime = os.path.getmtime(FILE_KEYWORDS_DB)
            if curr_db_mtime > self._last_db_mtime:
                self._last_db_mtime = curr_db_mtime
                need_refresh = True

        # 2. reports/ 配下の更新チェック
        curr_rep_mtime = self._get_latest_report_mtime()
        if curr_rep_mtime > self._last_report_mtime:
            self._last_report_mtime = curr_rep_mtime
            need_refresh = True

        # 外部で更新があった場合、UIを実行中でなければ自動リフレッシュ
        if need_refresh and not self.tab_expand.runner.is_running:
            self.lbl_sync_badge.config(text="⚡ 同期反映中...", bg="#fef3c7", fg="#d97706")
            try:
                self.tab_results.reload_results()
                self.tab_database.reload_data()
                self.tab_audit.reload_logs()
            except Exception:
                pass
            self.after(1000, lambda: self.lbl_sync_badge.config(text="🔄 自動同期: ON", bg="#f0fdf4", fg="#16a34a"))

        # 次回チェック (2.5秒間隔)
        self.after(2500, self._check_external_updates)

    def _build_tabs(self):
        """タブ統合（Notebook）"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # タブ1: 展開＆メガバッチ実行
        self.tab_expand = ExpandTab(
            self.notebook,
            on_status_change=self.set_running_state,
            on_research_finished=self._on_research_finished
        )
        self.notebook.add(self.tab_expand, text=" 🚀 キーワード展開＆メガバッチ実行 ")

        # タブ2: リサーチ結果＆星判定テーブル
        self.tab_results = ResultsTab(self.notebook)
        self.notebook.add(self.tab_results, text=" 📊 リサーチ結果＆星判定 ")

        # タブ3: 多層キャッシュ＆DB検索
        self.tab_database = DatabaseTab(self.notebook)
        self.notebook.add(self.tab_database, text=" 🗄 多層キャッシュ＆DB検索 ")

        # タブ4: API監査＆生ログ証跡
        self.tab_audit = AuditTab(self.notebook)
        self.notebook.add(self.tab_audit, text=" 🛡 API監査＆生ログ証跡 ")

    def set_running_state(self, is_running: bool):
        """全体の稼働状態バッジを更新"""
        if is_running:
            self.lbl_status_badge.config(
                text="⚡ 実行中 (RUNNING...)",
                bg=COLOR_RUNNING_BG,
                fg=COLOR_RUNNING_FG
            )
        else:
            self.lbl_status_badge.config(
                text="● 待機中 (IDLE)",
                bg=COLOR_IDLE_BG,
                fg=COLOR_IDLE_FG
            )

    def _on_research_finished(self):
        """リサーチ完了時の自動リフレッシュ＆タブ誘導"""
        self.tab_results.reload_results()
        self.tab_database.reload_data()
        self.tab_audit.reload_logs()

        # 自動的に結果タブに切り替えるか案内
        self.notebook.select(self.tab_results)
        messagebox.showinfo(
            "リサーチ完了",
            "1-Shotメガバッチリサーチが完了しました！\nリサーチ結果テーブルを表示します。"
        )

    def _on_closing(self):
        """ウィンドウを閉じる際の終了処理"""
        self._is_watcher_running = False
        if self.tab_expand.runner.is_running:
            if not messagebox.askyesno("終了確認", "現在リサーチパイプラインが実行中です。強制終了して閉じますか？"):
                return
            self.tab_expand.runner.stop()
        self.destroy()

def main():
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
