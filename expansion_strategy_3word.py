# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: expansion_strategy_3word.py
■ カテゴリ: Expansion / 3語キーワード（[A] [B] [C]）前後スライド固定展開戦略
■ 責務・役割（Single Responsibility）:
  - 3語シードキーワード（[A] [B] [C]）を受け取り、文脈死守スライド固定型（ルール02）で軸①・軸②を生成する。
  - 軸① `[A B] 〇〇`: 前ペア固定（例: カメラ アプリ 〇〇、5号 ケーキ 〇〇）。サジェストおよび悩み・目的系で25個深掘り。
  - 軸② `〇〇 [B C]`: 後ペア固定（例: 〇〇 アプリ ロゴ、〇〇 ケーキ 切り方）。Aの同族を前置して25個横展開。
  - 各軸きっかり25個（計50個）の重複ゼロ・実測クエリ候補を確定して返却する。
==============================================================================
"""

import json
from typing import Dict, List, Any
from api_suggest_client import fetch_search_suggestions
from engine_semantic_family import detect_semantic_family, detect_scale_family
from filter_prohibited_terms import is_prohibited_term

INTENT_EXTENSIONS = [
    "おすすめ", "人気", "無料", "やり方", "コツ", "比較", "違い", "初心者",
    "ランキング", "選び方", "使い方", "理由", "デメリット", "簡単", "プロ",
    "基本", "注意点", "アレンジ", "失敗", "自作", "安全", "効果", "時間"
]

def generate_3word_axes(tokens: List[str], clean_seed: str) -> Dict[str, Any]:
    slot_a = tokens[0]
    slot_b = tokens[1]
    slot_c = " ".join(tokens[2:])

    prefix_pair = f"{slot_a} {slot_b}"  # [A B]
    suffix_pair = f"{slot_b} {slot_c}"  # [B C]

    # --- 軸①: [A B] 〇〇 (前ペア固定) ---
    axis1_set = set()
    sugg_a1 = fetch_search_suggestions(f"{prefix_pair} ")

    for s in sugg_a1:
        c = s.strip()
        if not c or c == clean_seed or c == prefix_pair: continue
        if is_prohibited_term(c): continue
        if c.startswith(prefix_pair):
            axis1_set.add(c)
        else:
            cand = f"{prefix_pair} {c}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis1_set.add(cand)
        if len(axis1_set) >= 25:
            break

    if len(axis1_set) < 25:
        for ext in INTENT_EXTENSIONS:
            cand = f"{prefix_pair} {ext}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis1_set.add(cand)
            if len(axis1_set) >= 25:
                break

    # --- 軸②: 〇〇 [B C] (後ペア固定) ---
    axis2_set = set()

    family_res = detect_scale_family(slot_a) or detect_semantic_family(slot_a)
    if family_res:
        _, family_members = family_res
        for member in family_members:
            cand = f"{member} {suffix_pair}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis2_set.add(cand)
            if len(axis2_set) >= 25:
                break

    if len(axis2_set) < 25:
        sugg_a2 = fetch_search_suggestions(f"{suffix_pair} ")
        for s in sugg_a2:
            c = s.strip()
            if not c or c == clean_seed or c == suffix_pair: continue
            if is_prohibited_term(c): continue
            parts = c.split()
            other_parts = [p for p in parts if p not in [slot_b, slot_c]]
            if other_parts:
                cand = f"{' '.join(other_parts)} {suffix_pair}"
                if cand != clean_seed and not is_prohibited_term(cand):
                    axis2_set.add(cand)
            if len(axis2_set) >= 25:
                break

    if len(axis2_set) < 25:
        ALT_PREFIXES = [
            "おすすめ", "人気", "最新", "プロ", "簡単", "初心者", "定番",
            "安い", "高評価", "話題", "便利", "基本", "失敗しない", "おしゃれ"
        ]
        for p in ALT_PREFIXES:
            cand = f"{p} {suffix_pair}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis2_set.add(cand)
            if len(axis2_set) >= 25:
                break

    axis1_list = sorted(list(axis1_set))[:25]
    axis2_list = sorted(list(axis2_set))[:25]

    return {
        "mode": "3_words",
        "slot_a": prefix_pair,
        "slot_b": suffix_pair,
        "axis1_label": f"軸①: [{prefix_pair}] 〇〇 (前固定)",
        "axis2_label": f"軸②: 〇〇 [{suffix_pair}] (後固定)",
        "axis1": axis1_list,
        "axis2": axis2_list,
        "total_count": len(axis1_list) + len(axis2_list)
    }
