# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: cluster_topic_builder.py
■ カテゴリ: Topic Cluster / トピッククラスター4大意図統合供給エンジン
■ 責務・役割（Single Responsibility）:
  - ピラーキーワード（シードKW）に対して、Google・読者が求める「トピッククラスター」を
    構成する4大スロット（入門・実践・比較・深掘り）のキラーワードを均等に統合供給する。
  - ジャンルを過剰分割せず、あらゆる分野（趣味・スポーツ・IT・暮らし・ビジネス等）に
    普遍的に通用する網羅的クラスターリストを生成・返却する。
=============================================================================
"""

from typing import List

# Slot 1: 【入門・準備クラスター】（始めるためのハードル解消）
CLUSTER_SLOT_GETTING_STARTED = [
    "初心者", "始め方", "基本", "準備", "道具", "持ち物", "必要なもの",
    "費用", "相場", "予算", "いくら", "初期費用", "入門"
]

# Slot 2: 【実践・解決クラスター】（ノウハウ・上達・トラブル解決）
CLUSTER_SLOT_HOWTO_TROUBLE = [
    "コツ", "やり方", "手順", "注意点", "失敗しない", "原因", "対処法",
    "解決", "上達", "直し方", "練習", "ポイント", "裏ワザ"
]

# Slot 3: 【比較・選定クラスター】（購買・意思決定・商品選定）
CLUSTER_SLOT_COMPARISON_BUY = [
    "おすすめ", "人気", "比較", "選び方", "ランキング", "口コミ", "評判",
    "コスパ", "定番", "最新", "安い", "高評価", "格安", "最安値"
]

# Slot 4: 【深掘り・疑問クラスター】（納得・ルール・違い・周辺知識）
CLUSTER_SLOT_IN_DEPTH = [
    "違い", "メリット", "デメリット", "理由", "マナー", "ルール",
    "時期", "タイミング", "平均", "期間", "長持ち", "危険"
]

def build_topic_cluster_prefixes() -> List[str]:
    """
    4大クラスタースロットからバランスよく単語を抽出し、
    完全なトピッククラスターを形成する計40件以上のプレフィックス候補リストを返す。
    """
    combined = []
    # 各スロットから均等に交互にブレンド（多様性と網羅性を担保）
    max_len = max(
        len(CLUSTER_SLOT_GETTING_STARTED),
        len(CLUSTER_SLOT_HOWTO_TROUBLE),
        len(CLUSTER_SLOT_COMPARISON_BUY),
        len(CLUSTER_SLOT_IN_DEPTH)
    )

    for i in range(max_len):
        if i < len(CLUSTER_SLOT_COMPARISON_BUY):
            combined.append(CLUSTER_SLOT_COMPARISON_BUY[i])
        if i < len(CLUSTER_SLOT_GETTING_STARTED):
            combined.append(CLUSTER_SLOT_GETTING_STARTED[i])
        if i < len(CLUSTER_SLOT_HOWTO_TROUBLE):
            combined.append(CLUSTER_SLOT_HOWTO_TROUBLE[i])
        if i < len(CLUSTER_SLOT_IN_DEPTH):
            combined.append(CLUSTER_SLOT_IN_DEPTH[i])

    # 重複削除しつつ順序維持
    seen = set()
    result = []
    for item in combined:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result
