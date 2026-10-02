"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: view_tab_results.py
   - カテゴリ: view (UI表示・分析)
   - 責務: 最新リサーチ結果または生成されたMarkdownレポートのTreeviewテーブル表示、
     星判定 (☆☆☆/☆☆/☆/-) による絞り込み、CSV/レポートファイル直接起動。

2. 入出力・依存関係:
   - 入力: ユーザーによるフィルター操作、再読み込みイベント
   - 出力: リサーチ結果一覧テーブル、レポートファイル起動
   - 依存先: core_config, service_data_manager, os, subprocess

3. AI改修時の指針・注意点:
   - レポート生成直後に自動リフレッシュ可能となるよう `reload_results` メソッドを公開すること。
================================================================================
"""

import csv
import os
import subprocess
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog
from core_config import FILE_KEYWORDS_CSV, DIR_REPORTS
from service_data_manager import DataManager

class ResultsTab(ttk.Frame):
    """リサーチ結果＆星判定テーブルタブ"""

    def __init__(self, parent):
        super().__init__(parent)
        self.all_items = []
        self._build_ui()
        self.reload_results()

    def _build_ui(self):
        # ツールバー
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="絞り込み:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.var_filter = tk.StringVar(value="全件表示")
        cb_filter = ttk.Combobox(
            toolbar,
            textvariable=self.var_filter,
            values=["全件表示", "☆☆☆ (超穴場・最優先)", "☆☆ 以上 (本命当たり)", "☆ 以上 (手堅いロングテール)", "未判定 / API上限"],
            state="readonly",
            width=24
        )
        cb_filter.pack(side=tk.LEFT, padx=(0, 12))
        cb_filter.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        self.lbl_stats = ttk.Label(toolbar, text="表示件数: 0件", font=("Segoe UI", 9))
        self.lbl_stats.pack(side=tk.LEFT)

        # 右側アクションボタン
        btn_export_csv = ttk.Button(toolbar, text="💾 CSVエクスポート(保存)", command=self._export_csv_as)
        btn_export_csv.pack(side=tk.RIGHT, padx=4)

        btn_open_csv = ttk.Button(toolbar, text="📊 Excel/CSVを開く", command=self._open_csv)
        btn_open_csv.pack(side=tk.RIGHT, padx=4)

        btn_open_report = ttk.Button(toolbar, text="📄 最新MDを開く", command=self._open_latest_report)
        btn_open_report.pack(side=tk.RIGHT, padx=4)

        btn_reload = ttk.Button(toolbar, text="🔄 再読み込み", command=self.reload_results)
        btn_reload.pack(side=tk.RIGHT, padx=4)

        # メインテーブル (Treeview)
        table_frame = ttk.Frame(self, padding=(8, 0, 8, 8))
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("star", "keyword", "type", "volume", "sd", "seed", "updated")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("star", text="判定 (星)")
        self.tree.heading("keyword", text="キーワード")
        self.tree.heading("type", text="展開種別")
        self.tree.heading("volume", text="月間Vol")
        self.tree.heading("sd", text="SEO難易度(SD)")
        self.tree.heading("seed", text="元のシードKW")
        self.tree.heading("updated", text="取得日時")

        self.tree.column("star", width=90, anchor=tk.CENTER)
        self.tree.column("keyword", width=220, anchor=tk.W)
        self.tree.column("type", width=120, anchor=tk.CENTER)
        self.tree.column("volume", width=90, anchor=tk.E)
        self.tree.column("sd", width=90, anchor=tk.E)
        self.tree.column("seed", width=160, anchor=tk.W)
        self.tree.column("updated", width=130, anchor=tk.CENTER)

        # スクロールバー
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # 行選択時イベント
        self.tree.bind("<<TreeviewSelect>>", self._on_item_selected)

        # 下部詳細パネル
        detail_frame = ttk.LabelFrame(self, text=" 選択キーワードの詳細インサイト ", padding=8)
        detail_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.lbl_detail_kw = ttk.Label(detail_frame, text="キーワード: (未選択)", font=("Segoe UI", 10, "bold"))
        self.lbl_detail_kw.pack(anchor=tk.W)

        self.lbl_detail_desc = ttk.Label(
            detail_frame,
            text="テーブル上のキーワードをクリックすると、星評価や検索意図の解説が表示されます。",
            foreground="#475569"
        )
        self.lbl_detail_desc.pack(anchor=tk.W, pady=(2, 0))

    def reload_results(self):
        """データベース＆レポートから最新データを読み込み更新"""
        self.all_items = DataManager.load_keywords_db()
        self._apply_filter()

    def _apply_filter(self):
        """選択されたフィルターに応じてTreeviewを再描画"""
        self.tree.delete(*self.tree.get_children())
        filter_mode = self.var_filter.get()

        displayed_count = 0
        for item in self.all_items:
            star = item.get("star_rating", "-")
            vol = item.get("volume", 0)
            sd = item.get("sd", 0)

            # フィルター判定
            if filter_mode == "☆☆☆ (超穴場・最優先)":
                if "☆☆☆" not in star: continue
            elif filter_mode == "☆☆ 以上 (本命当たり)":
                if "☆☆" not in star and "☆☆☆" not in star: continue
            elif filter_mode == "☆ 以上 (手堅いロングテール)":
                if "☆" not in star: continue
            elif filter_mode == "未判定 / API上限":
                if star != "-" and star != "未判定" and "UNCHECKED" not in star: continue

            vol_str = f"{vol:,}" if vol is not None else "N/A"
            sd_str = str(sd) if sd is not None else "N/A"

            self.tree.insert("", tk.END, values=(
                star,
                item.get("keyword", ""),
                item.get("expansion_type", "MEGA_BATCH"),
                vol_str,
                sd_str,
                item.get("seed_keyword", ""),
                item.get("updated_at", "")
            ))
            displayed_count += 1

        self.lbl_stats.config(text=f"表示件数: {displayed_count} 件 / 総登録: {len(self.all_items)} 件")

    def _on_item_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected[0], "values")
        if not vals:
            return

        star, kw, exp_type, vol, sd, seed, updated = vals
        self.lbl_detail_kw.config(text=f"【{star}】 {kw}  (種別: {exp_type} | 月間Vol: {vol} | SD: {sd})")

        # 簡易インサイト解説
        if "☆☆☆" in star:
            desc = "★ 超穴場キーワード: 月間検索数が多く競合難易度が低いため、個人ブログでも即座に上位狙いが可能な神キーワードです。"
        elif "☆☆" in star:
            desc = "★ 本命当たりキーワード: 需要が大きく、網羅的な記事や実体験を入れることで上位争いに勝てる本命ゾーンです。"
        elif "☆" in star:
            desc = "★ 手堅いロングテール: 競合が少ない手堅いキーワード。ピラー記事への内部リンク集約用に最適です。"
        else:
            desc = "・ 要注意 / 見送り: 難易度が高いか、需要が極めて少ない、またはAPI上限で未取得のキーワードです。"

        self.lbl_detail_desc.config(text=desc)

    def _export_csv_as(self):
        """現在表示されているテーブル内容を名前を付けてCSV保存"""
        items_to_export = []
        for child in self.tree.get_children():
            vals = self.tree.item(child, "values")
            if vals:
                items_to_export.append(vals)

        if not items_to_export:
            messagebox.showwarning("警告", "エクスポート対象のデータがありません。")
            return

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"keywords_export_{now_str}.csv"

        save_path = filedialog.asksaveasfilename(
            title="CSVエクスポート（名前を付けて保存）",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSVファイル (*.csv)", "*.csv"), ("すべてのファイル (*.*)", "*.*")]
        )

        if not save_path:
            return

        try:
            # Excelで日本語が文字化けしないよう utf-8-sig (BOM付きUTF-8) で書き出し
            with open(save_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                # ヘッダー
                writer.writerow(["判定(星)", "キーワード", "展開種別", "月間検索Vol", "SEO難易度(SD)", "登録元シード", "取得日時"])
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

    def _open_csv(self):
        """keywords.csv をOSのデフォルトアプリで開く"""
        if os.path.exists(FILE_KEYWORDS_CSV):
            try:
                os.startfile(FILE_KEYWORDS_CSV)
            except Exception as e:
                messagebox.showerror("エラー", f"CSVを開けませんでした: {e}")
        else:
            messagebox.showinfo("案内", "まだ keywords.csv が生成されていません。リサーチを実行してください。")

    def _open_latest_report(self):
        """最新のMarkdownレポートを開く"""
        latest = DataManager.get_latest_report()
        if latest and os.path.exists(latest["file_path"]):
            try:
                os.startfile(latest["file_path"])
            except Exception as e:
                messagebox.showerror("エラー", f"レポートを開けませんでした: {e}")
        else:
            messagebox.showinfo("案内", "まだレポートファイルが存在しません。リサーチを実行してください。")
