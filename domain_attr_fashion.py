# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_fashion.py
■ カテゴリ: Domain Attribute / ② ファッション・美容・身だしなみ系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「ファッション」「コーデ」「服装」「着こなし」「メイク」「髪型」等の
    外見・アピアランス属性に該当するか判定する。
  - 「やり方」「仕組み」「修理」「道具」「接続」「設定」「時間」等の機械・工作系語句との
    意味破綻を検知・排除する。
  - ファッション・美容に特化した高CTRキラープレフィックス（女子ウケ、垢抜け、プチプラ等）を供給する。
=============================================================================
"""

from typing import List

# ファッション・美容系サフィックス
FASHION_SUFFIXES = [
    "ファッション", "メンズファッション", "レディースファッション",
    "コーデ", "コーディネート", "服装", "着こなし", "身だしなみ",
    "メイク", "コスメ", "髪型", "ヘアスタイル", "ヘアセット",
    "スキンケア", "香水", "フレグランス", "スタイリング", "シルエット"
]

# ファッション系と衝突して意味破綻を起こす機械・工作・道具系プレフィックス
FASHION_INCOHERENT_PREFIXES = [
    "やり方", "仕組み", "修理", "直し方", "道具", "時間", "接続", "設定",
    "壊れた", "解約", "自作", "工作", "エラー", "便利", "機能", "スペック"
]

# ファッション・美容系に最適化された高品質キラープレフィックス（30件）
FASHION_KILLER_PREFIXES = [
    "おすすめ", "人気", "女子ウケ", "垢抜け", "きれいめ", "カジュアル",
    "プチプラ", "ブランド", "ダサい", "モテる", "定番", "初心者", "通販",
    "失敗しない", "体型カバー", "シンプル", "トレンド", "最新", "コスパ",
    "着回し", "高見え", "上品", "清潔感", "おしゃれ", "大人", "オフィスカジュアル",
    "休日", "ストリート", "年代別", "高級感"
]

def match_domain_fashion(suffix: str) -> bool:
    """
    指定されたsuffixがファッション・美容系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == f or s_last.endswith(f) for f in FASHION_SUFFIXES)

def is_incoherent_fashion(prefix: str, suffix: str) -> bool:
    """
    ファッション系サフィックスに対し、機械・工作語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in FASHION_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_fashion_prefixes() -> List[str]:
    """
    ファッション・美容系に最適なキラープレフィックスリストを返す。
    """
    return list(FASHION_KILLER_PREFIXES)
