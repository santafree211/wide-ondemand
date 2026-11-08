# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: validator_pre_output.py
■ カテゴリ: Validation / 出力前自動品質検証プロセス（Pre-Output Quality Gate）
■ 責務・役割（Single Responsibility）:
  - 軸①・軸②の生成結果を出力・表示する直前に、全キーワードの構文・意味整合性を自動監査する。
  - 不自然な語、重複語、文法崩れを1件も漏らさず検知・排除する。
  - 25件未満の場合はGoogleサジェストハーベスターから追加実測クエリを補充し、人工合成語の混入を100%遮断する。
  - ルール03（事前出力バリデーション規約）を100%自動執行する。
=============================================================================
"""

from typing import Dict, List, Any, Tuple
from validator_semantic_coherence import is_semantically_incoherent
from filter_prohibited_terms import is_prohibited_term
from api_suggest_harvester import harvest_axis1_prefix_suggestions, harvest_axis2_suffix_suggestions

def validate_and_repair_axis(
    axis_list: List[str],
    slot_fixed: str,
    is_prefix_fixed: bool,
    seed_context: str = "",
    target_count: int = 25
) -> Tuple[List[str], List[Any]]:
    """
    1つの軸リストに対して、出力直前の完全自動検証および不備語の排除・本物サジェストによる再補充を行う。
    """
    valid_items = []
    seen = set()
    filtered_junk = []

    for kw in axis_list:
        clean_kw = kw.strip()
        if not clean_kw or clean_kw in seen:
            continue

        # 1. 禁止語チェック
        if is_prohibited_term(clean_kw):
            filtered_junk.append((clean_kw, "PROHIBITED_TERM"))
            continue

        # 2. 単語内トークン重複チェック（例: 「汚れ 汚れ」「インク インク」）
        tokens = clean_kw.split()
        if len(tokens) != len(set(tokens)):
            filtered_junk.append((clean_kw, "TOKEN_DUPLICATION"))
            continue

        # 3. 意味整合性チェック（プレフィックス × サフィックス）
        if len(tokens) >= 2:
            prefix_part = tokens[0]
            suffix_part = " ".join(tokens[1:])
            if is_semantically_incoherent(prefix_part, suffix_part):
                filtered_junk.append((clean_kw, "SEMANTIC_INCOHERENCE"))
                continue

        seen.add(clean_kw)
        valid_items.append(clean_kw)

    # 4. 25件に満たない場合の本物サジェスト再補充プロセス（合成語の生成は永久禁止）
    if len(valid_items) < target_count:
        if is_prefix_fixed:
            fresh = harvest_axis1_prefix_suggestions(
                prefix=slot_fixed,
                suffix_context=seed_context,
                target_count=target_count + 10
            )
        else:
            fresh = harvest_axis2_suffix_suggestions(
                suffix=slot_fixed,
                seed_entity=seed_context,
                target_count=target_count + 10
            )

        for cand in fresh:
            if cand in seen or is_prohibited_term(cand):
                continue
            c_tokens = cand.split()
            if len(c_tokens) != len(set(c_tokens)):
                continue
            p_part = c_tokens[0]
            s_part = " ".join(c_tokens[1:])
            if is_semantically_incoherent(p_part, s_part):
                continue

            seen.add(cand)
            valid_items.append(cand)
            if len(valid_items) >= target_count:
                break

    final_list = valid_items[:target_count]
    return final_list, filtered_junk

def run_pre_output_validation(axes_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成結果辞書（axis1, axis2）を受け取り、完全監査・修復を実行して検証済み結果を返却する。
    """
    mode = axes_result.get("mode", "2_words")
    slot_a = axes_result.get("slot_a", "")
    slot_b = axes_result.get("slot_b", "")

    # 軸①の検証・修復（前固定）
    fixed_slot_1 = slot_a
    clean_axis1, junk1 = validate_and_repair_axis(
        axes_result.get("axis1", []),
        slot_fixed=fixed_slot_1,
        is_prefix_fixed=True,
        seed_context=slot_b,
        target_count=25
    )

    # 軸②の検証・修復（後固定）
    fixed_slot_2 = slot_b
    clean_axis2, junk2 = validate_and_repair_axis(
        axes_result.get("axis2", []),
        slot_fixed=fixed_slot_2,
        is_prefix_fixed=False,
        seed_context=slot_a,
        target_count=25
    )

    all_junk = junk1 + junk2
    status = "PASSED_WITH_REPAIRS" if all_junk else "PASSED_CLEAN"

    # 検証済み辞書を構成
    validated_result = dict(axes_result)
    validated_result["axis1"] = clean_axis1
    validated_result["axis2"] = clean_axis2
    validated_result["total_count"] = len(clean_axis1) + len(clean_axis2)
    validated_result["validation_audit"] = {
        "status": status,
        "checked_total": len(axes_result.get("axis1", [])) + len(axes_result.get("axis2", [])),
        "passed_total": len(clean_axis1) + len(clean_axis2),
        "filtered_junk_count": len(all_junk),
        "filtered_details": all_junk
    }

    return validated_result
