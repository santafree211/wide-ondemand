# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: api_suggest_harvester.py
■ カテゴリ: API / Googleサジェスト実測キーワード・ハーベスター
■ 責務・役割（Single Responsibility）:
  - AIやシステムによる作為的な単語合成（マナー、持ち物、やり方等の強制結合）を完全根絶する。
  - Googleが実際に認知・蓄積している「本物の生検索キーワード」のみをサジェストAPIから徹底走査・収集する。
  - 軸①（前固定）および軸②（後固定）に対し、実在する自然なクエリのみで各25件を満たす。
==============================================================================
"""

from typing import List, Set, Optional
from api_suggest_client import fetch_search_suggestions
from filter_prohibited_terms import is_prohibited_term
from engine_semantic_family import detect_semantic_family, detect_scale_family
from engine_context_harmonizer import (
    analyze_seed_context, get_harmonized_axis2_entities, is_contextually_incoherent
)

# 50音＋アルファベットの走査インデックス
SCAN_CHARS = [
    "", "あ", "い", "う", "え", "お", "か", "き", "く", "け", "こ",
    "さ", "し", "す", "せ", "そ", "た", "ち", "つ", "て", "と",
    "な", "に", "ぬ", "ね", "の", "は", "ひ", "ふ", "へ", "ほ",
    "ま", "み", "む", "め", "も", "や", "ゆ", "よ", "ら", "り",
    "る", "れ", "ろ", "わ", "a", "b", "c", "d", "e", "f", "g",
    "h", "i", "j", "k", "l", "m", "n", "o", "p", "r", "s", "t", "w"
]

def harvest_axis1_prefix_suggestions(
    prefix: str,
    suffix_context: str = "",
    exclude_seed: str = "",
    target_count: int = 25
) -> List[str]:
    """
    軸①用: [prefix] 〇〇 (前固定) の本物のGoogleサジェストキーワードを走査・収集する。
    人工的な単語合成は一切行わず、Googleが返した完全一致プレフィックスクエリのみを採用。
    """
    clean_p = prefix.strip()
    clean_seed = exclude_seed.strip()
    collected: List[str] = []
    seen: Set[str] = set()

    if not clean_p:
        return []

    context_info = analyze_seed_context(clean_p, suffix_context) if suffix_context else None

    for ch in SCAN_CHARS:
        query = f"{clean_p} {ch}".strip()
        suggestions = fetch_search_suggestions(query)
        for s in suggestions:
            item = s.strip()
            if not item or item == clean_p or item == clean_seed:
                continue
            if is_prohibited_term(item):
                continue
            # 必ず prefix で始まっていること
            if not item.startswith(clean_p):
                continue
            remainder = item[len(clean_p):].strip()
            if not remainder:
                continue

            normalized = f"{clean_p} {remainder}"
            if context_info and is_contextually_incoherent(normalized, context_info):
                continue

            if normalized not in seen:
                seen.add(normalized)
                collected.append(normalized)
                if len(collected) >= target_count:
                    return collected

    return collected

def harvest_axis2_suffix_suggestions(
    suffix: str,
    seed_entity: str = "",
    exclude_seed: str = "",
    target_count: int = 25
) -> List[str]:
    """
    軸②用: 〇〇 [suffix] (後固定) の本物のGoogleサジェストキーワードを走査・収集する。
    1. 同族エンティティ（魚、号数、色、調理品等）を優先し、Googleサジェストで実在照合
    2. suffix を含む実在サジェストから前置エンティティを抽出（例: '手羽先 レシピ フライパン'）
    3. 前置1文字走査で実在する後置一致クエリを収集
    """
    clean_s = suffix.strip()
    clean_seed = exclude_seed.strip()
    clean_entity = seed_entity.strip()
    collected: List[str] = []
    seen: Set[str] = set()

    if not clean_s:
        return []

    suffix_tokens = clean_s.split()

    # Priority 1: シードエンティティの同族（魚種、色、家電、号数等）をGoogleで実在検証
    if clean_entity:
        context_info = analyze_seed_context(clean_entity, clean_s)
        candidates = get_harmonized_axis2_entities(context_info)
        if not candidates:
            fam = detect_scale_family(clean_entity) or detect_semantic_family(clean_entity)
            if fam:
                _, candidates = fam

        if candidates:
            for member in candidates:
                cand = f"{member} {clean_s}"
                if cand in seen or cand == clean_seed or is_prohibited_term(cand):
                    continue
                # Googleサジェストで実際に検索されているか実在確認
                suggs = fetch_search_suggestions(cand)
                if suggs:
                    seen.add(cand)
                    collected.append(cand)
                    if len(collected) >= target_count:
                        return collected

    # Priority 2: Suffix走査で Google が返す実在クエリ群から抽出（料理名、アイテム名等）
    for ch in SCAN_CHARS:
        query = f"{clean_s} {ch}".strip()
        suggestions = fetch_search_suggestions(query)
        for s in suggestions:
            item = s.strip()
            if not item or item == clean_s or item == clean_seed:
                continue
            if is_prohibited_term(item):
                continue

            tokens = item.split()
            if len(suffix_tokens) == 1:
                # 1語サフィックス（例: 食べる）
                if len(tokens) >= 2 and tokens[-1] == suffix_tokens[0]:
                    normalized = " ".join(tokens)
                    if normalized not in seen and normalized != clean_seed:
                        seen.add(normalized)
                        collected.append(normalized)
                        if len(collected) >= target_count:
                            return collected
            else:
                # 2語以上サフィックス（例: レシピ フライパン）
                match_idx = -1
                for i in range(len(tokens) - len(suffix_tokens) + 1):
                    if tokens[i:i + len(suffix_tokens)] == suffix_tokens:
                        match_idx = i
                        break
                if match_idx > 0:
                    prefix_part = " ".join(tokens[:match_idx])
                    normalized = f"{prefix_part} {clean_s}"
                    if normalized not in seen and not is_prohibited_term(normalized) and normalized != clean_seed:
                        seen.add(normalized)
                        collected.append(normalized)
                        if len(collected) >= target_count:
                            return collected

    # Priority 3: 前置文字走査で実在する後置一致クエリを収集
    if len(collected) < target_count:
        for ch in SCAN_CHARS[1:]:
            q = f"{ch} {clean_s}"
            suggestions = fetch_search_suggestions(q)
            for s in suggestions:
                item = s.strip()
                if not item or item == clean_s or item == clean_seed:
                    continue
                if is_prohibited_term(item):
                    continue
                tokens = item.split()
                if len(tokens) >= 2 and item.endswith(clean_s):
                    if item not in seen and item != clean_seed:
                        seen.add(item)
                        collected.append(item)
                        if len(collected) >= target_count:
                            return collected

    return collected
