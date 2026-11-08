# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_money.py
■ カテゴリ: Domain Attribute / ⑭ 金融・投資・資産運用・保険・クレカ系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「NISA」「つみたてNISA」「iDeCo」「投資信託」「配当金」「株主優待」
    「住宅ローン」「金利」「生命保険」「医療保険」「クレジットカード」「クレカ」「限度額」「審査」等の
    金融・投資・資産・信用属性に該当するか判定する。
  - 「作り方」「美味しい」「隠し味」「女子ウケ」「垢抜け」「修理」「壊れた」「自作」等の
    料理・外見・機械工作系プレフィックスとの意味破綻（例: 「作り方 NISA」「女子ウケ 住宅ローン」等）を検知・排除する。
  - 金融・マネー系に特化した超高単価キラープレフィックス（始め方、利回り、元本割れ、シミュレーション等）を供給する。
=============================================================================
"""

from typing import List

# 金融・投資・資産運用・保険・クレカ系サフィックス
MONEY_SUFFIXES = [
    "NISA", "つみたてNISA", "新NISA", "iDeCo", "投資信託", "配当金",
    "株主優待", "住宅ローン", "金利", "生命保険", "医療保険", "がん保険",
    "自動車保険", "学資保険", "クレジットカード", "クレカ", "限度額",
    "キャッシング", "審査", "カードローン", "暗号資産", "仮想通貨", "FX"
]

# 金融系と衝突して意味破綻を起こす料理・外見・工作系プレフィックス
MONEY_INCOHERENT_PREFIXES = [
    "作り方", "美味しい", "隠し味", "黄金比", "女子ウケ", "垢抜け",
    "体型カバー", "修理", "直し方", "壊れた", "自作", "工作", "日持ち",
    "賞味期限", "下ごしらえ", "着回し"
]

# 金融・マネー系に最適化された高品質キラープレフィックス（30件）
MONEY_KILLER_PREFIXES = [
    "始め方", "初心者", "シミュレーション", "利回り", "元本割れ", "おすすめ銘柄", "還元率",
    "審査落ち", "控除", "非課税", "デメリット", "リスク", "おすすめ", "人気", "比較",
    "いくらから", "毎月", "上限", "引き落とし", "ポイント", "年会費", "繰り上げ返済",
    "見直し", "相談", "複利", "確定拠出年金", "選び方", "手数料", "銘柄", "お得"
]

def match_domain_money(suffix: str) -> bool:
    """
    指定されたsuffixが金融・資産運用系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == m or s_last.endswith(m) for m in MONEY_SUFFIXES)

def is_incoherent_money(prefix: str, suffix: str) -> bool:
    """
    金融系サフィックスに対し、料理・外見・工作語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in MONEY_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_money_prefixes() -> List[str]:
    """
    金融・資産運用系に最適なキラープレフィックスリストを返す。
    """
    return list(MONEY_KILLER_PREFIXES)
