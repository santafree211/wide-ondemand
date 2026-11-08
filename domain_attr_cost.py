# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_cost.py
■ カテゴリ: Domain Attribute / ① コスト・価格・相場系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワードの末尾が「値段」「費用」「相場」「料金」等のコスト属性に該当するか判定する。
  - 「やり方」「手順」「コツ」「道具」等のハウツー・作業系プレフィックスとの意味破綻を検知・排除する。
  - 価格属性に最適化されたキラープレフィックス（安い、高い、コスパ、最安値等）を供給する。
=============================================================================
"""

from typing import List

# 価格・費用系サフィックス（属性: コスト・金銭・数値）
COST_SUFFIXES = [
    "値段", "価格", "費用", "料金", "相場", "相場価格", "予算", "金額",
    "月額", "年額", "維持費", "見積もり", "手数料", "初期費用", "総額"
]

# 価格系と衝突して意味破綻を起こすハウツー・動作・工程系プレフィックス
COST_INCOHERENT_PREFIXES = [
    "やり方", "コツ", "手順", "方法", "失敗", "アレンジ", "注意点", "基本",
    "プロ", "初心者", "簡単", "自作", "道具", "時間", "メリット", "デメリット",
    "理由", "仕組み", "修理", "直し方", "作り方", "使い方"
]

# 価格系に最適化された高品質キラープレフィックス（25件以上）
COST_KILLER_PREFIXES = [
    "おすすめ", "人気", "安い", "高い", "コスパ", "相場", "比較", "選び方",
    "最新", "格安", "定価", "お得", "平均", "目安", "自前", "業務用", "高級",
    "最安値", "割引", "セール", "予算", "適正", "中古", "新品", "買い時",
    "節約", "還元", "キャンペーン", "底値", "実質"
]

def match_domain_cost(suffix: str) -> bool:
    """
    指定されたsuffix（または単語末尾）がコスト・価格系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == p or s_last.endswith(p) for p in COST_SUFFIXES)

def is_incoherent_cost(prefix: str, suffix: str) -> bool:
    """
    コスト・価格系サフィックスに対し、ハウツー・動作語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for h in COST_INCOHERENT_PREFIXES:
        if clean_p == h or clean_p.endswith(h) or clean_p.startswith(h):
            return True
    return False

def get_fallback_cost_prefixes() -> List[str]:
    """
    コスト・価格系に最適なキラープレフィックスリストを返す。
    """
    return list(COST_KILLER_PREFIXES)
