# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_trouble.py
■ カテゴリ: Domain Attribute / ⑤ トラブル・悩み・不具合・リスク系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「壊れた」「動かない」「エラー」「治らない」「痛い」「後悔」
    「失敗」「理由」「原因」「消えた」「つながらない」等のトラブル・不具合属性に該当するか判定する。
  - 「おすすめ」「人気」「定番」「作り方」「定価」「最安値」「女子ウケ」「かわいい」等の
    不謹慎・的外れなプレフィックスとの意味破綻（例: 「おすすめ 壊れた」「定価 動かない」等）を検知・排除する。
  - トラブル系に特化した高CTR・救済キラープレフィックス（対処法、原因、解決、応急処置等）を供給する。
=============================================================================
"""

from typing import List

# トラブル・悩み・不具合系サフィックス
TROUBLE_SUFFIXES = [
    "壊れた", "動かない", "エラー", "治らない", "痛い", "後悔", "失敗",
    "理由", "原因", "なぜ", "危険", "落ちる", "外れる", "消えた",
    "つながらない", "起動しない", "フリーズ", "遅い", "重い", "不具合"
]

# トラブル系と衝突して意味破綻・不謹慎となるプレフィックス
TROUBLE_INCOHERENT_PREFIXES = [
    "おすすめ", "人気", "定番", "作り方", "定価", "最安値", "格安", "割引",
    "セール", "女子ウケ", "かわいい", "おしゃれ", "きれいめ", "モテる",
    "プチプラ", "高級", "業務用", "長持ち"
]

# トラブル・悩み系に最適化された高品質キラープレフィックス（30件）
TROUBLE_KILLER_PREFIXES = [
    "対処法", "解決", "解決策", "応急処置", "治し方", "直し方", "原因", "理由",
    "防ぐ", "予防", "問い合わせ", "サポート", "保証", "修理", "初期化",
    "再起動", "復旧", "交換", "買い替え", "簡単", "自分で", "一人で",
    "即効", "すぐできる", "安全", "注意点", "確認", "チェック", "無料", "症状別"
]

def match_domain_trouble(suffix: str) -> bool:
    """
    指定されたsuffixがトラブル・悩み系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == t or s_last.endswith(t) for t in TROUBLE_SUFFIXES)

def is_incoherent_trouble(prefix: str, suffix: str) -> bool:
    """
    トラブル系サフィックスに対し、おすすめ・外見語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in TROUBLE_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_trouble_prefixes() -> List[str]:
    """
    トラブル・悩み系に最適なキラープレフィックスリストを返す。
    """
    return list(TROUBLE_KILLER_PREFIXES)
