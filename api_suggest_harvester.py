# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: api_suggest_harvester.py
■ カテゴリ: API / Googleサジェスト実測キーワード・ハーベスター（高速並列版）
■ 責務・役割（Single Responsibility）:
  - AIやシステムによる作為的な単語合成（マナー、持ち物等の強制結合）を完全根絶。
  - GoogleサジェストAPIをThreadPoolExecutorで高速並列走査（1〜2秒完結）し、
    人間が実際に検索している生キーワードのみを各軸25件収集する。
==============================================================================
"""

from typing import List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_suggest_client import fetch_search_suggestions
from filter_prohibited_terms import is_prohibited_term
from engine_semantic_family import detect_semantic_family, detect_scale_family
from engine_context_harmonizer import (
    analyze_seed_context, get_harmonized_axis2_entities, is_contextually_incoherent
)

# 走査文字インデックス（代表文字＋アルファベット）
FAST_CHARS = [
    "", "あ", "い", "う", "え", "お", "か", "き", "く", "け", "こ",
    "さ", "し", "す", "せ", "そ", "た", "ち", "つ", "て", "と",
    "な", "に", "は", "ひ", "ま", "み", "や", "ゆ", "よ", "ら", "り", "わ",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "m", "p", "r", "s", "t"
]

def harvest_axis1_prefix_suggestions(
    prefix: str,
    suffix_context: str = "",
    exclude_seed: str = "",
    target_count: int = 25
) -> List[str]:
    """
    軸①用: [prefix] 〇〇 (前固定) の本物のGoogleサジェストキーワードを高速並列走査・収集する。
    """
    clean_p = prefix.strip()
    clean_seed = exclude_seed.strip()
    if not clean_p:
        return []

    collected: List[str] = []
    seen: Set[str] = set()
    context_info = analyze_seed_context(clean_p, suffix_context) if suffix_context else None

    # Step 1: まずプレフィックス単体のサジェストを取得
    base_suggs = fetch_search_suggestions(f"{clean_p} ")
    for s in base_suggs:
        item = s.strip()
        if not item or item == clean_p or item == clean_seed or is_prohibited_term(item):
            continue
        if item.startswith(clean_p):
            rem = item[len(clean_p):].strip()
            if rem:
                norm = f"{clean_p} {rem}"
                if not (context_info and is_contextually_incoherent(norm, context_info)):
                    if norm not in seen:
                        seen.add(norm)
                        collected.append(norm)

    if len(collected) >= target_count:
        return collected[:target_count]

    # Step 2: 並列走査で不足分を高速取得
    queries = [f"{clean_p} {ch}".strip() for ch in FAST_CHARS if ch]
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_search_suggestions, q): q for q in queries}
        for future in as_completed(future_map):
            try:
                suggs = future.result()
                for s in suggs:
                    item = s.strip()
                    if not item or item == clean_p or item == clean_seed or is_prohibited_term(item):
                        continue
                    if item.startswith(clean_p):
                        rem = item[len(clean_p):].strip()
                        if rem:
                            norm = f"{clean_p} {rem}"
                            if not (context_info and is_contextually_incoherent(norm, context_info)):
                                if norm not in seen:
                                    seen.add(norm)
                                    collected.append(norm)
            except Exception:
                pass
            if len(collected) >= target_count:
                break

    return collected[:target_count]

def harvest_axis2_suffix_suggestions(
    suffix: str,
    seed_entity: str = "",
    exclude_seed: str = "",
    target_count: int = 25
) -> List[str]:
    """
    軸②用: 〇〇 [suffix] (後固定) の本物のGoogleサジェストキーワードを高速並列走査・収集する。
    """
    clean_s = suffix.strip()
    clean_seed = exclude_seed.strip()
    clean_entity = seed_entity.strip()
    if not clean_s:
        return []

    collected: List[str] = []
    seen: Set[str] = set()
    suffix_tokens = clean_s.split()

    # Priority 1: 同族エンティティ（ウイスキー、魚、号数、色等）を並列検証
    candidates = []
    if clean_entity:
        context_info = analyze_seed_context(clean_entity, clean_s)
        candidates = get_harmonized_axis2_entities(context_info)
        if not candidates:
            fam = detect_semantic_family(clean_entity) or detect_scale_family(clean_entity)
            if fam:
                _, candidates = fam

    if candidates:
        cand_queries = [f"{m} {clean_s}" for m in candidates if f"{m} {clean_s}" != clean_seed]
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_map = {executor.submit(fetch_search_suggestions, cq): cq for cq in cand_queries}
            for future in as_completed(future_map):
                cq = future_map[future]
                try:
                    suggs = future.result()
                    if suggs: # Googleで実在する検索と認定
                        if cq not in seen and not is_prohibited_term(cq):
                            seen.add(cq)
                            collected.append(cq)
                except Exception:
                    pass
                if len(collected) >= target_count:
                    return collected[:target_count]

    # Priority 2: Suffixの並列走査で実在する前置クエリを収集
    if len(collected) < target_count:
        queries = [f"{clean_s} {ch}".strip() for ch in FAST_CHARS]
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_map = {executor.submit(fetch_search_suggestions, q): q for q in queries}
            for future in as_completed(future_map):
                try:
                    suggs = future.result()
                    for s in suggs:
                        item = s.strip()
                        if not item or item == clean_s or item == clean_seed or is_prohibited_term(item):
                            continue
                        tokens = item.split()
                        if len(suffix_tokens) == 1:
                            if len(tokens) >= 2 and tokens[-1] == suffix_tokens[0]:
                                norm = " ".join(tokens)
                                if norm not in seen and norm != clean_seed:
                                    seen.add(norm)
                                    collected.append(norm)
                        else:
                            # 2語以上サフィックス（例: レシピ フライパン）
                            for i in range(len(tokens) - len(suffix_tokens) + 1):
                                if tokens[i:i + len(suffix_tokens)] == suffix_tokens and i > 0:
                                    p_part = " ".join(tokens[:i])
                                    norm = f"{p_part} {clean_s}"
                                    if norm not in seen and not is_prohibited_term(norm) and norm != clean_seed:
                                        seen.add(norm)
                                        collected.append(norm)
                                    break
                except Exception:
                    pass
                if len(collected) >= target_count:
                    break

    # Priority 3: 前置文字並列走査
    if len(collected) < target_count:
        queries = [f"{ch} {clean_s}" for ch in FAST_CHARS if ch]
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_map = {executor.submit(fetch_search_suggestions, q): q for q in queries}
            for future in as_completed(future_map):
                try:
                    suggs = future.result()
                    for s in suggs:
                        item = s.strip()
                        if not item or item == clean_s or item == clean_seed or is_prohibited_term(item):
                            continue
                        tokens = item.split()
                        if len(tokens) >= 2 and item.endswith(clean_s):
                            if item not in seen and item != clean_seed:
                                seen.add(item)
                                collected.append(item)
                except Exception:
                    pass
                if len(collected) >= target_count:
                    break

    return collected[:target_count]
