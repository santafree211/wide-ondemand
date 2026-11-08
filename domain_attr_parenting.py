# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_parenting.py
■ カテゴリ: Domain Attribute / ⑮ 子育て・育児・知育系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「離乳食」「夜泣き」「トイトレ」「イヤイヤ期」「授乳」「ミルク」
    「保育園」「幼稚園」「知育玩具」「ランドセル」「習い事」「おねしょ」「ベビーカー」等の
    子育て・育児・知育属性に該当するか判定する。
  - 「女子ウケ」「確定申告」「ダウンロード」「スペック」「型番」「初期化」「年収」等の
    外見・税務・IT・就労系プレフィックスとの意味破綻（例: 「女子ウケ 離乳食」「確定申告 夜泣き」等）を検知・排除する。
  - 育児系に特化した超高需要キラープレフィックス（いつから、進め方、食べない、寝ない等）を供給する。
=============================================================================
"""

from typing import List

# 子育て・育児・知育系サフィックス
PARENTING_SUFFIXES = [
    "離乳食", "夜泣き", "トイトレ", "イヤイヤ期", "授乳", "ミルク", "卒乳",
    "断乳", "保育園", "幼稚園", "知育玩具", "ランドセル", "習い事",
    "おねしょ", "反抗期", "名付け", "出産準備", "ベビーカー", "抱っこ紐",
    "チャイルドシート", "幼児食", "寝かしつけ"
]

# 育児系と衝突して意味破綻を起こす外見・税務・IT・就労系プレフィックス
PARENTING_INCOHERENT_PREFIXES = [
    "女子ウケ", "垢抜け", "体型カバー", "確定申告", "ダウンロード", "スペック",
    "型番", "初期化", "年収", "初任給", "ボーナス", "修理", "解約"
]

# 子育て・育児系に最適化された高品質キラープレフィックス（30件）
PARENTING_KILLER_PREFIXES = [
    "いつから", "進め方", "スケジュール", "食べない", "寝ない", "対策", "時期",
    "月齢", "年齢別", "イライラ", "便利グッズ", "コツ", "ステップ", "おすすめ",
    "人気", "失敗", "注意点", "選び方", "準備", "期間", "量", "回数", "卒業",
    "ランキング", "手作り", "市販", "先輩ママ", "口コミ", "理由", "相談"
]

def match_domain_parenting(suffix: str) -> bool:
    """
    指定されたsuffixが子育て・育児系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == p or s_last.endswith(p) for p in PARENTING_SUFFIXES)

def is_incoherent_parenting(prefix: str, suffix: str) -> bool:
    """
    育児系サフィックスに対し、IT・税務・外見語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in PARENTING_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_parenting_prefixes() -> List[str]:
    """
    子育て・育児系に最適なキラープレフィックスリストを返す。
    """
    return list(PARENTING_KILLER_PREFIXES)
