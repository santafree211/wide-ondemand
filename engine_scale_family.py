# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: engine_scale_family.py
■ カテゴリ: Engine / 数値スケール・単位同族判定エンジン
■ 責務・役割（Single Responsibility）:
  - 数値＋単位パターン（号数、合数、人前、年代、年齢、月齢、寸法、重量・容量等）を正規表現で検出。
  - 現在の数値を基準に、差分の絶対値が小さい順（近接順）にソートした同族スケールリストを動的生成・返却する。
==============================================================================
"""

import re
from typing import List, Tuple, Optional

def detect_scale_family(term: str) -> Optional[Tuple[str, List[str]]]:
    """
    数値＋単位パターン（号数、合数、人前、年代など）を判定し、同族スケールリストを動的生成
    """
    clean = term.strip()

    # 1. 号数 (^d+号$)
    m_gou = re.match(r'^(\d+)号$', clean)
    if m_gou:
        curr = int(m_gou.group(1))
        common_gous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 20]
        sorted_gous = sorted([g for g in common_gous if g != curr], key=lambda x: abs(x - curr))
        return "scale_gou", [f"{g}号" for g in sorted_gous]

    # 2. 合数 (^d+合$, 半合, 一升, 1升)
    if re.match(r'^(\d+|半|一|1)合$', clean) or clean in ["一升", "1升"]:
        all_gous = ["1合", "2合", "3合", "4合", "5合", "6合", "半合", "一升", "1升", "0.5合", "1.5合", "2.5合", "3.5合", "7合", "8合", "10合"]
        res = [g for g in all_gous if g != clean]
        return "scale_goh", res

    # 3. 人前・人分・人数 (^d+(人前|人分|人)$)
    m_nin = re.match(r'^(\d+)(人前|人分|人)$', clean)
    if m_nin:
        curr_num = int(m_nin.group(1))
        unit = m_nin.group(2)
        common_nums = [1, 2, 3, 4, 5, 6, 8, 10]
        sorted_nums = sorted([n for n in common_nums if n != curr_num], key=lambda x: abs(x - curr_num))
        res = [f"{n}{unit}" for n in sorted_nums]
        alt_unit = "人分" if unit == "人前" else "人前"
        res.extend([f"{n}{alt_unit}" for n in sorted_nums[:5]])
        res.extend([f"何{unit}", "一人前", "二人前", "三人前"])
        return "scale_nin", [r for r in res if r != clean]

    # 4. 年代 (^d+0代$ or ^d+代$)
    m_dai = re.match(r'^(\d+)代$', clean)
    if m_dai:
        all_dais = ["10代", "20代", "30代", "40代", "50代", "60代", "70代", "80代", "アラサー", "アラフォー", "アラフィフ"]
        return "scale_dai", [d for d in all_dais if d != clean]

    # 5. 年齢・月齢
    m_age = re.match(r'^(\d+)(歳|才)$', clean)
    if m_age:
        curr_age = int(m_age.group(1))
        unit = m_age.group(2)
        common_ages = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        sorted_ages = sorted([a for a in common_ages if a != curr_age], key=lambda x: abs(x - curr_age))
        return "scale_age", [f"{a}{unit}" for a in sorted_ages]

    m_mon = re.match(r'^(\d+)(ヶ月|カ月|か月|ヵ月)$', clean)
    if m_mon:
        curr_m = int(m_mon.group(1))
        unit = m_mon.group(2)
        common_ms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        sorted_ms = sorted([m for m in common_ms if m != curr_m], key=lambda x: abs(x - curr_m))
        return "scale_month", [f"{m}{unit}" for m in sorted_ms]

    # 6. 寸法 (cm, mm, m)
    m_len = re.match(r'^(\d+)(cm|mm|m)$', clean, re.IGNORECASE)
    if m_len:
        curr_len = int(m_len.group(1))
        unit = m_len.group(2).lower()
        if unit == "cm":
            c_lens = [5, 10, 15, 20, 30, 40, 50, 60, 100]
        elif unit == "mm":
            c_lens = [1, 2, 3, 5, 8, 10, 12, 15, 20]
        else:
            c_lens = [1, 2, 3, 5, 10]
        sorted_lens = sorted([l for l in c_lens if l != curr_len], key=lambda x: abs(x - curr_len))
        return "scale_len", [f"{l}{unit}" for l in sorted_lens]

    # 7. 重量・容量 (g, kg, ml, l, L)
    m_wt = re.match(r'^(\d+)(g|kg|ml|l|cc)$', clean, re.IGNORECASE)
    if m_wt:
        curr_wt = int(m_wt.group(1))
        unit = m_wt.group(2)
        if unit.lower() in ["g", "グラム"]:
            c_wts = [50, 100, 150, 200, 250, 300, 500, 1000]
        elif unit.lower() == "kg":
            c_wts = [1, 2, 3, 5, 10]
        else:
            c_wts = [100, 200, 300, 500, 1000]
        sorted_wts = sorted([w for w in c_wts if w != curr_wt], key=lambda x: abs(x - curr_wt))
        return "scale_weight", [f"{w}{unit}" for w in sorted_wts]

    return None
