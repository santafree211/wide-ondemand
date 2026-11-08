# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_health.py
■ カテゴリ: Domain Attribute / ⑦ 健康・体質・医療・ヘルスケア系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「効果」「効能」「副作用」「症状」「治す」「ダイエット」「痩せる」
    「カロリー」「糖質」「栄養」「改善」等のヘルスケア・身体属性に該当するか判定する。
  - 「設定」「接続」「自作」「ダウンロード」「初期化」「修理」「定価」「格安」等の
    IT・工作・商取引系プレフィックスとの意味破綻（例: 「設定 効果」「接続 症状」等）を検知・排除する。
  - ヘルスケア系に特化した高CTRキラープレフィックス（いつ飲む、タイミング、期間、即効性等）を供給する。
=============================================================================
"""

from typing import List

# 健康・体質・医療系サフィックス
HEALTH_SUFFIXES = [
    "効果", "効能", "副作用", "症状", "治す", "ダイエット", "痩せる",
    "太る", "カロリー", "糖質", "栄養", "筋トレ", "ストレッチ", "改善",
    "予防", "体質改善", "免疫力", "代謝", "健康効果"
]

# 健康系と衝突して意味破綻を起こすIT・工作・商取引系プレフィックス
HEALTH_INCOHERENT_PREFIXES = [
    "設定", "接続", "自作", "ダウンロード", "初期化", "再起動", "修理",
    "定価", "最安値", "格安", "セール", "割引", "スペック", "型番"
]

# ヘルスケア・体質系に最適化された高品質キラープレフィックス（30件）
HEALTH_KILLER_PREFIXES = [
    "いつ飲む", "タイミング", "期間", "毎日", "飲み過ぎ", "危険", "即効性", "目安",
    "効果的な飲み方", "おすすめ", "人気", "注意点", "デメリット", "理由", "食事",
    "運動", "朝", "夜", "寝る前", "空腹時", "継続", "口コミ", "変化", "女性",
    "男性", "妊娠中", "安全", "副作用", "摂取量", "ビフォーアフター"
]

def match_domain_health(suffix: str) -> bool:
    """
    指定されたsuffixが健康・体質系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == h or s_last.endswith(h) for h in HEALTH_SUFFIXES)

def is_incoherent_health(prefix: str, suffix: str) -> bool:
    """
    健康系サフィックスに対し、IT・工作語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in HEALTH_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_health_prefixes() -> List[str]:
    """
    健康・体質系に最適なキラープレフィックスリストを返す。
    """
    return list(HEALTH_KILLER_PREFIXES)
