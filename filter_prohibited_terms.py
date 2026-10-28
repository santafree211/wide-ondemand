# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: filter_prohibited_terms.py
■ カテゴリ: Validation / 禁止語事前排除フィルター
■ 責務・役割（Single Responsibility）:
  - 地元系（全国3,756自治体名、地域・店舗・場所名詞）およびエンタメ系（芸能・アニメ・ゲーム・音楽）の
    禁止キーワードを判定し、軸生成・リサーチ候補から100%事前排除する。
  - ルール02（固定展開）およびルール03（出力前検証）の「事前排除規約」をシステム的に担保する。

■ 設計思想・背景:
  - 地元系（市区町村・駅・店舗など）は、Googleマップ（MEO枠）や大手ポータル（食べログ・ホットペッパー）に
    検索上位を完全独占され、個人ブログが上位表示できず星0判定が確定する。
  - エンタメ系（芸能人名、アニメキャラ、ゲーム攻略等）は、公式サイト・SNS・大手Wikiに独占され、
    トレンドの乱高下により長期的なアクセスが望めない。
  - これらをAPI取得前に除外することで、Ubersuggest APIの貴重な日次枠（100件）を星0キーワードに無駄遣いせず、
    個人ブログ・知恵袋が上位に居座る「真の当たりキーワード」に100%集中投資する。

■ 入出力仕様:
  - [Input]:
    - term: str （判定対象の候補単語。例: "豊橋駅", "アニメ声優", "緑色", "4号"）
  - [Output]:
    - bool （禁止語に該当する場合は True、許可される場合は False）

■ 内部アルゴリズム / 処理フロー:
  1. 文字列を小文字化・空白トリム（空文字列は除外対象 True）。
  2. 全国市区町村マスター（3,756件: japan_municipalities.json）との完全一致判定。
  3. スペース区切り各トークン単位での自治体名チェック、および「〇〇駅」「〇〇店」などの前方/後方一致判定。
  4. 主要都市名・行政区分・店舗場所系固定ワード（LOCAL_EXCLUDE_TERMS: 40語以上）との部分一致判定。
  5. 末尾の行政・店舗正規表現チェック（都・道・府・県・市・区・町・村・駅・店・通り・IC・番地 等）。
  6. 店舗写真クエリ（「〇〇 写真」）の除外。
  7. エンタメ固定ワード（ENTERTAINMENT_EXCLUDE_TERMS: アニメ、キャラ、声優、芸能人、ゲーム、攻略、歌詞 等）の判定。

■ 厳格な制約・禁止事項:
  - 例外的な地域名であっても、自治体マスターに載っている語句をすり抜けさせてはならない。
  - このモジュール内でキーワードの生成やAPI通信を行ってはならない（純粋な判定関数に徹する）。

■ 保守・修正時のガイドライン:
  - 除外対象を増やす場合は、LOCAL_EXCLUDE_TERMS または ENTERTAINMENT_EXCLUDE_TERMS に定数を追記すること。
  - 新たな自治体データの追加は japan_municipalities.json を更新すること。
==============================================================================
"""

import json
import re
from pathlib import Path
from typing import Set

# 固定の地元系・店舗系キーワード
LOCAL_EXCLUDE_TERMS = [
    # 主要地域・行政区分
    "東京", "大阪", "名古屋", "福岡", "北海道", "沖縄", "京都", "横浜", "埼玉", "千葉", "神戸", "仙台", "広島",
    "新宿", "渋谷", "池袋", "銀座", "難波", "梅田", "天神", "博多",
    "都", "道", "府", "県", "市", "区", "町", "村", "駅", "駅前",
    # 店舗・売り場・立地
    "近く", "周辺", "店舗", "取扱店", "売り場", "コーナー", "売ってる場所", "どこで買える", "買える場所",
    "販売店", "ショップ", "実店舗", "店", "アクセス", "地図", "営業時間", "場所", "行き方", "フロア"
]

# 固定のエンタメ系キーワード
ENTERTAINMENT_EXCLUDE_TERMS = [
    # アニメ・漫画・キャラクター
    "アニメ", "漫画", "マンガ", "キャラクター", "キャラ", "声優", "作画", "原作", "ネタバレ", "最終回", "打ち切り",
    "コスプレ", "フィギュア", "聖地", "作者", "登場人物", "イラスト", "同人", "グッズ",
    # 芸能・アイドル・タレント
    "芸能人", "タレント", "アイドル", "熱愛", "結婚", "彼氏", "彼女", "本名", "年齢", "身長", "wiki",
    "出身", "学歴", "炎上", "脱退", "解散", "事務所",
    # ゲーム・配信
    "ゲーム", "攻略", "リセマラ", "最強", "ガチャ", "コード", "実況", "配信", "vtuber", "youtuber", "mod",
    # 音楽・映像
    "曲", "歌", "歌詞", "主題歌", "op", "ed", "ライブ", "コンサート", "映画", "ドラマ", "動画", "ファン", "pv", "mv"
]

def load_municipalities() -> Set[str]:
    """
    全国市区町村マスター辞書 (japan_municipalities.json) を読み込んでSetとして返却
    """
    candidates = [
        Path(__file__).parent / "japan_municipalities.json",
        Path(r"C:\Users\santa\OneDrive\prideall\projects\wide\japan_municipalities.json")
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                pass
    return set()

ALL_LOCALITIES: Set[str] = load_municipalities()

def is_prohibited_term(term: str) -> bool:
    """
    地元系・エンタメ系・物販場所系の禁止キーワードが含まれているか判定
    含まれている場合は True を返し、軸生成から完全に除外する
    """
    clean = term.lower().strip()
    if not clean:
        return True

    # 1. 全国市区町村マスターとの完全照合
    if clean in ALL_LOCALITIES:
        return True

    # 2. スペース区切りの各トークンチェック（例：「幸田 写真」「中野 24時間」等）
    tokens = clean.split()
    for tok in tokens:
        if tok in ALL_LOCALITIES:
            return True
        for loc in ALL_LOCALITIES:
            if len(loc) >= 2 and (tok == loc or tok.startswith(loc) or tok.endswith(loc)):
                return True

    # 3. 地元系・場所系固定ワードチェック
    for loc in LOCAL_EXCLUDE_TERMS:
        if loc in clean:
            return True

    # 4. 末尾が行政区分や交通・店舗パターンチェック
    if re.search(r'(都|道|府|県|市|区|町|村|駅|駅前|口|店|通り|線|ic|インター|丁目|番地)$', clean):
        return True

    # 5. 写真等の店舗・画像系クエリ除外
    if clean.endswith("写真") or clean.startswith("写真"):
        return True

    # 6. エンタメ系チェック
    for ent in ENTERTAINMENT_EXCLUDE_TERMS:
        if ent in clean:
            return True

    return False

if __name__ == "__main__":
    test_terms = ["中野", "幸田", "豊橋駅", "アニメ声優", "緑色", "4号", "作り方"]
    print(f"Loaded {len(ALL_LOCALITIES)} municipalities.")
    for t in test_terms:
        prohibited = is_prohibited_term(t)
        print(f"Term '{t}': {'PROHIBITED' if prohibited else 'ALLOWED'}")
