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
from domain_attr_cost import match_domain_cost, is_incoherent_cost, get_fallback_cost_prefixes
from domain_attr_fashion import match_domain_fashion, is_incoherent_fashion, get_fallback_fashion_prefixes
from domain_attr_howto import match_domain_howto, is_incoherent_howto, get_fallback_howto_prefixes

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

    # 3. ① コスト・価格系属性モジュールによる排除判定
    if match_domain_cost(clean_s):
        if is_incoherent_cost(clean_p, clean_s):
            return True

    # 4. ② ファッション・美容系属性モジュールによる排除判定
    if match_domain_fashion(clean_s):
        if is_incoherent_fashion(clean_p, clean_s):
            return True

    # 5. ③ ハウツー・操作系属性モジュールによる排除判定
    if match_domain_howto(clean_s):
        if is_incoherent_howto(clean_p, clean_s):
            return True

    # 4. 比較・違い系サフィックスに対する不要な動詞・助詞混入の排除
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

    # ① コスト・価格系の場合
    if match_domain_cost(clean_s):
        return get_fallback_cost_prefixes()

    # ② ファッション・美容系の場合
    if match_domain_fashion(clean_s):
        return get_fallback_fashion_prefixes()

    # ③ ハウツー・操作系の場合
    if match_domain_howto(clean_s):
        return get_fallback_howto_prefixes()

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
