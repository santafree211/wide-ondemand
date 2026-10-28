# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: expansion_strategy_2word.py
■ カテゴリ: Expansion / 2語キーワード（[A] [B]）前後2大固定軸展開戦略
■ 責務・役割（Single Responsibility）:
  - 2語シードキーワード（[A] [B]）を受け取り、ルール02に準拠した軸①（前固定）と軸②（後固定）を生成する。
  - 軸① `[A] 〇〇`: 前置1語固定（元KW除外）。Googleサジェストと悩み・ハウツー・代用系で25個深掘り。
  - 軸② `〇〇 [B]`: 後置1語固定（元KW除外）。Aの同族（色・号数・家電等）を最優先注入して25個横展開。
  - 各軸きっかり25個（計50個）の重複ゼロ・実測クエリ候補を確定して返却する。
==============================================================================
"""

import json
from typing import Dict, List, Any
from api_suggest_client import fetch_search_suggestions
from engine_semantic_family import detect_semantic_family, detect_scale_family
from filter_prohibited_terms import is_prohibited_term

HIGH_RETENTION_TERMS = [
    "作り方", "使い方", "代用", "代わり", "人気", "おすすめ", "簡単", "自作",
    "改造", "壊れた", "切れた", "外れる", "外れない", "外れ防止", "落下防止",
    "落とす", "落ちる", "付け方", "結び方", "黒", "白", "エアー", "ブランド",
    "身近なもの", "どこで買える", "売ってない"
]

def score_term(t: str) -> int:
    score = 0
    for h in HIGH_RETENTION_TERMS:
        if h in t:
            score += 2
    if any(q in t for q in ["違い", "比較", "デメリット", "理由"]):
        score += 3
    return score

def generate_2word_axes(tokens: List[str], clean_seed: str) -> Dict[str, Any]:
    slot_a = tokens[0]
    slot_b = tokens[1]

    # --- 軸①: [A] 〇〇 (前固定) ---
    axis1_set = set()
    sugg_a1 = fetch_search_suggestions(f"{slot_a} ")
    sugg_a1_sorted = sorted(sugg_a1, key=score_term, reverse=True)

    for s in sugg_a1_sorted:
        c = s.strip()
        if not c: continue
        if c == clean_seed or c == slot_a: continue
        if is_prohibited_term(c): continue
        if c.startswith(slot_a):
            axis1_set.add(c)
        else:
            cand = f"{slot_a} {c}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis1_set.add(cand)
        if len(axis1_set) >= 25:
            break

    if len(axis1_set) < 25:
        for t in HIGH_RETENTION_TERMS:
            cand = f"{slot_a} {t}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis1_set.add(cand)
            if len(axis1_set) >= 25:
                break

    # --- 軸②: 〇〇 [B] (後固定) ---
    axis2_set = set()

    family_res = detect_scale_family(slot_a) or detect_semantic_family(slot_a)
    if family_res:
        _, family_members = family_res
        for member in family_members:
            cand = f"{member} {slot_b}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis2_set.add(cand)
            if len(axis2_set) >= 25:
                break

    if len(axis2_set) < 25:
        sugg_a2 = fetch_search_suggestions(f"{slot_b} ")
        for s in sugg_a2:
            c = s.strip()
            if not c or c == clean_seed or c == slot_b: continue
            if is_prohibited_term(c): continue
            parts = c.split()
            other_parts = [p for p in parts if p != slot_b]
            if other_parts:
                cand = f"{' '.join(other_parts)} {slot_b}"
                if cand != clean_seed and not is_prohibited_term(cand):
                    axis2_set.add(cand)
            if len(axis2_set) >= 25:
                break

    if len(axis2_set) < 25:
        BACKUP_EXPANSIONS = [
            "やり方", "コツ", "人気", "おすすめ", "種類", "選び方", "基本",
            "失敗", "注意点", "アレンジ", "簡単", "初心者", "プロ", "道具",
            "費用", "時間", "メリット", "デメリット", "理由", "手順"
        ]
        for t in BACKUP_EXPANSIONS:
            cand = f"{t} {slot_b}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis2_set.add(cand)
            if len(axis2_set) >= 25:
                break

    axis1_list = sorted(list(axis1_set))[:25]
    axis2_list = sorted(list(axis2_set))[:25]

    return {
        "mode": "2_words",
        "slot_a": slot_a,
        "slot_b": slot_b,
        "axis1_label": f"軸①: [{slot_a}] 〇〇 (前固定)",
        "axis2_label": f"軸②: 〇〇 [{slot_b}] (後固定)",
        "axis1": axis1_list,
        "axis2": axis2_list,
        "total_count": len(axis1_list) + len(axis2_list)
    }
