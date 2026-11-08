# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: validator_semantic_coherence.py
■ カテゴリ: Validation / 意味整合性・自然言語構文バリデーター
■ 責務・役割（Single Responsibility）:
  - 「〇〇 [B]」等のキーワード結合時に、文脈上・文法上破綻した不自然な組み合わせ（検索意図ゼロ）を排除判定する。
  - 例1: 価格・相場系サフィックス（「値段」「費用」「相場」「料金」等）に対する
         「やり方」「手順」「コツ」「失敗」等のハウツー修飾の衝突を排除。
  - 例2: 感情・評価系サフィックス（「デメリット」「メリット」「理由」等）に対する
         無意味な名詞修飾・二重否定の衝突を排除。
  - 例3: サジェストから得られた単語のうち、文頭と文末で同じ単語が重複する構文破壊（例: 「値段はいくら 値段」）を排除。
=============================================================================
"""

import re
from typing import List

# 価格・費用系サフィックス（属性: コスト・数値）
PRICE_COST_SUFFIXES = [
    "値段", "価格", "費用", "料金", "相場", "相場価格", "予算", "金額", "月額", "年額"
]

# ハウツー・動作・工程系プレフィックス（属性: アクション・方法）
HOWTO_ACTION_PREFIXES = [
    "やり方", "コツ", "手順", "方法", "失敗", "アレンジ", "注意点", "基本",
    "プロ", "初心者", "簡単", "自作", "道具", "時間", "メリット", "デメリット", "理由"
]

# 価格・費用系と相性の良い自然な前置・展開語
PRICE_NATURAL_PREFIXES = [
    "相場", "安い", "高い", "おすすめ", "人気", "コスパ", "比較", "選び方",
    "平均", "目安", "定価", "割引", "セール", "お得", "最安値", "格安"
]

# 比較・ランキング系サフィックス
COMPARISON_SUFFIXES = [
    "比較", "ランキング", "一覧", "まとめ", "違い"
]

def is_semantically_incoherent(prefix: str, suffix: str) -> bool:
    """
    prefix と suffix を結合したキーワード（f"{prefix} {suffix}"）が
    日本語の意味として破綻している（検索需要が実質ゼロ）かどうかを判定する。
    破綻している場合は True、自然な場合は False を返す。
    """
    clean_p = prefix.strip()
    clean_s = suffix.strip()

    if not clean_p or not clean_s:
        return False

    # 1. 完全同一語・重複結合の排除（例: 「値段 値段」「比較 比較」「珈琲 珈琲」）
    if clean_p == clean_s or clean_p in clean_s or clean_s in clean_p:
        return True

    # 2. 接尾辞の末尾語（メインの名詞属性）を取得
    s_tokens = clean_s.split()
    s_last = s_tokens[-1]

    # 3. 価格・費用系サフィックスに対するハウツー動詞結合の排除
    # 例: 「やり方 珈琲値段」「手順 値段」「コツ 費用」
    is_price_suffix = any(s_last == p or s_last.endswith(p) for p in PRICE_COST_SUFFIXES)
    if is_price_suffix:
        # ハウツー系プレフィックスは意味破綻
        for h in HOWTO_ACTION_PREFIXES:
            if clean_p == h or clean_p.endswith(h) or clean_p.startswith(h):
                return True

    # 4. 比較・違い系サフィックスに対する不要な動詞・助詞混入の排除
    # 例: 「比較して 比較」「比較的 意味 比較」「比較対象 比較」
    is_comp_suffix = any(s_last == c or s_last.endswith(c) for c in COMPARISON_SUFFIXES)
    if is_comp_suffix:
        if any(w in clean_p for w in ["比較", "違い", "ランキング", "して", "する", "的", "級"]):
            return True

    # 5. 文法・品詞的なゴミ（英語の文法用語、活用形崩れ等）の排除
    grammatical_junk = ["英語", "意味", "とは", "画像", "wiki", "一覧", "例文", "類語"]
    if clean_p in grammatical_junk:
        return True

    return False

def get_fallback_prefixes_for_suffix(suffix: str) -> List[str]:
    """
    suffix（後固定部）の持つ意味属性に合わせて、
    意味破綻しない自然なバックアップ展開候補リストを動的に選定して返す。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s

    # 価格・費用系の場合
    if any(s_last == p or s_last.endswith(p) for p in PRICE_COST_SUFFIXES):
        return [
            "おすすめ", "人気", "安い", "高い", "コスパ", "相場", "比較", "選び方",
            "最新", "格安", "定価", "お得", "平均", "目安", "自前", "業務用", "高級",
            "最安値", "割引", "セール", "予算", "適正", "中古", "新品", "買い時",
            "維持費", "総額", "内訳", "節約"
        ]

    # 比較・違い系の場合
    if any(s_last == c or s_last.endswith(c) for c in COMPARISON_SUFFIXES):
        return [
            "おすすめ", "人気", "最新", "プロ", "定番", "安い", "コスパ",
            "初心者", "評判", "口コミ", "徹底", "主要", "人気ブランド", "話題",
            "特徴", "性能", "使いやすさ", "機能", "メリット", "デメリット",
            "デザイン", "価格", "満足度", "耐久性", "シェア", "スペック"
        ]

    # デフォルト（道具・製品・一般対象）
    return [
        "おすすめ", "人気", "やり方", "コツ", "選び方", "種類", "基本",
        "簡単", "初心者", "プロ", "注意点", "失敗", "道具", "費用", "時間",
        "最新", "定番", "便利", "仕組み", "メリット", "デメリット",
        "アレンジ", "長持ち", "お手入れ", "自作", "安全"
    ]
