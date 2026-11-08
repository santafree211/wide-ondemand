# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: expansion_strategy_2word.py
■ カテゴリ: Expansion / 2語キーワード（[A] [B]）前後2大固定軸展開戦略
■ 責務・役割（Single Responsibility）:
  - 2語シードキーワード（[A] [B]）を受け取り、ルール02に準拠した軸①（前固定）と軸②（後固定）を生成する。
  - 人工的な単語合成を完全排除し、Googleサジェストハーベスターから本物の生検索キーワードを各25件収集する。
  - 軸① `[A] 〇〇`: 前置1語固定（元KW除外）。Googleサジェスト実測クエリで25個深掘り。
  - 軸② `〇〇 [B]`: 後置1語固定（元KW除外）。同族エンティティ実在照合＆後置サジェストで25個横展開。
==============================================================================
"""

from typing import Dict, List, Any
from api_suggest_harvester import harvest_axis1_prefix_suggestions, harvest_axis2_suffix_suggestions

def generate_2word_axes(tokens: List[str], clean_seed: str) -> Dict[str, Any]:
    slot_a = tokens[0]
    slot_b = tokens[1]

    # --- 軸①: [A] 〇〇 (前固定) ---
    # Googleサジェスト実測クエリのみを収集（Bの文脈と調和したクエリを優先）
    axis1_list = harvest_axis1_prefix_suggestions(
        prefix=slot_a,
        suffix_context=slot_b,
        exclude_seed=clean_seed,
        target_count=25
    )

    # --- 軸②: 〇〇 [B] (後固定) ---
    # Aの同族エンティティ実在照合およびGoogleサジェスト実測クエリのみを収集
    axis2_list = harvest_axis2_suffix_suggestions(
        suffix=slot_b,
        seed_entity=slot_a,
        exclude_seed=clean_seed,
        target_count=25
    )

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
