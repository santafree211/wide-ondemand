# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_living.py
■ カテゴリ: Domain Attribute / ⑬ 住まい・暮らし・家事・ペット系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「掃除」「片付け」「収納」「洗濯」「引越し」「賃貸」「カビ」
    「汚れ」「消臭」「インテリア」「犬」「猫」「飼い方」「しつけ」「鳴き声」等の
    住生活・家事・ペット属性に該当するか判定する。
  - 「女子ウケ」「垢抜け」「合格率」「ダウンロード」「いつ飲む」「確定申告」「面接」等の
    外見・試験・IT・医療・就労系プレフィックスとの意味破綻（例: 「女子ウケ 掃除」「合格率 犬」等）を検知・排除する。
  - 暮らし・家事・ペット系に特化した高CTRキラープレフィックス（重曹、クエン酸、100均、しつけ方等）を供給する。
=============================================================================
"""

from typing import List

# 住まい・暮らし・家事・ペット系サフィックス
LIVING_SUFFIXES = [
    "掃除", "片付け", "収納", "洗濯", "引越し", "賃貸", "退去", "カビ",
    "汚れ", "消臭", "インテリア", "模様替え", "犬", "猫", "ペット",
    "飼い方", "しつけ", "鳴き声", "噛み癖", "抜け毛", "水回り"
]

# 暮らし・ペット系と衝突して意味破綻を起こす外見・試験・IT・就労系プレフィックス
LIVING_INCOHERENT_PREFIXES = [
    "女子ウケ", "垢抜け", "体型カバー", "合格率", "受験", "ダウンロード",
    "いつ飲む", "確定申告", "面接", "志望動機", "年収", "初任給", "初期化"
]

# 住まい・暮らし・ペット系に最適化された高品質キラープレフィックス（30件）
LIVING_KILLER_PREFIXES = [
    "簡単", "オキシクリーン", "クエン酸", "重曹", "ウタマロ", "100均", "ニトリ", "無印",
    "裏ワザ", "落ちない", "コツ", "やり方", "手順", "おすすめ", "人気", "便利グッズ",
    "失敗しない", "費用", "初心者", "しつけ方", "食べない", "噛む", "鳴く", "留守番",
    "病気", "予防", "対策", "時期", "頻度", "お手入れ"
]

def match_domain_living(suffix: str) -> bool:
    """
    指定されたsuffixが住まい・暮らし・家事・ペット系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == l or s_last.endswith(l) for l in LIVING_SUFFIXES)

def is_incoherent_living(prefix: str, suffix: str) -> bool:
    """
    暮らし・ペット系サフィックスに対し、無関係な試験語や外見語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in LIVING_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_living_prefixes() -> List[str]:
    """
    住まい・暮らし・家事・ペット系に最適なキラープレフィックスリストを返す。
    """
    return list(LIVING_KILLER_PREFIXES)
