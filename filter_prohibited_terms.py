# -*- coding: utf-8 -*-
"""
filter_prohibited_terms.py
責務: 地元系（全国自治体3756件、地域・店舗・場所）およびエンタメ系（芸能・アニメ・ゲーム等）の事前排除判定
Pure single-responsibility module.
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
