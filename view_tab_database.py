"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: view_tab_database.py
   - カテゴリ: view (UI表示・DB管理)
   - 責務: Tier 1 マスターDB (keywords_db.json) および Tier 2 キャッシュ
     (verified_volume_cache.json) の統計サマリー表示、全文キーワード検索、
     およびキャッシュ資産の可視化。

2. 入出力・依存関係:
   - 入力: ユーザーによる検索入力、更新ボタン
   - 出力: サマリーカード (総数/キャッシュ数/星別)、キーワード検索一覧
   - 依存先: core_config, service_data_manager

3. AI改修時の指針・注意点:
   - 大量データ時もUIがフリーズしないよう、部分一致検索は効率的に行うこと。
================================================================================
"""

import csv
import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog
from service_data_manager import DataManager

class DatabaseTab(ttk.Frame):
    """多層キャッシュ＆マスターDB閲覧タブ"""

    def __init__(self, parent):
        super().__init__(parent)
        self.db_items = []
        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        # 1. 上部サマリーカードエリア
        summary_group = ttk.LabelFrame(self, text=" 多層キャッシュ＆蓄積資産サマリー (Rule 05) ", padding=8)
        summary_group.pack(fill=tk.X, padx=8, pady=8)

        card_row = ttk.Frame(summary_group)
        card_row.pack(fill=tk.X)

        self.card_total = self._create_card(card_row, "マスターDB総数", "0", "#1e3a8a", "#dbeafe")
        self.card_cache = self._create_card(card_row, "Tier 2 高速キャッシュ", "0", "#065f46", "#d1fae5")
        self.card_star3 = self._create_card(card_row, "☆☆☆ 超穴場", "0", "#92400e", "#fef3c7")
        self.card_star2 = self._create_card(card_row, "☆☆ 本命当たり", "0", "#166534", "#dcfce7")
        self.card_star1 = self._create_card(card_row, "☆ 手堅いロング", "0", "#374151", "#f3f4f6")

        # 2. 検索・ツールバー
        toolbar = ttk.Frame(self, padding=(8, 0, 8, 4))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="キーワード検索:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.var_search = tk.StringVar()
        entry_search = ttk.Entry(toolbar, textvariable=self.var_search, width=28)
        entry_search.pack(side=tk.LEFT, padx=(0, 8))
        entry_search.bind("<KeyRelease>", lambda e: self._on_search_changed())

        btn_clear = ttk.Button(toolbar, text="クリア", command=self._clear_search)
        btn_clear.pack(side=tk.LEFT, padx=(0, 12))

        self.lbl_result_count = ttk.Label(toolbar, text="一致: 0件")
        self.lbl_result_count.pack(side=tk.LEFT)

        btn_export = ttk.Button(toolbar, text="💾 絞り込み結果をCSV保存", command=self._export_csv_as)
        btn_export.pack(side=tk.RIGHT, padx=4)

        btn_reload = ttk.Button(toolbar, text="🔄 最新状態に更新", command=self.reload_data)
        btn_reload.pack(side=tk.RIGHT, padx=4)

        # 3. データベース一覧テーブル
        table_frame = ttk.Frame(self, padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("star", "keyword", "volume", "sd", "seed", "expansion_type", "updated_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("star", text="星評価")
        self.tree.heading("keyword", text="キーワード")
        self.tree.heading("volume", text="月間検索Vol")
        self.tree.heading("sd", text="難易度(SD)")
        self.tree.heading("seed", text="登録元シード")
        self.tree.heading("expansion_type", text="展開種別")
        self.tree.heading("updated_at", text="最終照合日時")

        self.tree.column("star", width=80, anchor=tk.CENTER)
        self.tree.column("keyword", width=220, anchor=tk.W)
        self.tree.column("volume", width=100, anchor=tk.E)
        self.tree.column("sd", width=90, anchor=tk.E)
        self.tree.column("seed", width=180, anchor=tk.W)
        self.tree.column("expansion_type", width=120, anchor=tk.CENTER)
        self.tree.column("updated_at", width=140, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def _create_card(self, parent, title: str, init_val: str, fg_color: str, bg_color: str):
        """サマリーカードを生成"""
        f = tk.Frame(parent, bg=bg_color, padx=12, pady=6, relief=tk.GROOVE, bd=1)
        f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        lbl_t = tk.Label(f, text=title, font=("Segoe UI", 8), bg=bg_color, fg=fg_color)
        lbl_t.pack(anchor=tk.W)

        lbl_v = tk.Label(f, text=init_val, font=("Segoe UI", 14, "bold"), bg=bg_color, fg=fg_color)
        lbl_v.pack(anchor=tk.W)
        return lbl_v

    def reload_data(self):
        """データ再読込＆カード集計更新"""
        self.db_items = DataManager.load_keywords_db()
        stats = DataManager.get_summary_stats()

        self.card_total.config(text=f"{stats['total_db_keywords']:,} 件")
        self.card_cache.config(text=f"{stats['total_cached_keywords']:,} 件")

        star_c = stats["star_counts"]
        self.card_star3.config(text=f"{star_c['3_star']} 件")
        self.card_star2.config(text=f"{star_c['2_star']} 件")
        self.card_star1.config(text=f"{star_c['1_star']} 件")

        self._filter_table()

    def _on_search_changed(self):
        self._filter_table()

    def _clear_search(self):
        self.var_search.set("")
        self._filter_table()

    def _filter_table(self):
        self.tree.delete(*self.tree.get_children())
        query = self.var_search.get().strip().lower()

        count = 0
        for item in self.db_items:
            kw = item.get("keyword", "")
            seed = item.get("seed_keyword", "")

            if query and (query not in kw.lower() and query not in seed.lower()):
                continue

            vol = item.get("volume", 0)
            sd = item.get("sd", 0)

            self.tree.insert("", tk.END, values=(
                item.get("star_rating", "-"),
                kw,
                f"{vol:,}" if vol is not None else "N/A",
                str(sd) if sd is not None else "N/A",
                seed,
                item.get("expansion_type", "MEGA_BATCH"),
                item.get("updated_at", "")
            ))
            count += 1

        self.lbl_result_count.config(text=f"一致: {count} 件 / 総数: {len(self.db_items)} 件")

    def _export_csv_as(self):
        """検索・絞り込み中の一覧データを名前を付けてCSV保存"""
        items_to_export = []
        for child in self.tree.get_children():
            vals = self.tree.item(child, "values")
            if vals:
                items_to_export.append(vals)

        if not items_to_export:
            messagebox.showwarning("警告", "エクスポート対象のデータがありません。")
            return

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        q = self.var_search.get().strip()
        suffix = f"_{q}" if q else ""
        default_name = f"database_export{suffix}_{now_str}.csv"

        save_path = filedialog.asksaveasfilename(
            title="データベース検索結果のエクスポート",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSVファイル (*.csv)", "*.csv"), ("すべてのファイル (*.*)", "*.*")]
        )

        if not save_path:
            return

        try:
            with open(save_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["星評価", "キーワード", "月間検索Vol", "難易度(SD)", "登録元シード", "展開種別", "最終照合日時"])
                for row in items_to_export:
                    writer.writerow(row)

            res = messagebox.askyesno(
                "エクスポート完了",
                f"CSVファイルを保存しました:\n{save_path}\n\n今すぐこのファイルを開きますか？"
            )
            if res:
                os.startfile(save_path)
        except Exception as e:
            messagebox.showerror("エラー", f"CSV保存に失敗しました: {e}")
