# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_procedure.py
■ カテゴリ: Domain Attribute / ⑨ 制度・手続き・学習・資格系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「申請」「免除」「控除」「手続き」「必要書類」「資格」「難易度」
    「合格率」「勉強法」「試験」「届出」「給付金」「確定申告」等の制度・学習属性に該当するか判定する。
  - 「おしゃれ」「かわいい」「女子ウケ」「美味しい」「自作」「工作」「修理」等の
    外見・グルメ・機械系プレフィックスとの意味破綻（例: 「女子ウケ 確定申告」「美味しい 資格」等）を検知・排除する。
  - 制度・手続き系に特化した高CTRキラープレフィックス（書き方、流れ、必要書類、独学等）を供給する。
=============================================================================
"""

from typing import List

# 制度・手続き・資格・学習系サフィックス
PROCEDURE_SUFFIXES = [
    "申請", "免除", "控除", "手続き", "必要書類", "資格", "難易度",
    "合格率", "勉強法", "試験", "期限", "条件", "更新", "届出",
    "給付金", "確定申告", "補助金", "申告", "受給", "更新手続き"
]

# 制度系と衝突して意味破綻を起こす外見・グルメ・工作系プレフィックス
PROCEDURE_INCOHERENT_PREFIXES = [
    "おしゃれ", "かわいい", "女子ウケ", "垢抜け", "体型カバー",
    "美味しい", "隠し味", "黄金比", "日持ち", "賞味期限", "自作",
    "工作", "修理", "直し方", "壊れた", "解約"
]

# 制度・手続き系に最適化された高品質キラープレフィックス（30件）
PROCEDURE_KILLER_PREFIXES = [
    "書き方", "流れ", "いつまで", "必要書類", "対象者", "条件", "期限", "どこで",
    "独学", "テキスト", "スケジュール", "合格率", "難易度", "過去問", "勉強時間",
    "おすすめ", "初心者", "注意点", "失敗", "理由", "免除", "いくら", "シミュレーション",
    "オンライン", "郵送", "窓口", "記入例", "添付書類", "控除額", "確定申告"
]

def match_domain_procedure(suffix: str) -> bool:
    """
    指定されたsuffixが制度・手続き系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == p or s_last.endswith(p) for p in PROCEDURE_SUFFIXES)

def is_incoherent_procedure(prefix: str, suffix: str) -> bool:
    """
    制度系サフィックスに対し、外見・グルメ語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in PROCEDURE_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_procedure_prefixes() -> List[str]:
    """
    制度・手続き系に最適なキラープレフィックスリストを返す。
    """
    return list(PROCEDURE_KILLER_PREFIXES)
