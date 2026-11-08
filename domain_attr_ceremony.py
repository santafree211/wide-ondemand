# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_ceremony.py
■ カテゴリ: Domain Attribute / ⑫ 冠婚葬祭・マナー・贈答系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「結婚式」「葬式」「お通夜」「香典」「祝儀」「お祝い」「プレゼント」
    「手土産」「お中元」「お歳暮」「内祝い」「のし」「マナー」等の礼儀・儀礼属性に該当するか判定する。
  - 「安い」「最安値」「格安」「定価」「壊れた」「修理」「自作」「初期化」等の
    不謹慎・機械工作系プレフィックスとの意味破綻（例: 「最安値 香典」「格安 祝儀」等）を検知・排除する。
  - 冠婚葬祭・贈答系に特化した高CTRキラープレフィックス（相場、包み方、渡し方、マナー等）を供給する。
=============================================================================
"""

from typing import List

# 冠婚葬祭・マナー・贈答系サフィックス
CEREMONY_SUFFIXES = [
    "結婚式", "葬式", "お通夜", "告別式", "香典", "祝儀", "ご祝儀",
    "お祝い", "プレゼント", "手土産", "お中元", "お歳暮", "内祝い",
    "のし", "水引", "返礼品", "マナー", "引き出物", "香典返し"
]

# 冠婚葬祭系と衝突して不謹慎・意味破綻を起こすプレフィックス
CEREMONY_INCOHERENT_PREFIXES = [
    "安い", "最安値", "格安", "定価", "セール", "割引", "壊れた",
    "修理", "直し方", "自作", "工作", "初期化", "設定", "接続"
]

# 冠婚葬祭・贈答系に最適化された高品質キラープレフィックス（30件）
CEREMONY_KILLER_PREFIXES = [
    "相場", "金額", "書き方", "包み方", "渡し方", "服装", "マナー", "NG",
    "タブー", "いつ渡す", "のし", "お返し", "失礼", "関係性", "友人", "親族",
    "上司", "連名", "お礼", "添え状", "選び方", "喜ばれる", "おすすめ", "人気",
    "年代別", "タイミング", "郵送", "辞退", "ふくさ", "表書き"
]

def match_domain_ceremony(suffix: str) -> bool:
    """
    指定されたsuffixが冠婚葬祭・マナー系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == c or s_last.endswith(c) for c in CEREMONY_SUFFIXES)

def is_incoherent_ceremony(prefix: str, suffix: str) -> bool:
    """
    冠婚葬祭系サフィックスに対し、不謹慎な格安語や機械語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in CEREMONY_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_ceremony_prefixes() -> List[str]:
    """
    冠婚葬祭・贈答系に最適なキラープレフィックスリストを返す。
    """
    return list(CEREMONY_KILLER_PREFIXES)
