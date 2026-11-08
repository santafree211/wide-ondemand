# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_comparison.py
■ カテゴリ: Domain Attribute / ④ 比較・評価・選定・レビュー系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「比較」「ランキング」「違い」「選び方」「おすすめ」「口コミ」「評判」
    「レビュー」「メリット」「デメリット」「特徴」等の選定・評価属性に該当するか判定する。
  - 「作り方」「手順」「直し方」「設定」「接続」等の作業語や、「比較して 比較」等の重複語句の
    意味破綻を検知・排除する。
  - 比較・評価系に特化した高CTRキラープレフィックス（徹底、主要、コスパ、評判、満足度等）を供給する。
=============================================================================
"""

from typing import List

# 比較・評価・選定系サフィックス
COMPARISON_SUFFIXES = [
    "比較", "ランキング", "違い", "選び方", "おすすめ", "口コミ", "評判",
    "レビュー", "メリット", "デメリット", "特徴", "感想", "評価", "満足度"
]

# 比較系と衝突して意味破綻を起こす作業・工程・重複プレフィックス
COMPARISON_INCOHERENT_PREFIXES = [
    "作り方", "手順", "直し方", "修理", "設定", "接続", "解約", "結び方",
    "組み立て方", "落とし方", "英語", "意味", "とは", "画像", "wiki"
]

# 重複・助詞崩れを防ぐキーワード
COMPARISON_DUPLICATE_TOKENS = [
    "比較", "違い", "ランキング", "して", "する", "的", "級", "対象"
]

# 比較・選定系に最適化された高品質キラープレフィックス（30件）
COMPARISON_KILLER_PREFIXES = [
    "徹底", "主要", "人気", "最新", "定番", "おすすめ", "コスパ", "初心者", "プロ",
    "人気ブランド", "話題", "評判", "口コミ", "使いやすさ", "機能", "価格", "満足度",
    "耐久性", "シェア", "スペック", "性能", "デザイン", "失敗しない", "比較表",
    "総合", "項目別", "高評価", "実力", "注目", "定番メーカー"
]

def match_domain_comparison(suffix: str) -> bool:
    """
    指定されたsuffixが比較・評価・選定系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == c or s_last.endswith(c) for c in COMPARISON_SUFFIXES)

def is_incoherent_comparison(prefix: str, suffix: str) -> bool:
    """
    比較系サフィックスに対し、作業語や重複語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    clean_s = suffix.strip()

    # ハウツー・作業系の衝突排除
    for inc in COMPARISON_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True

    # 語幹重複（例: 「比較して 比較」「比較的 違い」）の排除
    if any(w in clean_p for w in COMPARISON_DUPLICATE_TOKENS) and any(w in clean_s for w in ["比較", "違い"]):
        return True

    return False

def get_fallback_comparison_prefixes() -> List[str]:
    """
    比較・選定系に最適なキラープレフィックスリストを返す。
    """
    return list(COMPARISON_KILLER_PREFIXES)
