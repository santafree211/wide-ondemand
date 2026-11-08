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
from validator_semantic_coherence import is_semantically_incoherent, get_fallback_prefixes_for_suffix
from engine_context_harmonizer import (
    analyze_seed_context, get_harmonized_axis1_terms, get_harmonized_axis2_entities,
    is_contextually_incoherent
)

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

    # 【シード文脈・相互整合解析】AとBの関係性から統合テーマを特定
    context_info = analyze_seed_context(slot_a, slot_b)

    # --- 軸①: [A] 〇〇 (前固定) ---
    # Bの文脈（食べる、値段、汚れ等）と調和する語句を優先注入
    axis1_set = set()
    sugg_a1 = fetch_search_suggestions(f"{slot_a} ")
    sugg_a1_sorted = sorted(sugg_a1, key=score_term, reverse=True)

    for s in sugg_a1_sorted:
        c = s.strip()
        if not c: continue
        if c == clean_seed or c == slot_a: continue
        if is_prohibited_term(c): continue
        if c.startswith(slot_a):
            target_kw = c
        else:
            target_kw = f"{slot_a} {c}"

        t_parts = target_kw.split()
        if len(t_parts) >= 2 and is_semantically_incoherent(t_parts[0], ' '.join(t_parts[1:])):
            continue
        if is_contextually_incoherent(target_kw, context_info):
            continue
        axis1_set.add(target_kw)
        if len(axis1_set) >= 25:
            break

    if len(axis1_set) < 25:
        # Bの文脈（調理・食味、コスト等）に整合したキラーサフィックスを最優先注入
        harmonized_terms = get_harmonized_axis1_terms(context_info)
        fallback_candidates = harmonized_terms + HIGH_RETENTION_TERMS

        for t in fallback_candidates:
            if is_semantically_incoherent(slot_a, t):
                continue
            cand = f"{slot_a} {t}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis1_set.add(cand)
            if len(axis1_set) >= 25:
                break

    # --- 軸②: 〇〇 [B] (後固定) ---
    # Aのドメイン（魚類、家電、衣服等）に完全に整合した同族を最優先ロック
    axis2_set = set()

    harmonized_entities = get_harmonized_axis2_entities(context_info)
    if harmonized_entities:
        for member in harmonized_entities:
            cand = f"{member} {slot_b}"
            if cand != clean_seed and not is_prohibited_term(cand):
                axis2_set.add(cand)
            if len(axis2_set) >= 25:
                break

    if len(axis2_set) < 25:
        scale_res = detect_scale_family(slot_a)
        if scale_res:
            _, scale_members = scale_res
            for m in scale_members:
                cand = f"{m} {slot_b}"
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
            # 末尾が slot_b で終わっている自然な後置クエリのみ採用
            if c.endswith(slot_b) and c != slot_b:
                prefix_cand = c[:-len(slot_b)].strip()
                if prefix_cand and not is_semantically_incoherent(prefix_cand, slot_b):
                    axis2_set.add(c)
            if len(axis2_set) >= 25:
                break

    if len(axis2_set) < 25:
        fallbacks = get_fallback_prefixes_for_suffix(slot_b)
        for t in fallbacks:
            if is_semantically_incoherent(t, slot_b):
                continue
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
