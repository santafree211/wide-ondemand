# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: engine_context_harmonizer.py
■ カテゴリ: Engine / シード文脈・相互整合エンジン（Contextual Harmonizer）
■ 責務・役割（Single Responsibility）:
  - シードキーワードの [A] と [B] から「シード全体の共通文脈（テーマ）」を統合特定する。
  - 軸①（[A] 〇〇）の展開時、Bの文脈（食味、価格、汚れ、初心者等）に合致した語句を優先注入し、
    無関係な別ジャンル（ウイスキー、工作等）への脱線を遮断する。
  - 軸②（〇〇 [B]）の展開時、Aのドメイン（魚類、飲料、家電、衣類等）に完全に整合した
    同族エンティティを最優先でロック・供給する。
=============================================================================
"""

from typing import Dict, List, Any, Optional
from engine_semantic_family import detect_semantic_family

# 飲食・食味・調理系サフィックス群
COOKING_INTENTS = [
    "食べる", "飲む", "料理", "レシピ", "味", "美味しい", "臭い", "刺身", "調理", "下処理"
]

# 価格・コスト系サフィックス群
COST_INTENTS = [
    "値段", "価格", "費用", "料金", "相場", "予算", "月額", "安い", "高い", "コスパ"
]

# 汚れ・除去系サフィックス群
CLEANING_INTENTS = [
    "汚れ", "シミ", "カビ", "落とし方", "消し方", "黄ばみ", "黒ずみ", "臭い"
]

# トラブル・不調系サフィックス群
TROUBLE_INTENTS = [
    "おかしい", "変", "動かない", "壊れた", "エラー", "重い", "遅い", "原因", "対処法"
]

def analyze_seed_context(slot_a: str, slot_b: str) -> Dict[str, Any]:
    """
    slot_a と slot_b を掛け合わせ、シード全体の統合文脈（テーマ）を判定する。
    """
    clean_a = slot_a.strip()
    clean_b = slot_b.strip()

    # 1. slot_a のドメイン特定（同族判定エンジンより）
    family_res = detect_semantic_family(clean_a)
    domain_a = family_res[0] if family_res else "general"

    # 2. slot_b の意図カテゴリ特定
    intent_b = "general"
    if any(clean_b == c or clean_b.endswith(c) for c in COOKING_INTENTS):
        intent_b = "cooking_eating"
    elif any(clean_b == co or clean_b.endswith(co) for co in COST_INTENTS):
        intent_b = "cost_pricing"
    elif any(clean_b == cl or clean_b.endswith(cl) for cl in CLEANING_INTENTS):
        intent_b = "cleaning_removal"
    elif any(clean_b == tr or clean_b.endswith(tr) for tr in TROUBLE_INTENTS):
        intent_b = "trouble_fault"

    # 3. 共通テーマ（コンテキスト）の決定
    combined_context = f"{domain_a}_{intent_b}"

    return {
        "slot_a": clean_a,
        "slot_b": clean_b,
        "domain_a": domain_a,
        "intent_b": intent_b,
        "context": combined_context,
        "family_members_a": family_res[1] if family_res else []
    }

def is_contextually_incoherent(target_kw: str, context_info: Dict[str, Any]) -> bool:
    """
    シードの統合文脈に対して、候補キーワードが文脈脱線（別ジャンルへの誤爆）を起こしていないか判定する。
    """
    context = context_info.get("context", "")
    t = target_kw.strip()

    # 魚 × 調理・食味 の文脈でウイスキー（お酒）系へ脱線した場合
    if "fish" in context or context_info.get("intent_b") == "cooking_eating":
        whisky_words = ["ウイスキー", "リーガル", "ミズナラ", "12年", "18年", "水割り", "ハイボール"]
        if any(w in t for w in whisky_words):
            return True

    # 汚れ・染み × 除去 の文脈でゴミ単語の排除
    if context_info.get("intent_b") == "cleaning_removal":
        if any(w in t for w in ["いんく", "代わり", "代用", "作り方"]):
            return True

    return False

def get_harmonized_axis1_terms(context_info: Dict[str, Any]) -> List[str]:
    """
    シード全体の文脈に基づき、軸①（[A] 〇〇）に優先注入すべき整合トピックリストを返す。
    """
    domain = context_info["domain_a"]
    intent = context_info["intent_b"]

    # 魚・食材 × 食べる・調理 の場合
    if domain in ["fish", "dish", "sweet", "staple"] or intent == "cooking_eating":
        return [
            "刺身", "臭い", "寄生虫", "毒", "旬", "レシピ", "料理", "下処理",
            "持ち帰り方", "保存", "味", "洗い", "ムニエル", "塩焼き", "煮付け",
            "生食", "食べ方", "美味しい", "フライ", "カルパッチョ", "人気", "おすすめ"
        ]

    # 飲料・食品 × 価格・コスト の場合
    if domain in ["health_drink", "sweet", "staple"] or intent == "cost_pricing":
        return [
            "相場", "安い", "コスパ", "おすすめ", "定価", "平均", "割引", "最安値",
            "通販", "業務用", "定期便", "比較", "選び方", "賞味期限", "人気"
        ]

    # 汚れ・染み × 除去 の場合
    if intent == "cleaning_removal" or "汚れ" in context_info["slot_b"]:
        return [
            "落とし方", "消し方", "服", "シャツ", "手", "壁紙", "オキシクリーン",
            "ウタマロ", "重曹", "除光液", "エタノール", "時間が経った", "落ちない"
        ]

    return []

def get_harmonized_axis2_entities(context_info: Dict[str, Any]) -> List[str]:
    """
    シード全体の文脈に基づき、軸②（〇〇 [B]）に優先注入すべき同族エンティティリストを返す。
    """
    # Aの同族リストが存在する場合はそれを最優先返却（完全ロック）
    members = context_info.get("family_members_a", [])
    if members:
        return list(members)

    # 汚れ系の場合の他の汚れ種類
    if context_info["intent_b"] == "cleaning_removal":
        return [
            "油", "泥", "サビ", "皮脂", "血液", "カビ", "黄ばみ", "黒ずみ",
            "食べこぼし", "コーヒー", "醤油", "ボールペン", "ファンデーション",
            "ワイン", "ヤニ", "水垢", "茶渋", "黒カビ"
        ]

    return []
