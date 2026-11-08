# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_relationship.py
■ カテゴリ: Domain Attribute / ⑩ 恋愛・人間関係・対人心理系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「脈あり」「脈なし」「告白」「復縁」「接し方」「会話」「態度」
    「嫌われる」「好かれる」「上司」「義母」「旦那」「友達」「心理」「冷めた」「既読無視」等の
    対人関係・恋愛・心理属性に該当するか判定する。
  - 「定価」「最安値」「スペック」「型番」「設定」「接続」「修理」「作り方」「自作」等の
    商取引・機械・工作系プレフィックスとの意味破綻（例: 「定価 脈あり」「設定 復縁」等）を検知・排除する。
  - 恋愛・人間関係系に特化した高CTRキラープレフィックス（サイン、見分け方、LINE、男性心理等）を供給する。
=============================================================================
"""

from typing import List

# 恋愛・人間関係・対人心理系サフィックス
RELATIONSHIP_SUFFIXES = [
    "脈あり", "脈なし", "告白", "復縁", "接し方", "会話", "態度",
    "嫌われる", "好かれる", "上司", "部下", "後輩", "同僚", "義母",
    "姑", "旦那", "夫", "妻", "友達", "ママ友", "心理", "本音",
    "冷めた", "既読無視", "未読無視", "アプローチ", "好意"
]

# 恋愛・対人系と衝突して意味破綻を起こす商取引・機械・IT・工作系プレフィックス
RELATIONSHIP_INCOHERENT_PREFIXES = [
    "定価", "最安値", "格安", "割引", "セール", "スペック", "型番",
    "設定", "接続", "修理", "直し方", "作り方", "自作", "初期化",
    "ダウンロード", "解約", "賞味期限", "日持ち"
]

# 恋愛・人間関係系に最適化された高品質キラープレフィックス（30件）
RELATIONSHIP_KILLER_PREFIXES = [
    "サイン", "見分け方", "LINE", "男性心理", "女性心理", "特徴", "タイミング",
    "対処法", "諦める", "きっかけ", "本音", "態度", "行動", "好意", "職場",
    "返し方", "連絡", "心理", "逆転", "理由", "アドバイス", "NG行動",
    "距離感", "アプローチ", "引き際", "サイン見逃し", "相談", "体験談",
    "関係修復", "占い"
]

def match_domain_relationship(suffix: str) -> bool:
    """
    指定されたsuffixが恋愛・人間関係・心理系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == r or s_last.endswith(r) for r in RELATIONSHIP_SUFFIXES)

def is_incoherent_relationship(prefix: str, suffix: str) -> bool:
    """
    恋愛・対人系サフィックスに対し、機械・商取引語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in RELATIONSHIP_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_relationship_prefixes() -> List[str]:
    """
    恋愛・人間関係系に最適なキラープレフィックスリストを返す。
    """
    return list(RELATIONSHIP_KILLER_PREFIXES)
