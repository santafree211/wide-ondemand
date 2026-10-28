# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: generator_ai_expansion.py
■ カテゴリ: Orchestration / 前後2大固定軸展開オーケストレーター
■ 責務・役割（Single Responsibility）:
  - シードキーワードの構文解析（語数判定: 2語モード / 3語モードの自動判別）。
  - 各展開戦略モジュール（expansion_strategy_2word / expansion_strategy_3word）への委譲・統括。
  - ルール02（完全対称性の原則）およびルール03（25件閾値）に準拠した軸①・軸②の確定返却。

■ 設計思想・背景:
  - 展開ロジックの実装詳細を戦略モジュールへ完全に分離し、
    本モジュールは「語数解析と適切な戦略の呼び出し」のみに専念するスリムなオーケストレーターとする。

■ 入出力仕様:
  - Input: seed: str （例: "茶色 作り方", "スニーカー 厚底 メンズ"）
  - Output: Dict[str, Any] (mode, slot_a, slot_b, axis1, axis2, total_count)
==============================================================================
"""

import re
from typing import Dict, List, Any, Tuple
from expansion_strategy_2word import generate_2word_axes
from expansion_strategy_3word import generate_3word_axes

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
    語数（2語 / 3語以上）を判別し、適切な展開戦略を呼び出して軸①・軸②を生成する
    """
    clean_seed = re.sub(r'[\s\u3000]+', ' ', seed).strip()
    if not clean_seed:
        return {
            "mode": "none",
            "slot_a": "",
            "slot_b": "",
            "axis1_label": "軸①",
            "axis2_label": "軸②",
            "axis1": [],
            "axis2": [],
            "total_count": 0
        }

    tokens = clean_seed.split()

    # 1語のみで既知サフィックスを含む場合の擬似2語化
    if len(tokens) == 1:
        for s in sorted(KNOWN_SUFFIXES, key=len, reverse=True):
            if clean_seed.endswith(s) and len(clean_seed) > len(s):
                tokens = [clean_seed[:-len(s)].strip(), s]
                break

    if len(tokens) >= 3:
        return generate_3word_axes(tokens, clean_seed)
    elif len(tokens) == 2:
        return generate_2word_axes(tokens, clean_seed)
    else:
        # 1語のみの場合のフォールバック
        return generate_2word_axes([tokens[0], "おすすめ"], clean_seed)

if __name__ == "__main__":
    import sys
    test_seed = sys.argv[1] if len(sys.argv) > 1 else "スニーカー厚底 メンズ"
    res = generate_axes(test_seed)
    print(f"Mode: {res['mode']}, Axis1: {len(res['axis1'])}, Axis2: {len(res['axis2'])}, Total: {res['total_count']}")
