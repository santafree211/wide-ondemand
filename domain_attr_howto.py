# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_howto.py
■ カテゴリ: Domain Attribute / ③ ハウツー・操作・工程・作業系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「作り方」「使い方」「始め方」「直し方」「設定」「接続」等の
    工程・操作・作業属性に該当するか判定する。
  - 「安い」「高い」「定価」「最安値」「格安」「女子ウケ」「ダサい」等の価格・外見系語句との
    意味破綻（例: 「安い 作り方」「最安値 使い方」等）を検知・排除する。
  - ハウツー・作業系に特化した高需要キラープレフィックス（簡単、初心者、コツ、失敗しない等）を供給する。
=============================================================================
"""

from typing import List

# ハウツー・操作・作業系サフィックス
HOWTO_SUFFIXES = [
    "作り方", "使い方", "始め方", "やり方", "手順", "方法",
    "直し方", "修理", "設定", "接続", "登録", "解約", "結び方",
    "落とし方", "洗い方", "外し方", "付け方", "巻き方", "組み立て方"
]

# ハウツー系と衝突して意味破綻を起こす価格・外見系プレフィックス
HOWTO_INCOHERENT_PREFIXES = [
    "安い", "高い", "定価", "最安値", "格安", "割引", "セール", "お得",
    "相場", "費用", "料金", "予算", "女子ウケ", "ダサい", "垢抜け",
    "体型カバー", "きれいめ", "カジュアル", "ストリート"
]

# ハウツー・作業系に最適化された高品質キラープレフィックス（30件）
HOWTO_KILLER_PREFIXES = [
    "簡単", "初心者", "コツ", "手順", "失敗しない", "注意点", "基本",
    "プロ", "道具", "自作", "おすすめ", "人気", "時短", "短時間",
    "身近なもの", "家にあるもの", "代用", "綺麗に", "わかりやすい", "図解",
    "一人で", "安全", "アレンジ", "裏ワザ", "ポイント", "徹底解説",
    "準備", "失敗", "失敗例", "最新"
]

def match_domain_howto(suffix: str) -> bool:
    """
    指定されたsuffixがハウツー・操作系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == h or s_last.endswith(h) for h in HOWTO_SUFFIXES)

def is_incoherent_howto(prefix: str, suffix: str) -> bool:
    """
    ハウツー系サフィックスに対し、価格・外見語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in HOWTO_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_howto_prefixes() -> List[str]:
    """
    ハウツー・作業系に最適なキラープレフィックスリストを返す。
    """
    return list(HOWTO_KILLER_PREFIXES)
