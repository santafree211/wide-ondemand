# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_gourmet.py
■ カテゴリ: Domain Attribute / ⑥ 飲食・料理・グルメ系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「レシピ」「味」「食べ方」「飲み方」「焼き方」「茹で方」
    「保存方法」「賞味期限」「日持ち」「腐る」「隠し味」等の料理・飲食属性に該当するか判定する。
  - 「設定」「接続」「修理」「直し方」「女子ウケ」「垢抜け」「申請」「解約」「初期化」等の
    機械・外見・制度系プレフィックスとの意味破綻（例: 「設定 レシピ」「接続 食べ方」等）を検知・排除する。
  - 料理・グルメ系に特化した高CTRキラープレフィックス（美味しい、黄金比、アレンジ、時短等）を供給する。
=============================================================================
"""

from typing import List

# 飲食・料理・グルメ系サフィックス
GOURMET_SUFFIXES = [
    "レシピ", "味", "食べ方", "飲み方", "焼き方", "茹で方", "炒め方",
    "保存方法", "賞味期限", "消費期限", "腐る", "日持ち", "献立",
    "具材", "隠し味", "下処理", "下ごしらえ", "付け合わせ"
]

# グルメ系と衝突して意味破綻を起こす機械・外見・制度系プレフィックス
GOURMET_INCOHERENT_PREFIXES = [
    "設定", "接続", "修理", "直し方", "女子ウケ", "垢抜け", "体型カバー",
    "申請", "解約", "初期化", "再起動", "エラー", "スペック", "型番", "免除"
]

# 料理・グルメ系に最適化された高品質キラープレフィックス（30件）
GOURMET_KILLER_PREFIXES = [
    "美味しい", "簡単", "時短", "人気", "おすすめ", "アレンジ", "プロ",
    "本格", "黄金比", "冷凍", "日持ち", "代用", "下ごしらえ", "失敗しない",
    "基本", "定番", "子ども", "お弁当", "フライパン", "レンジ", "大量消費",
    "作り置き", "ヘルシー", "節約", "初心者", "秘訣", "合わせ調味料", "絶品",
    "栄養", "保存"
]

def match_domain_gourmet(suffix: str) -> bool:
    """
    指定されたsuffixが飲食・グルメ系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == g or s_last.endswith(g) for f in GOURMET_SUFFIXES for g in [f])

def is_incoherent_gourmet(prefix: str, suffix: str) -> bool:
    """
    グルメ系サフィックスに対し、機械・外見語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in GOURMET_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_gourmet_prefixes() -> List[str]:
    """
    飲食・グルメ系に最適なキラープレフィックスリストを返す。
    """
    return list(GOURMET_KILLER_PREFIXES)
