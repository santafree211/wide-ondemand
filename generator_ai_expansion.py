# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: generator_ai_expansion.py
■ カテゴリ: Orchestration / 3大軸展開オーケストレーター
■ 責務・役割（Single Responsibility）:
  - シードキーワードの構文解析（語数判定: 2語モード / 3語モードの自動判別）。
  - 各展開戦略モジュール（expansion_strategy_2word / expansion_strategy_3word）への委譲。
  - 第3の軸（generator_blue_ocean: AI創造性・視点ずらし枠25件）の生成と統合。
  - ルール02（完全対称性の原則）およびルール03（25件閾値）に準拠した3軸（計75件）の確定返却。
==============================================================================
"""

import re
from typing import Dict, List, Any, Tuple
from expansion_strategy_2word import generate_2word_axes
from expansion_strategy_3word import generate_3word_axes
from generator_blue_ocean import generate_blue_ocean_keywords
from validator_pre_output import run_pre_output_validation

KNOWN_SUFFIXES = [
    "100均", "ダイソー", "セリア", "キャンドゥ", "ワッツ",
    "おすすめ", "口コミ", "評判", "違い", "比較", "ランキング",
    "使い方", "作り方", "危険性", "デメリット", "メリット", "効果",
    "体に悪い", "買ってはいけないメーカー", "買ってはいけない", "太る", "痩せる",
    "低い", "高い", "サブスク", "レンタル", "知育", "売ってない", "どこで買える"
]

def smart_split_seed(text: str) -> Tuple[str, str]:
    """
    シードキーワードをスペースまたは既知サフィックスに基づいて (slot_a, slot_b) に分解する
    """
    clean = re.sub(r'[\s\u3000]+', ' ', text).strip()
    parts = clean.split()
    if len(parts) >= 3:
        return (f"{parts[0]} {parts[1]}", f"{parts[1]} {' '.join(parts[2:])}")
    if len(parts) == 2:
        return (parts[0], parts[1])
    for s in sorted(KNOWN_SUFFIXES, key=len, reverse=True):
        if clean.endswith(s) and len(clean) > len(s):
            return (clean[:-len(s)].strip(), s)
    return (clean, "")

def generate_axes(seed: str) -> Dict[str, Any]:
    """
    語数（2語 / 3語以上）を判別し、軸①（前固定25）・軸②（後固定25）・軸③（AI創造25）を生成する
    """
    clean_seed = re.sub(r'[\s\u3000]+', ' ', seed).strip()
    if not clean_seed:
        return {
            "mode": "none",
            "slot_a": "",
            "slot_b": "",
            "axis1_label": "軸①: [A] 〇〇 (前固定)",
            "axis2_label": "軸②: 〇〇 [B] (後固定)",
            "axis3_label": "軸③: 💡 ブルーオーシャン・視点ずらし (AI創造25件)",
            "axis1": [],
            "axis2": [],
            "axis3": [],
            "total_count": 0
        }

    tokens = clean_seed.split()

    if len(tokens) == 1:
        for s in sorted(KNOWN_SUFFIXES, key=len, reverse=True):
            if clean_seed.endswith(s) and len(clean_seed) > len(s):
                tokens = [clean_seed[:-len(s)].strip(), s]
                break

    if len(tokens) >= 3:
        raw_res = generate_3word_axes(tokens, clean_seed)
    elif len(tokens) == 2:
        raw_res = generate_2word_axes(tokens, clean_seed)
    else:
        raw_res = generate_2word_axes([tokens[0], "おすすめ"], clean_seed)

    slot_a = raw_res.get("slot_a", "")
    slot_b = raw_res.get("slot_b", "")

    # 第3の軸：AI創造性・視点ずらし枠（25件）を生成
    axis3_list = generate_blue_ocean_keywords(clean_seed, slot_a, slot_b)
    raw_res["axis3"] = axis3_list
    raw_res["axis3_label"] = "軸③: 💡 ブルーオーシャン・視点ずらし (AI創造25件)"

    # 出力直前の完全自動検証＆修復プロセス（Pre-Output Quality Gate）
    validated = run_pre_output_validation(raw_res)
    # total_countを3軸合計に更新
    validated["axis3"] = axis3_list
    validated["axis3_label"] = raw_res["axis3_label"]
    validated["total_count"] = len(validated["axis1"]) + len(validated["axis2"]) + len(axis3_list)

    return validated

if __name__ == "__main__":
    import sys
    test_seed = sys.argv[1] if len(sys.argv) > 1 else "茶色 作り方"
    res = generate_axes(test_seed)
    print(f"Mode: {res['mode']}, Axis1: {len(res['axis1'])}, Axis2: {len(res['axis2'])}, Axis3: {len(res['axis3'])}, Total: {res['total_count']}")
