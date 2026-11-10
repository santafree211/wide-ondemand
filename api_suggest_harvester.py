# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: api_suggest_harvester.py
■ カテゴリ: API / Googleサジェスト実測キーワード・ハーベスター（高速並列版）
■ 責務・役割（Single Responsibility）:
  - 軸①（前固定）: GoogleサジェストAPIを並列走査し、実需のある生クエリを25件収集。
  - 軸②（後固定）: LLMによる動的カテゴリ推論 ＋ Google実需並列検証で、
    文字ハック（a ブランド、か ブランド等）のゴミを100%根絶し、実在クエリのみを25件収集。
==============================================================================
"""

import re
from typing import List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_suggest_client import fetch_search_suggestions
from filter_prohibited_terms import is_prohibited_term
from engine_semantic_family import detect_semantic_family, detect_scale_family
from engine_context_harmonizer import (
    analyze_seed_context, get_harmonized_axis2_entities, is_contextually_incoherent
)
from engine_gemini_client import infer_related_entities_via_gemini

FAST_CHARS = [
    "", "あ", "い", "う", "え", "お", "か", "き", "く", "け", "こ",
    "さ", "し", "す", "せ", "そ", "た", "ち", "つ", "て", "と",
    "な", "に", "は", "ひ", "ま", "み", "や", "ゆ", "よ", "ら", "り", "わ",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "m", "p", "r", "s", "t"
]

def is_noise_axis2_term(kw: str, suffix: str) -> bool:
    """軸②における頭文字・単語断片ノイズ（a ブランド、か ブランド等）を判定"""
    clean_kw = re.sub(r'[\s\u3000]+', ' ', kw).strip()
    clean_s = suffix.strip()
    if not clean_kw.endswith(clean_s):
        return True
    prefix_part = clean_kw[:-len(clean_s)].strip()
    if not prefix_part:
        return True
    tokens = prefix_part.split()
    # 最後の前置単語が1文字以下の場合はノイズ
    if len(tokens[-1]) <= 1:
        return True
    # 記号（ü, ., 英語1文字など）の混入
    if re.search(r'[üäö\.]|^[a-zA-Z]$', prefix_part):
        return True
    return False

def harvest_axis1_prefix_suggestions(
    prefix: str,
    suffix_context: str = "",
    exclude_seed: str = "",
    target_count: int = 25
) -> List[str]:
    """軸①用: [prefix] 〇〇 (前固定) の本物のGoogleサジェストキーワードを収集"""
    clean_p = prefix.strip()
    clean_seed = exclude_seed.strip()
    if not clean_p:
        return []

    collected: List[str] = []
    seen: Set[str] = set()
    context_info = analyze_seed_context(clean_p, suffix_context) if suffix_context else None

    # Step 1: プレフィックス単体サジェスト
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

    # Step 2: 並列走査
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
    """軸②用: 〇〇 [suffix] (後固定) をLLM推論 ＋ Google実需照合で収集"""
    clean_s = suffix.strip()
    clean_seed = exclude_seed.strip()
    clean_entity = seed_entity.strip()
    if not clean_s:
        return []

    collected: List[str] = []
    seen: Set[str] = set()

    # Step 1: LLM（Gemini）による動的同族・競合・関連アイテム推論
    candidates = []
    if clean_entity:
        ai_entities = infer_related_entities_via_gemini(clean_entity, clean_s)
        if ai_entities:
            candidates.extend(ai_entities)

    # Step 2: セマンティックカタログ（静的同族: ウイスキー、号数、色等）
    if clean_entity:
        context_info = analyze_seed_context(clean_entity, clean_s)
        cat_entities = get_harmonized_axis2_entities(context_info)
        if cat_entities:
            candidates.extend(cat_entities)
        else:
            fam = detect_semantic_family(clean_entity) or detect_scale_family(clean_entity)
            if fam:
                _, fam_cands = fam
                candidates.extend(fam_cands)

    # Step 3: 軸①（前固定）の実在サジェストからのアイテム抽出
    if clean_entity:
        try:
            base_suggs = fetch_search_suggestions(f"{clean_entity} ")
            for bs in base_suggs:
                bs_clean = bs.strip()
                if bs_clean.startswith(clean_entity):
                    sub = bs_clean[len(clean_entity):].strip()
                    if sub and len(sub) >= 2 and not is_prohibited_term(sub):
                        candidates.append(f"{clean_entity}{sub}")
                        candidates.append(sub)
        except Exception:
            pass

    # 重複除去した候補群をGoogleサジェストで高速並列検証
    unique_cands = []
    for c in candidates:
        c_clean = c.strip()
        if c_clean and c_clean != clean_entity and c_clean not in unique_cands and len(c_clean) >= 2:
            unique_cands.append(c_clean)

    if unique_cands:
        cand_queries = [f"{m} {clean_s}" for m in unique_cands if f"{m} {clean_s}" != clean_seed]
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_map = {executor.submit(fetch_search_suggestions, cq): cq for cq in cand_queries}
            for future in as_completed(future_map):
                cq = future_map[future]
                try:
                    suggs = future.result()
                    # Googleで実在し、かつノイズでないものを採用
                    if suggs and not is_noise_axis2_term(cq, clean_s) and not is_prohibited_term(cq):
                        if cq not in seen:
                            seen.add(cq)
                            collected.append(cq)
                except Exception:
                    pass
                if len(collected) >= target_count:
                    return collected[:target_count]

    # Step 4: Suffix自体の自然な前置サジェスト（断片ノイズは完全遮断）
    if len(collected) < target_count:
        suffix_tokens = clean_s.split()
        s_len = len(suffix_tokens)
        queries = [f"{clean_s} {ch}".strip() for ch in FAST_CHARS[:20]]
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
                        if len(tokens) > s_len:
                            if tokens[-s_len:] == suffix_tokens:
                                p_part = " ".join(tokens[:-s_len])
                                norm = f"{p_part} {clean_s}"
                                if not is_noise_axis2_term(norm, clean_s) and norm not in seen and norm != clean_seed:
                                    seen.add(norm)
                                    collected.append(norm)
                            elif tokens[:s_len] == suffix_tokens:
                                p_part = " ".join(tokens[s_len:])
                                norm = f"{p_part} {clean_s}"
                                if not is_noise_axis2_term(norm, clean_s) and norm not in seen and norm != clean_seed:
                                    seen.add(norm)
                                    collected.append(norm)
                except Exception:
                    pass
                if len(collected) >= target_count:
                    break

    return collected[:target_count]
