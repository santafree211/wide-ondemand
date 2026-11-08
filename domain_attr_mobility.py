# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_mobility.py
■ カテゴリ: Domain Attribute / ⑯ 自動車・バイク・カーライフ系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「車検」「タイヤ」「燃費」「オイル交換」「下取り」「買取」
    「擦った」「傷」「へこみ」「洗車」「コーティング」「工賃」「ドラレコ」等の
    自動車・バイク・車両メンテナンス属性に該当するか判定する。
  - 「美味しい」「隠し味」「女子ウケ」「離乳食」「夜泣き」「確定申告」「脈あり」「いつ飲む」等の
    料理・育児・税務・恋愛・健康系プレフィックスとの意味破綻（例: 「美味しい タイヤ」「離乳食 車検」等）を検知・排除する。
  - カーライフ・車両系に特化した超高需要キラープレフィックス（費用、相場、交換時期、工賃等）を供給する。
=============================================================================
"""

from typing import List

# 自動車・バイク・カーライフ系サフィックス
MOBILITY_SUFFIXES = [
    "車検", "タイヤ", "燃費", "オイル交換", "下取り", "買取", "新車",
    "中古車", "擦った", "傷", "へこみ", "洗車", "コーティング", "ドラレコ",
    "工賃", "カーナビ", "バッテリー交換", "パンク", "板金", "納車", "愛車"
]

# 車両系と衝突して意味破綻を起こす料理・育児・税務・恋愛・健康系プレフィックス
MOBILITY_INCOHERENT_PREFIXES = [
    "美味しい", "隠し味", "黄金比", "女子ウケ", "垢抜け", "離乳食", "夜泣き",
    "トイトレ", "確定申告", "免除", "脈あり", "復縁", "いつ飲む", "賞味期限", "日持ち"
]

# 自動車・バイク・カーライフ系に最適化された高品質キラープレフィックス（30件）
MOBILITY_KILLER_PREFIXES = [
    "費用", "相場", "時期", "寿命", "交換時期", "おすすめ", "自分で", "見積もり",
    "査定", "維持費", "工賃", "DIY", "安い時期", "初心者", "注意点", "失敗",
    "長持ち", "選び方", "手順", "比較", "期間", "頻度", "必要", "持ち込み",
    "修理代", "買い替え", "車検切れ", "メリット", "デメリット", "安く抑える"
]

def match_domain_mobility(suffix: str) -> bool:
    """
    指定されたsuffixが自動車・バイク系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == m or s_last.endswith(m) for m in MOBILITY_SUFFIXES)

def is_incoherent_mobility(prefix: str, suffix: str) -> bool:
    """
    車両系サフィックスに対し、料理・育児・恋愛語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in MOBILITY_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_mobility_prefixes() -> List[str]:
    """
    自動車・バイク系に最適なキラープレフィックスリストを返す。
    """
    return list(MOBILITY_KILLER_PREFIXES)
