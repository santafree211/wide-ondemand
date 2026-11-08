# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_gadget.py
■ カテゴリ: Domain Attribute / ⑧ IT・ガジェット・機器・ソフトウェア系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「アプリ」「ソフト」「ツール」「機種」「型番」「スペック」
    「バッテリー」「充電」「アップデート」「ドライバ」等のIT・機器属性に該当するか判定する。
  - 「女子ウケ」「垢抜け」「栄養」「副作用」「カロリー」「美味しい」「隠し味」等の
    外見・グルメ・健康系プレフィックスとの意味破綻（例: 「女子ウケ バッテリー」「美味しい アプリ」等）を検知・排除する。
  - IT・ガジェット系に特化した高CTRキラープレフィックス（無料、互換性、使い方、高速化等）を供給する。
=============================================================================
"""

from typing import List

# IT・ガジェット・ソフトウェア系サフィックス
GADGET_SUFFIXES = [
    "アプリ", "ソフト", "ツール", "機種", "型番", "スペック", "性能",
    "バッテリー", "充電", "アップデート", "ファームウェア", "ドライバ",
    "拡張機能", "プラグイン", "OS", "メモリ", "ストレージ", "端子"
]

# IT系と衝突して意味破綻を起こす外見・グルメ・健康系プレフィックス
GADGET_INCOHERENT_PREFIXES = [
    "女子ウケ", "垢抜け", "体型カバー", "栄養", "副作用", "カロリー",
    "美味しい", "隠し味", "黄金比", "日持ち", "賞味期限", "下ごしらえ",
    "ダサい", "モテる", "きれいめ"
]

# IT・ガジェット系に最適化された高品質キラープレフィックス（30件）
GADGET_KILLER_PREFIXES = [
    "無料", "有料", "使い方", "おすすめ", "人気", "最新", "比較", "互換性",
    "重い", "落ちる", "初期化", "設定", "接続方法", "買い替え", "評判",
    "口コミ", "レビュー", "安全", "セキュリティ", "同期", "バックアップ",
    "復元", "初心者", "動作環境", "高速化", "エラー", "アップデート", "便利",
    "通知", "対応機種"
]

def match_domain_gadget(suffix: str) -> bool:
    """
    指定されたsuffixがIT・ガジェット系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == g or s_last.endswith(g) for g in GADGET_SUFFIXES)

def is_incoherent_gadget(prefix: str, suffix: str) -> bool:
    """
    IT系サフィックスに対し、グルメ・外見語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in GADGET_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_gadget_prefixes() -> List[str]:
    """
    IT・ガジェット系に最適なキラープレフィックスリストを返す。
    """
    return list(GADGET_KILLER_PREFIXES)
