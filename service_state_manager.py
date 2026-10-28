# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: service_state_manager.py
■ カテゴリ: Data Service / 状態管理・リサーチ結果取得サービス
■ 責務・役割（Single Responsibility）:
  - フォーム入力状態（state.json）の永続化保存および読み込み。
  - バックグラウンドワーカーの進行状態（progress_status.json）の読み込み。
  - keywords_db.json からの特定シードKWに限定したリサーチ結果の厳格フィルタリング取得。
  - main.py からデータ入出力・ファイルIOの責務を完全に排除・集約する。

■ 設計思想・背景:
  - main.py がHTTPルーティング（ディスパッチ）のみに集中できるよう、
    ファイル読み書きやフィルタリングロジックを本サービスに完全に隔離する。
  - シードKWの完全厳格フィルタリングにより、過去の別シード結果（100均等）が漏洩するのを防ぐ。

■ 入出力仕様:
  - [get_form_state]: Output: Dict[str, Any]
  - [save_form_state]: Input: Dict[str, Any] -> Output: bool
  - [get_research_progress]: Output: Dict[str, Any]
  - [get_research_results]: Input: target_seed (str) -> Output: List[Dict[str, Any]]
==============================================================================
"""

import json
from pathlib import Path
from typing import Dict, Any, List

HERE = Path(__file__).parent.resolve()
WIDE_DIR = Path(r"C:\Users\santa\OneDrive\prideall\projects\wide").resolve()
STATE_FILE = WIDE_DIR / "state.json"
PROGRESS_FILE = WIDE_DIR / "progress_status.json"
DB_FILE = WIDE_DIR / "keywords_db.json"

def get_form_state() -> Dict[str, Any]:
    """フォームの前回入力状態を取得"""
    state = {}
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
    return state

def save_form_state(state_data: Dict[str, Any]) -> bool:
    """フォームの入力状態を保存"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def get_research_progress() -> Dict[str, Any]:
    """リサーチ進行状態を取得"""
    prog = {"status": "IDLE", "current": 0, "total": 0, "percent": 0, "current_keyword": "", "message": ""}
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                prog = json.load(f)
        except Exception:
            pass
    return prog

def get_research_results(target_seed: str = "") -> List[Dict[str, Any]]:
    """
    指定シードキーワードに厳格一致するリサーチ結果を取得。
    シード未指定時または一致なし時は空配列 [] を返す（過去データの漏洩防止）。
    """
    items = []
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8-sig") as f:
                raw = json.load(f)
                items = raw.get("keywords", [])
        except Exception:
            pass

    if target_seed and target_seed.strip():
        norm_seed = target_seed.replace(" ", "").replace("　", "").lower()
        items = [
            it for it in items
            if it.get("seed_keyword", "").replace(" ", "").replace("　", "").lower() == norm_seed
        ]
    else:
        items = []

    return items
