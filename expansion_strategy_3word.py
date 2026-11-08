# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: expansion_strategy_3word.py
■ カテゴリ: Expansion / 3語キーワード（[A] [B] [C]）前後スライド固定展開戦略
■ 責務・役割（Single Responsibility）:
  - 3語シードキーワード（[A] [B] [C]）を受け取り、文脈死守スライド固定型（ルール02）で軸①・軸②を生成する。
  - 人工的な単語合成を完全排除し、Googleサジェストハーベスターから本物の生検索キーワードを各25件収集する。
  - 軸① `[A B] 〇〇`: 前ペア固定。Googleサジェスト実測クエリで25個深掘り。
  - 軸② `〇〇 [B C]`: 後ペア固定。Googleサジェスト実測クエリ（料理名・アイテム名等）で25個横展開。
==============================================================================
"""

from typing import Dict, List, Any
from api_suggest_harvester import harvest_axis1_prefix_suggestions, harvest_axis2_suffix_suggestions

def generate_3word_axes(tokens: List[str], clean_seed: str) -> Dict[str, Any]:
    slot_a = tokens[0]
    slot_b = tokens[1]
    slot_c = " ".join(tokens[2:])

    prefix_pair = f"{slot_a} {slot_b}"  # [A B]
    suffix_pair = f"{slot_b} {slot_c}"  # [B C]

    # --- 軸①: [A B] 〇〇 (前ペア固定) ---
    # Googleサジェスト実測クエリのみを収集
    axis1_list = harvest_axis1_prefix_suggestions(
        prefix=prefix_pair,
        suffix_context=slot_c,
        exclude_seed=clean_seed,
        target_count=25
    )

    # --- 軸②: 〇〇 [B C] (後ペア固定) ---
    # Suffix走査による実在クエリ（例: '手羽先 レシピ フライパン'）のみを収集
    axis2_list = harvest_axis2_suffix_suggestions(
        suffix=suffix_pair,
        seed_entity=slot_a,
        exclude_seed=clean_seed,
        target_count=25
    )

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
