# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: validator_semantic_coherence.py
■ カテゴリ: Validation / トピッククラスター型 意味整合性バリデーター
■ 責務・役割（Single Responsibility）:
  - トピッククラスターの4大意図（入門・実践・比較・深掘り）とシードキーワードの結合時に、
    日本語として破綻する組み合わせ（価格×ハウツー衝突、語幹重複、文法ゴミ等）を判定・排除する。
  - 16個の業種別ファイルに依存せず、普遍的な言語規則とトピッククラスターエンジンにより
    あらゆるジャンルのキーワード展開を安全かつ高精度に制御する。
=============================================================================
"""

from typing import List
from cluster_topic_builder import build_topic_cluster_prefixes

# 価格・費用系サフィックス（属性: 金銭・数値）
PRICE_COST_SUFFIXES = [
    "値段", "価格", "費用", "料金", "相場", "予算", "金額", "月額", "年額", "維持費"
]

# 状態・感情・不具合系形容詞サフィックス（属性: 違和感・トラブル・不調）
ADJECTIVE_STATE_SUFFIXES = [
    "おかしい", "可笑しい", "変", "痛い", "重い", "遅い", "怪しい", "ダサい",
    "怖い", "つらい", "だるい", "臭い", "危ない", "めんどくさい", "動かない"
]

# 除去・清掃・トラブル対象サフィックス（属性: 汚れ・付着・被害）
STAIN_CLEANING_SUFFIXES = [
    "汚れ", "シミ", "カビ", "黄ばみ", "黒ずみ", "水垢", "サビ", "コゲ",
    "油汚れ", "手垢", "臭い", "ホコリ", "埃", "毛玉", "泥汚れ", "茶渋", "黒カビ"
]

# ハウツー・動作系サフィックス（属性: 工程・作業）
HOWTO_ACTION_SUFFIXES = [
    "作り方", "使い方", "始め方", "やり方", "手順", "直し方", "修理", "設定", "接続"
]

# 礼儀・冠婚葬祭系サフィックス（属性: マナー・儀礼）
CEREMONY_SUFFIXES = [
    "香典", "祝儀", "ご祝儀", "結婚式", "葬式", "お通夜", "告別式", "マナー"
]

# ハウツー・工程系プレフィックス
HOWTO_PREFIXES = [
    "やり方", "コツ", "手順", "方法", "直し方", "修理", "作り方", "使い方"
]

# 価格・安売り系プレフィックス
PRICE_PREFIXES = [
    "安い", "高い", "定価", "最安値", "格安", "割引", "セール", "お得"
]

# 比較重複用トークン
COMPARISON_DUPLICATE_TOKENS = [
    "比較", "違い", "ランキング", "して", "する", "的", "級"
]

# 文法・品詞的なゴミ単語
GRAMMATICAL_JUNK = [
    "英語", "意味", "とは", "画像", "wiki", "一覧", "類語"
]

def is_semantically_incoherent(prefix: str, suffix: str) -> bool:
    """
    prefix と suffix を結合したキーワード（f"{prefix} {suffix}"）が
    日本語の意味として破綻している（検索意図ゼロ）かどうかを判定する。
    破綻している場合は True、自然な場合は False を返す。
    """
    clean_p = prefix.strip()
    clean_s = suffix.strip()

    if not clean_p or not clean_s:
        return False

    # 1. 完全同一語・重複結合の排除（例: 「値段 値段」「比較 比較」「珈琲 珈琲」「可笑しい おかしい」）
    if clean_p == clean_s or clean_p in clean_s or clean_s in clean_p:
        return True
    if any(stem in clean_p and stem in clean_s for stem in ["おかしい", "可笑しい", "おかし"]):
        return True

    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s

    # 2. 状態・形容詞・不具合サフィックスに対するトピック汎用語の結合排除
    # 例: 「おすすめ おかしい」「やり方 おかしい」「初心者 おかしい」「手順 おかしい」
    if any(s_last == a or s_last.endswith(a) for a in ADJECTIVE_STATE_SUFFIXES):
        incoherent_for_adj = [
            "おすすめ", "人気", "ランキング", "初心者", "始め方", "基本",
            "やり方", "コツ", "手順", "選び方", "道具", "準備", "持ち物",
            "比較", "マナー", "ルール", "失敗しない", "メリット", "デメリット"
        ]
        if any(clean_p == inc or clean_p.startswith(inc) for inc in incoherent_for_adj):
            return True

    # 3. 除去・清掃・トラブル対象サフィックスに対するポジティブ・能動語の結合排除
    # 例: 「おすすめ 汚れ」「始め方 汚れ」「マナー 汚れ」「メリット 汚れ」「選び方 汚れ」
    if any(s_last == st or s_last.endswith(st) for st in STAIN_CLEANING_SUFFIXES):
        incoherent_for_stain = [
            "おすすめ", "人気", "ランキング", "始め方", "初心者", "基本",
            "メリット", "デメリット", "マナー", "ルール", "選び方", "持ち物",
            "準備", "比較", "道具", "入門"
        ]
        if any(clean_p == inc or clean_p.startswith(inc) for inc in incoherent_for_stain):
            return True

    # 3. 価格・費用系サフィックスに対するハウツー動詞結合の排除
    # 例: 「やり方 値段」「手順 費用」「コツ 相場」
    if any(s_last == p or s_last.endswith(p) for p in PRICE_COST_SUFFIXES):
        if any(clean_p == h or clean_p.startswith(h) for h in HOWTO_PREFIXES):
            return True

    # 4. ハウツー・動作系サフィックスに対する価格語結合の排除
    # 例: 「安い 作り方」「最安値 使い方」
    if any(s_last == h or s_last.endswith(h) for h in HOWTO_ACTION_SUFFIXES):
        if any(clean_p == pr or clean_p.startswith(pr) for pr in PRICE_PREFIXES):
            return True

    # 5. 冠婚葬祭系に対する格安語の不謹慎排除
    # 例: 「最安値 香典」「格安 祝儀」
    if any(s_last == c or s_last.endswith(c) for c in CEREMONY_SUFFIXES):
        if any(clean_p == pr for pr in PRICE_PREFIXES):
            return True

    # 5. 比較語幹の重複排除（例: 「比較して 比較」「比較的 違い」）
    if any(w in clean_p for w in COMPARISON_DUPLICATE_TOKENS) and any(w in clean_s for w in ["比較", "違い"]):
        return True

    # 6. 文法・品詞的なゴミの排除
    if clean_p in GRAMMATICAL_JUNK:
        return True

    return False

def get_fallback_prefixes_for_suffix(suffix: str) -> List[str]:
    """
    トピッククラスターの4大スロット（入門・実践・比較・深掘り）に基づき、
    suffixと意味整合するキラープレフィックス候補リストを生成して返す。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s

    # 価格・費用サフィックスに特化したクラスター候補
    if any(s_last == p or s_last.endswith(p) for p in PRICE_COST_SUFFIXES):
        return [
            "おすすめ", "人気", "安い", "高い", "コスパ", "相場", "比較", "選び方",
            "最新", "格安", "定価", "お得", "平均", "目安", "自前", "業務用", "高級",
            "最安値", "割引", "セール", "予算", "適正", "中古", "新品", "買い時",
            "節約", "還元", "キャンペーン", "底値", "実質"
        ]

    # 状態・感情・不具合系形容詞サフィックスに特化したクラスター候補
    # （何がおかしいのかという主語・対象 ＋ 原因・理由・対処法）
    if any(s_last == a or s_last.endswith(a) for a in ADJECTIVE_STATE_SUFFIXES):
        return [
            "パソコン", "スマホ", "iPhone", "画面", "Wi-Fi", "音", "車", "エンジン",
            "体調", "頭", "お腹", "喉", "会社", "上司", "職場", "旦那", "夫", "妻",
            "彼氏", "彼女", "態度", "行動", "話", "自分", "原因", "理由", "対処法",
            "直し方", "サイン", "初期症状", "相談", "違和感"
        ]

    # 除去・清掃・トラブル対象サフィックスに特化したクラスター候補
    # （落とし方・対処 ＋ 除去アイテム ＋ 付着した素材・場所 ＋ 落ちない状況）
    if any(s_last == st or s_last.endswith(st) for st in STAIN_CLEANING_SUFFIXES):
        return [
            "落とし方", "消し方", "落とす方法", "服", "シャツ", "白シャツ", "手",
            "壁紙", "床", "革", "オキシクリーン", "ウタマロ", "重曹", "クエン酸",
            "セスキ", "除光液", "エタノール", "洗剤", "漂白剤", "ワイドハイター",
            "100均", "クリーニング", "時間が経った", "落ちない", "乾いた", "応急処置",
            "綺麗にする", "洗う", "対処", "予防", "コツ", "手順"
        ]

    # それ以外の全ジャンル（釣り、ボーリング、珈琲、ファッション、IT、暮らし等）
    # ➡ トピッククラスター4大スロット（入門・実践・比較・深掘り）から自動供給
    raw_cluster_list = build_topic_cluster_prefixes()
    valid_list = []
    for p in raw_cluster_list:
        if not is_semantically_incoherent(p, clean_s):
            valid_list.append(p)

    return valid_list
