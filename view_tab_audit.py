"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: view_tab_audit.py
   - カテゴリ: view (UI表示・API監査)
   - 責務: Tier 1 生ログ監査 (raw_api_archive.json) の可視化、APIコール消費履歴、
     枯渇・429/403エラー検知ログの閲覧、および生JSONインスペクター。

2. 入出力・依存関係:
   - 入力: ユーザーによるログ選択
   - 出力: API監査一覧テーブル、生JSONペイロードビューア
   - 依存先: core_config, service_data_manager, json

3. AI改修時の指針・注意点:
   - 1リクエストで何件取得できたかを明示し、単発ループ消費が一切起きていないことを
     ユーザーが視覚的に監査・確信できるようにすること。
================================================================================
"""

import json
import tkinter as tk
from tkinter import ttk, scrolledtext
from core_config import COLOR_CONSOLE_BG, COLOR_CONSOLE_FG
from service_data_manager import DataManager

class AuditTab(ttk.Frame):
    """Ubersuggest API監査＆生ログ確認タブ"""

    def __init__(self, parent):
        super().__init__(parent)
        self.archive_items = []
        self._build_ui()
        self.reload_logs()

    def _build_ui(self):
        # 左右分割 (左: APIコール履歴一覧、右: 生JSONインスペクタ)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # === 左ペイン: APIコール履歴 ===
        left_frame = ttk.Frame(paned, padding=6)
        paned.add(left_frame, weight=1)

        head_row = ttk.Frame(left_frame)
        head_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(head_row, text="APIリクエスト監査証跡 (1-Shot Mega-Batch Evidence)", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        btn_reload = ttk.Button(head_row, text="🔄 更新", command=self.reload_logs)
        btn_reload.pack(side=tk.RIGHT)

        # 履歴テーブル
        table_frame = ttk.Frame(left_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("timestamp", "endpoint", "terms_count", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("timestamp", text="実行日時")
        self.tree.heading("endpoint", text="エンドポイント")
        self.tree.heading("terms_count", text="要求語句数")
        self.tree.heading("status", text="ステータス")

        self.tree.column("timestamp", width=140, anchor=tk.CENTER)
        self.tree.column("endpoint", width=120, anchor=tk.CENTER)
        self.tree.column("terms_count", width=90, anchor=tk.E)
        self.tree.column("status", width=90, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_log_selected)

        # === 右ペイン: 生JSONプレビュー ===
        right_frame = ttk.Frame(paned, padding=6)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="未加工生JSONエビデンス (Raw Payload)", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 6))

        self.txt_json = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=COLOR_CONSOLE_BG,
            fg=COLOR_CONSOLE_FG,
            insertbackground="white"
        )
        self.txt_json.pack(fill=tk.BOTH, expand=True)

    def reload_logs(self):
        """生ログ再読込"""
        self.tree.delete(*self.tree.get_children())
        self.archive_items = DataManager.load_raw_archive()

        # 最新順に並び替え
        for idx, item in enumerate(reversed(self.archive_items)):
            ts = item.get("timestamp", "-")
            ep = item.get("endpoint", "match_keywords")
            params = item.get("params", {})
            kw_list = params.get("keywords", [])
            terms_cnt = len(kw_list) if isinstance(kw_list, list) else 1

            status = "SUCCESS"
            if item.get("error"):
                status = "ERROR"

            self.tree.insert("", tk.END, iid=str(idx), values=(
                ts,
                ep,
                f"{terms_cnt} 語",
                status
            ))

        if not self.archive_items:
            self.txt_json.delete("1.0", tk.END)
            self.txt_json.insert(tk.END, "※ まだ APIコール監査ログ (raw_api_archive.json) は記録されていません。\n1-Shotメガバッチを実行するとここに未加工生JSONが自動保存されます。")

    def _on_log_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        # 逆順で表示しているので対応するインデックスを取得
        orig_idx = len(self.archive_items) - 1 - idx
        if 0 <= orig_idx < len(self.archive_items):
            raw_item = self.archive_items[orig_idx]
            formatted_json = json.dumps(raw_item, ensure_ascii=False, indent=2)
            self.txt_json.delete("1.0", tk.END)
            self.txt_json.insert(tk.END, formatted_json)
