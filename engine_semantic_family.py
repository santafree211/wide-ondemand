# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: engine_semantic_family.py
■ カテゴリ: Engine / 文脈・同族判定統合エンジン
■ 責務・役割（Single Responsibility）:
  - 入力単語の文脈（ジャンル・単位・スケール）を読み取り、同列・並列に展開すべき「同族リスト」を特定・返却する。
  - スケール判定（engine_scale_family）および辞書カタログ（dict_semantic_catalog）の統合窓口として機能する。

■ 設計思想・背景:
  - 巨大だった辞書定数を `dict_semantic_catalog.py` へ、スケール計算を `engine_scale_family.py` へ分離。
  - 本モジュールは約110行の極めてスリムな判定エンジンとして独立性を担保する。

■ 入出力仕様:
  - Input: term: str （例: "5号", "3合", "茶色", "カメラ", "炊飯器", "スニーカー"）
  - Output: Optional[Tuple[str, List[str]]] (カテゴリ名, [同族単語リスト])
==============================================================================
"""

import re
from typing import Dict, List, Tuple, Optional

# 分離したカタログ辞書モジュール
from dict_semantic_catalog import (
    COLORS_FULL, FOOTWEAR_LIST, SWEETS_LIST, STAPLES_LIST,
    COOKING_APPLIANCES, APP_GENRES, DISHES_LIST, SEASONINGS_LIST,
    HARDWARE_PARTS, APPLIANCES_LIST, HEALTH_DRINKS, MENTAL_TRAITS,
    CAR_WASH_STYLES
)

# 分離した数値スケール判定モジュール
from engine_scale_family import detect_scale_family

def detect_semantic_family(term: str) -> Optional[Tuple[str, List[str]]]:
    """
    単語の意味・カテゴリ（色、スイーツ、穀物、調理器具、アプリ、家電、健康飲料、メンタル等）を判定し、同族単語リストを返す
    """
    clean = term.strip()

    # 1. まずスケールパターンをチェック
    scale_res = detect_scale_family(clean)
    if scale_res:
        return scale_res

    # 2. 色（〜色、基本色）
    for c in COLORS_FULL:
        base_c = c.replace("色", "")
        if clean == c or clean == base_c or clean.startswith(base_c) or clean.endswith(c):
            is_iro_suffix = clean.endswith("色")
            res = []
            for item in COLORS_FULL:
                target = item if is_iro_suffix else item.replace("色", "")
                if target != clean and target not in res:
                    res.append(target)
            return "color", res

    # 3. 各種意味カテゴリ（完全一致または部分一致照合）
    catalogs = [
        ("footwear", FOOTWEAR_LIST),
        ("sweet", SWEETS_LIST),
        ("staple", STAPLES_LIST),
        ("cooking_appliance", COOKING_APPLIANCES),
        ("app_genre", APP_GENRES),
        ("dish", DISHES_LIST),
        ("seasoning", SEASONINGS_LIST),
        ("hardware_part", HARDWARE_PARTS),
        ("appliance", APPLIANCES_LIST),
        ("health_drink", HEALTH_DRINKS),
        ("mental_trait", MENTAL_TRAITS),
        ("car_wash", CAR_WASH_STYLES)
    ]

    for cat_name, cat_list in catalogs:
        matched = False
        for item in cat_list:
            if clean == item or (len(item) >= 2 and (item in clean or clean in item)):
                matched = True
                break
        if matched:
            res = [x for x in cat_list if x != clean]
            return cat_name, res

    return None

if __name__ == "__main__":
    import sys
    test_term = sys.argv[1] if len(sys.argv) > 1 else "スニーカー"
    res = detect_semantic_family(test_term)
    if res:
        print(f"Detected category: {res[0]}, Count: {len(res[1])}, Top 5: {res[1][:5]}")
    else:
        print(f"No semantic family detected for: {test_term}")
