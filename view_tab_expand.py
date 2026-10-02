"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: view_tab_expand.py
   - カテゴリ: view (UI表示・操作)
   - 責務: シードキーワード構文解析、前後2大固定軸 (A固定/B固定) の展開・編集、
     Rule 04 (25件閾値メーター) のリアルタイム監視、1-Shot メガバッチ実行、
     およびリアルタイムコンソールログ描画。

2. 入出力・依存関係:
   - 入力: ユーザーによるシード入力、軸1/軸2展開語句、追加入力
   - 出力: パイプライン実行トリガー、リアルタイムログ、結果タブ更新イベント
   - 依存先: core_config, core_logger, service_runner

3. AI改修時の指針・注意点:
   - Rule 04 の「25件未満APIコール完全抑止原則」をUI側で物理的に強制すること。
     25件未満の場合は実行ボタンを抑止または警告ダイアログで保護する。
================================================================================
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Callable, Optional
from core_config import (
    APP_ROOT,
    SCRIPT_PIPELINE,
    MIN_THRESHOLD_DEFAULT,
    COLOR_ALERT_BG,
    COLOR_ALERT_FG,
    COLOR_SUCCESS_BG,
    COLOR_SUCCESS_FG,
    COLOR_BTN_PRIMARY,
    COLOR_BTN_SUCCESS,
    COLOR_BTN_DANGER,
    COLOR_CONSOLE_BG,
    COLOR_CONSOLE_FG,
)
from core_logger import log_info, log_warn
from service_runner import ProcessRunner

class ExpandTab(ttk.Frame):
    """キーワード展開＆メガバッチ実行タブ"""

    def __init__(self, parent, on_status_change: Optional[Callable[[bool], None]] = None, on_research_finished: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_status_change = on_status_change
        self.on_research_finished = on_research_finished
        self.runner = ProcessRunner()

        self._build_ui()
        self._update_threshold_meter()

    def _build_ui(self):
        # 左右分割 (左: 設定・展開入力、右: コンソールログ)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # === 左ペイン: 入力・展開フォーム ===
        left_frame = ttk.Frame(paned, padding=6)
        paned.add(left_frame, weight=1)

        # 1. シードキーワード入力
        seed_group = ttk.LabelFrame(left_frame, text=" 1. シードキーワード入力 (例: [A] [B]) ", padding=8)
        seed_group.pack(fill=tk.X, pady=(0, 6))

        seed_row = ttk.Frame(seed_group)
        seed_row.pack(fill=tk.X)

        self.var_seed = tk.StringVar(value="おもちゃ サブスク")
        self.entry_seed = ttk.Entry(seed_row, textvariable=self.var_seed, font=("Segoe UI", 10, "bold"))
        self.entry_seed.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.entry_seed.bind("<KeyRelease>", lambda e: self._on_seed_changed())

        btn_parse = ttk.Button(seed_row, text="構文解析 (分解＆候補生成)", command=self._parse_syntax)
        btn_parse.pack(side=tk.RIGHT)

        # 構文解析スロット表示バッジ
        slot_row = ttk.Frame(seed_group)
        slot_row.pack(fill=tk.X, pady=(6, 0))
        self.lbl_slot_a = ttk.Label(slot_row, text="[A] スロット: おもちゃ", foreground="#1e40af", font=("Segoe UI", 9, "bold"))
        self.lbl_slot_a.pack(side=tk.LEFT, padx=(0, 16))
        self.lbl_slot_b = ttk.Label(slot_row, text="[B] スロット: サブスク", foreground="#991b1b", font=("Segoe UI", 9, "bold"))
        self.lbl_slot_b.pack(side=tk.LEFT)

        # 2. 前後2大固定軸 展開入力
        axes_group = ttk.LabelFrame(left_frame, text=" 2. 前後2大固定軸 展開 (完全対称性の原則) ", padding=8)
        axes_group.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # 軸1 & 軸2 2列レイアウト
        axes_row = ttk.Frame(axes_group)
        axes_row.pack(fill=tk.BOTH, expand=True)

        # 軸1 (前固定: [A] 〇〇)
        axis1_col = ttk.Frame(axes_row)
        axis1_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        self.lbl_axis1_title = ttk.Label(axis1_col, text="軸①: [A] 〇〇 (前置固定)", font=("Segoe UI", 9, "bold"))
        self.lbl_axis1_title.pack(anchor=tk.W)
        self.txt_axis1 = tk.Text(axis1_col, height=9, font=("Consolas", 9), wrap=tk.NONE)
        self.txt_axis1.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.txt_axis1.bind("<KeyRelease>", lambda e: self._update_threshold_meter())

        # 軸2 (後固定: 〇〇 [B])
        axis2_col = ttk.Frame(axes_row)
        axis2_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        self.lbl_axis2_title = ttk.Label(axis2_col, text="軸②: 〇〇 [B] (後置固定)", font=("Segoe UI", 9, "bold"))
        self.lbl_axis2_title.pack(anchor=tk.W)
        self.txt_axis2 = tk.Text(axis2_col, height=9, font=("Consolas", 9), wrap=tk.NONE)
        self.txt_axis2.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.txt_axis2.bind("<KeyRelease>", lambda e: self._update_threshold_meter())

        # サンプル語句の初期投入 (おもちゃ サブスク または デフォルト)
        self.txt_axis1.insert("1.0", "知育\nレンタル\n買取\n収納\n人気\n年齢別\n片付け\n手作り\n消毒\nプレゼント\n赤ちゃん")
        self.txt_axis2.insert("1.0", "絵本\n洋服\n家具\n知育玩具\n花\nコーヒー\nお菓子\n家電\n音楽\nゲーム\n服")

        # 補助ボタンバー
        aux_row = ttk.Frame(axes_group)
        aux_row.pack(fill=tk.X, pady=(6, 0))
        btn_auto = ttk.Button(aux_row, text="💡 シードに沿った候補を自動生成", command=self._auto_populate_expansion)
        btn_auto.pack(side=tk.LEFT)
        btn_clear = ttk.Button(aux_row, text="入力クリア", command=self._clear_axes)
        btn_clear.pack(side=tk.LEFT, padx=6)

        # 3. 25件閾値メーター (Rule 04 防護)
        meter_group = ttk.LabelFrame(left_frame, text=" 3. 25件バッチ閾値防護 (Rule 04: Minimum Threshold) ", padding=8)
        meter_group.pack(fill=tk.X, pady=(0, 6))

        # バッジ表示
        badge_row = ttk.Frame(meter_group)
        badge_row.pack(fill=tk.X)

        self.lbl_count_badge = tk.Label(
            badge_row,
            text="合計: 0 / 25件",
            font=("Segoe UI", 10, "bold"),
            padx=10, pady=4,
            bg=COLOR_ALERT_BG, fg=COLOR_ALERT_FG
        )
        self.lbl_count_badge.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_status_msg = ttk.Label(
            badge_row,
            text="判定中...",
            font=("Segoe UI", 9)
        )
        self.lbl_status_msg.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # プログレスバー
        self.progress_bar = ttk.Progressbar(meter_group, maximum=25, value=0)
        self.progress_bar.pack(fill=tk.X, pady=(6, 0))

        # 4. アクションボタン
        act_row = ttk.Frame(left_frame)
        act_row.pack(fill=tk.X, pady=(4, 0))

        self.btn_run = tk.Button(
            act_row,
            text="🚀 1-Shot メガバッチ実行 (API: 1回)",
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_BTN_SUCCESS,
            fg="white",
            activebackground="#15803d",
            activeforeground="white",
            relief=tk.RAISED,
            padx=12, pady=6,
            command=self._on_run_clicked
        )
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_stop = tk.Button(
            act_row,
            text="■ 中断 (Kill)",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_BTN_DANGER,
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            state=tk.DISABLED,
            padx=10, pady=6,
            command=self._on_stop_clicked
        )
        self.btn_stop.pack(side=tk.RIGHT)

        # === 右ペイン: リアルタイムコンソールログ ===
        right_frame = ttk.Frame(paned, padding=6)
        paned.add(right_frame, weight=1)

        log_head = ttk.Frame(right_frame)
        log_head.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(log_head, text="リアルタイム実行ログ (Pure Batch Pipeline Output)", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        btn_log_clear = ttk.Button(log_head, text="ログ消去", command=self._clear_console)
        btn_log_clear.pack(side=tk.RIGHT)

        self.console = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=COLOR_CONSOLE_BG,
            fg=COLOR_CONSOLE_FG,
            insertbackground="white"
        )
        self.console.pack(fill=tk.BOTH, expand=True)

        self._log_to_console("=== wide-オンデマンド デスクトップコントローラー 準備完了 ===\n")
        self._log_to_console("Rule 04 鉄則: キーワードが合計25件集まるまでAPIコールは一切実行されません。\n")

    def _on_seed_changed(self):
        """シード入力変更時の自動スロット更新"""
        self._parse_syntax()
        self._update_threshold_meter()

    def _parse_syntax(self):
        """シードをスロット [A] と [B] に分割し、シードに応じた候補を自動生成"""
        seed = self.var_seed.get().strip()
        parts = seed.split()
        if len(parts) >= 2:
            slot_a = parts[0]
            slot_b = " ".join(parts[1:])
        elif len(parts) == 1:
            slot_a = parts[0]
            slot_b = ""
        else:
            slot_a = ""
            slot_b = ""

        self.lbl_slot_a.config(text=f"[A] スロット: {slot_a}")
        self.lbl_slot_b.config(text=f"[B] スロット: {slot_b}")
        self.lbl_axis1_title.config(text=f"軸①: [{slot_a}] 〇〇 (前置固定)")
        self.lbl_axis2_title.config(text=f"軸②: 〇〇 [{slot_b}] (後置固定)")
        self._auto_populate_expansion()

    def _auto_populate_expansion(self):
        """シードキーワードの文脈に沿った展開候補を自動提案・挿入"""
        seed = self.var_seed.get().strip()
        parts = seed.split()
        slot_a = parts[0] if len(parts) > 0 else ""
        slot_b = " ".join(parts[1:]) if len(parts) > 1 else ""

        # 1. 既知シードの特化辞書
        templates = {
            "おもちゃ サブスク": (
                ["知育", "レンタル", "買取", "収納", "人気", "年齢別", "片付け", "手作り", "消毒", "プレゼント", "赤ちゃん"],
                ["絵本", "洋服", "家具", "知育玩具", "花", "コーヒー", "お菓子", "家電", "音楽", "ゲーム", "服"]
            ),
            "はちみつレモン 体に悪い": (
                ["太る", "効果", "作り方", "カビ", "毎日", "賞味期限", "妊娠中", "保存容器", "白湯", "クエン酸", "効能"],
                ["レモン水", "リンゴ酢", "トマトジュース", "豆乳", "プロテイン", "炭酸水", "白湯", "お茶", "コーヒー", "緑茶", "青汁"]
            ),
            "自己肯定感 低い": (
                ["診断", "高める", "上げる", "特徴", "毒親", "原因", "チェック", "子供", "恋愛", "仕事", "トレーニング"],
                ["自己効力感", "自尊心", "コミュ力", "精神年齢", "語彙力", "集中力", "幸福度", "意欲", "感受性", "免疫力", "運動神経"]
            ),
            "履歴書 セリア": (
                ["ダイソー", "コンビニ", "書き方", "写真", "サイズ", "パート", "バイト", "志望動機", "自己PR", "封筒", "用紙"],
                ["職務経歴書", "封筒", "印鑑", "白封筒", "クリアファイル", "朱肉", "修正テープ", "のり", "ペン", "証明写真", "ファイル"]
            )
        }

        if seed in templates:
            a1, a2 = templates[seed]
        else:
            # 汎用展開ロジック (シードの意味に合わせたインテリジェント展開)
            a1 = ["おすすめ", "人気", "評判", "口コミ", "比較", "選び方", "使い方", "料金", "メリット", "デメリット", "ランキング"]
            # スロットBに応じた展開
            if "サブスク" in slot_b:
                a2 = ["絵本", "おもちゃ", "洋服", "家具", "花", "コーヒー", "知育玩具", "家電", "服", "お菓子", "本"]
            elif "悪い" in slot_b or "危険" in slot_b:
                a2 = ["豆乳", "トマトジュース", "リンゴ酢", "レモン水", "炭酸水", "プロテイン", "白湯", "お茶", "コーヒー", "牛乳", "緑茶"]
            elif "低い" in slot_b or "高い" in slot_b:
                a2 = ["自己効力感", "自尊心", "コミュ力", "精神年齢", "幸福度", "集中力", "意欲", "語彙力", "自己肯定感", "知能", "感受性"]
            elif "セリア" in slot_b or "ダイソー" in slot_b:
                a2 = ["職務経歴書", "封筒", "印鑑", "クリアファイル", "白封筒", "履歴書", "文房具", "ノート", "ファイル", "ペン", "修正テープ"]
            else:
                a2 = ["人気", "おすすめ", "安い", "コスパ", "定番", "最新", "プロ", "初心者", "店舗", "通販", "専門店"]

        self.txt_axis1.delete("1.0", tk.END)
        self.txt_axis1.insert("1.0", "\n".join(a1))
        self.txt_axis2.delete("1.0", tk.END)
        self.txt_axis2.insert("1.0", "\n".join(a2))
        self._update_threshold_meter()

    def _get_terms(self, text_widget: tk.Text):
        """テキストウィジェットから空行を除いたリストを取得"""
        raw = text_widget.get("1.0", tk.END)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return lines

    def _update_threshold_meter(self):
        """25件閾値の集計とUI更新"""
        seed = self.var_seed.get().strip()
        axis1_terms = self._get_terms(self.txt_axis1)
        axis2_terms = self._get_terms(self.txt_axis2)

        # 重複排除して合計KW数をカウント
        parts = seed.split()
        slot_a = parts[0] if len(parts) > 0 else ""
        slot_b = " ".join(parts[1:]) if len(parts) > 1 else ""

        all_kw = set()
        if seed:
            all_kw.add(seed)
        if slot_a:
            all_kw.add(slot_a)
        if slot_b:
            all_kw.add(slot_b)

        for t in axis1_terms:
            if slot_a:
                all_kw.add(f"{slot_a} {t}")
            else:
                all_kw.add(t)

        for t in axis2_terms:
            if slot_b:
                all_kw.add(f"{t} {slot_b}")
            else:
                all_kw.add(t)

        count = len(all_kw)
        self.progress_bar["value"] = min(count, MIN_THRESHOLD_DEFAULT)

        if count >= MIN_THRESHOLD_DEFAULT:
            self.lbl_count_badge.config(
                text=f"合計: {count} / 25件 (達成)",
                bg=COLOR_SUCCESS_BG,
                fg=COLOR_SUCCESS_FG
            )
            self.lbl_status_msg.config(
                text="✔ 閾値達成！1-Shotメガバッチ (API: 1回) 実行可能",
                foreground="#15803d"
            )
            self.btn_run.config(state=tk.NORMAL)
        else:
            deficit = MIN_THRESHOLD_DEFAULT - count
            self.lbl_count_badge.config(
                text=f"合計: {count} / 25件 (不足: {deficit})",
                bg=COLOR_ALERT_BG,
                fg=COLOR_ALERT_FG
            )
            self.lbl_status_msg.config(
                text=f"⚠ あと {deficit} 個不足しています (API消費0回で保護中)",
                foreground="#b91c1c"
            )

    def _reset_sample_terms(self):
        """サンプル語句を再投入"""
        self.txt_axis1.delete("1.0", tk.END)
        self.txt_axis2.delete("1.0", tk.END)
        default_axis1 = "太る\n効果\n作り方\nカビ\n毎日\n賞味期限\n妊娠中\n保存容器\n白湯\nクエン酸\n効能"
        default_axis2 = "レモン水\nリンゴ酢\nトマトジュース\n豆乳\nプロテイン\n炭酸水\n白湯\nお茶\nコーヒー\n緑茶\n青汁"
        self.txt_axis1.insert("1.0", default_axis1)
        self.txt_axis2.insert("1.0", default_axis2)
        self._update_threshold_meter()

    def _clear_axes(self):
        """入力テキストを全消去"""
        self.txt_axis1.delete("1.0", tk.END)
        self.txt_axis2.delete("1.0", tk.END)
        self._update_threshold_meter()

    def _log_to_console(self, text: str):
        """コンソールウィジェットにスレッドセーフで追記"""
        self.console.after(0, self._append_console_text, text)

    def _append_console_text(self, text: str):
        self.console.insert(tk.END, text)
        self.console.see(tk.END)

    def _clear_console(self):
        self.console.delete("1.0", tk.END)

    def _on_run_clicked(self):
        """1-Shot メガバッチ実行ボタン押下時の処理"""
        seed = self.var_seed.get().strip()
        if not seed:
            messagebox.showwarning("入力エラー", "シードキーワードを入力してください。")
            return

        axis1_terms = self._get_terms(self.txt_axis1)
        axis2_terms = self._get_terms(self.txt_axis2)

        # 展開キーワード全件の作成
        parts = seed.split()
        slot_a = parts[0] if len(parts) > 0 else ""
        slot_b = " ".join(parts[1:]) if len(parts) > 1 else ""

        all_kw_set = set()
        if seed: all_kw_set.add(seed)
        if slot_a: all_kw_set.add(slot_a)
        if slot_b: all_kw_set.add(slot_b)

        for t in axis1_terms:
            if slot_a: all_kw_set.add(f"{slot_a} {t}")
            else: all_kw_set.add(t)

        for t in axis2_terms:
            if slot_b: all_kw_set.add(f"{t} {slot_b}")
            else: all_kw_set.add(t)

        total_count = len(all_kw_set)

        # Rule 04: 25件未満APIコール完全抑止
        if total_count < MIN_THRESHOLD_DEFAULT:
            deficit = MIN_THRESHOLD_DEFAULT - total_count
            messagebox.showerror(
                "Rule 04 閾値エラー (API保護)",
                f"キーワードが合計 {total_count} 個しか集まっていません。\n"
                f"最大効率化に必要な25個まで、あと【 {deficit} 個 】不足しています。\n\n"
                f"APIチケットの無駄遣いを防ぐため、25個以上揃うまでAPIコールは実行できません。"
            )
            return

        # 一時クエリJSONファイルを作成 (Pure ASCII規約に準拠)
        query_file = os.path.join(APP_ROOT, "temp_ui_query.json")
        payload = {
            "seed_keyword": seed,
            "seed_keywords": [s for s in [slot_a, slot_b] if s],
            "axis1_terms": axis1_terms,
            "axis2_terms": axis2_terms,
            "keywords": sorted(list(all_kw_set))
        }

        try:
            with open(query_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("ファイルエラー", f"一時クエリ作成に失敗しました: {e}")
            return

        # 実行準備
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        if self.on_status_change:
            self.on_status_change(True)

        self._log_to_console(f"\n>>> [1-SHOT MEGA-BATCH] 開始: '{seed}' (対象件数: {total_count}件)\n")
        self._log_to_console(f">>> クエリファイル: {query_file}\n")

        args = [
            "-QueryFile", f"'{query_file}'",
            "-NonInteractive",
            "-MinThreshold", str(MIN_THRESHOLD_DEFAULT)
        ]

        def _on_line(line: str):
            self._log_to_console(line)

        def _on_complete(code: int):
            # 一時ファイル削除
            if os.path.exists(query_file):
                try: os.remove(query_file)
                except Exception: pass

            self.btn_run.after(0, lambda: self.btn_run.config(state=tk.NORMAL))
            self.btn_stop.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))
            if self.on_status_change:
                self.on_status_change(False)

            if code == 0:
                self._log_to_console(f"\n[SUCCESS] パイプラインが正常終了しました。(Exit Code: {code})\n")
                if self.on_research_finished:
                    self.on_research_finished()
            else:
                self._log_to_console(f"\n[WARNING] パイプラインが終了コード {code} で終了しました。\n")

        self.runner.run_powershell(
            script_path=SCRIPT_PIPELINE,
            args=args,
            working_dir=os.path.dirname(SCRIPT_PIPELINE),
            on_line=_on_line,
            on_complete=_on_complete
        )

    def _on_stop_clicked(self):
        """プロセス停止"""
        if messagebox.askyesno("確認", "実行中のリサーチプロセスを強制終了しますか？"):
            self.runner.stop()
            self._log_to_console("\n[TERMINATED] ユーザーによってプロセスが停止されました。\n")
            self.btn_run.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if self.on_status_change:
                self.on_status_change(False)
