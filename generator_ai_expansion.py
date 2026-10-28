# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: generator_ai_expansion.py
■ カテゴリ: Orchestration / 前後2大固定軸展開オーケストレーター
■ 責務・役割（Single Responsibility）:
  - シードキーワードの構文解析（語数判定: 2語モード / 3語モードの自動判別）。
  - 各種サブモジュール（外部サジェストAPI、禁止語除外判定、同族判定エンジン）を統括・結合し、
    ルール02（完全対称性の原則）およびルール03（25件閾値）に準拠した軸①・軸②を完成させる。
  - 合計50個（軸①: 25個、軸②: 25個）の重複ゼロ・実測クエリ候補を確定して返却する。

■ 設計思想・背景:
  - 【2語モード（[A] [B]）】:
    - 軸① `[A] 〇〇`: 前置1語固定（元KW除外）。Googleサジェストと悩み・ハウツー・代用系で25個深掘り。
    - 軸② `〇〇 [B]`: 後置1語固定（元KW除外）。Aの同族（色・号数・家電・飲料等）を最優先注入して25個横展開。
  - 【3語モード（[A] [B] [C]）】:
    - 1語固定（カメラ 〇〇 〇〇 等）にすると文脈が拡散するため、「前後2語スライド固定型（文脈死守）」を採用。
    - 軸① `[A B] 〇〇`: 対象ペア固定（例: カメラ アプリ 〇〇、5号 ケーキ 〇〇、炊飯器 ケーキ 〇〇）。
    - 軸② `〇〇 [B C]`: 後ペア固定（例: 〇〇 アプリ ロゴ、〇〇 ケーキ 切り方）。Aの同族を前置して横展開。

■ 入出力仕様:
  - [Input]:
    - seed: str （ユーザー入力キーワード。例: "茶色 作り方", "カメラ アプリ ロゴ", "5号 ケーキ 切り方"）
  - [Output]:
    - Dict[str, any]:
      - "mode": "2_words" または "3_words"
      - "slot_a": 軸①の固定プレフィックス文字列
      - "slot_b": 軸②の固定サフィックス文字列
      - "axis1_label": 軸①のUI用表示ラベル（例: "軸①: [カメラ アプリ] 〇〇 (前固定)"）
      - "axis2_label": 軸②のUI用表示ラベル（例: "軸②: 〇〇 [アプリ ロゴ] (後固定)"）
      - "axis1": 軸①の完成キーワードリスト（きっかり25個）
      - "axis2": 軸②の完成キーワードリスト（きっかり25個）
      - "total_count": 合計キーワード数（きっかり50個）

■ 内部アルゴリズム / 処理フロー:
  1. 空白文字（半角・全角 U+3000）を正規化し、トークン配列に分割。
  2. トークン数が3語以上の場合は `_generate_3word_axes`、2語以下の場合は `_generate_2word_axes` に自動分岐。
  3. 各モード内で外部サジェストAPI（api_suggest_client）から候補を取得。
  4. 同族判定エンジン（engine_semantic_family）によりA側の同族リストを特定し、軸②の先頭に最優先充当。
  5. 禁止語フィルター（filter_prohibited_terms）で3,756自治体名・店舗・エンタメ語を100%事前排除。
  6. 星が減りにくい悩み・手順・代用系（HIGH_RETENTION_TERMS）でスコアリングおよびスマート補完。
  7. 元シードキーワードの完全除外、および重複排除（Dedup）を行い、きっかり各25個（計50個）を生成。

■ 厳格な制約・禁止事項:
  - 元シードキーワードと完全一致するクエリを軸①・軸②に含めてはならない（完全除外）。
  - 軸①・軸②の間、および各軸内で重複キーワードを出力してはならない（Setによる一意性保証）。
  - 地元系・エンタメ系キーワードは軸生成段階で100%排除すること。
  - ボリュームや難易度の捏造を行ってはならない。

■ 保守・修正時のガイドライン:
  - 構文解析の分割ルールを変更する場合は、Rule 01 および Rule 02 と整合性を保つこと。
==============================================================================
"""

import re
from typing import Dict, List, Tuple

# 単一責任モジュール群のインポート
from api_suggest_client import fetch_search_suggestions
from filter_prohibited_terms import is_prohibited_term
from engine_semantic_family import (
    detect_scale_family,
    detect_semantic_family,
    HARDWARE_PARTS,
    APPLIANCES_LIST,
    HEALTH_DRINKS,
    MENTAL_TRAITS,
    CAR_WASH_STYLES
)

# 【星が減りにくい（知恵袋・個人ブログが居座る）優遇キーワード型】
HIGH_RETENTION_TERMS = [
    # トラブル・悩み・防止系
    "外れ防止", "外れる", "落ちる", "落下防止", "壊れた", "切れた", "外れない", "なくす", "落とす",
    # 代替・裏ワザ・自作系
    "代わり", "代用", "自作", "身近なもの", "改造",
    # 手順・ハウツー・コツ系
    "付け方", "外し方", "つなぎ方", "通し方", "切り方", "短くする", "長さ調整", "結び方", "固定", "補強", "復活",
    # 不安・デメリット・失敗回避系
    "デメリット", "注意点", "後悔", "危険性", "失敗", "比較", "選び方", "寿命", "劣化", "錆びる", "変色"
]

# 【星が激減しやすい（EC物販・店舗情報に押し出される）抑制キーワード】
LOW_RETENTION_TERMS = [
    "カバー", "売り場", "コーナー", "場所", "通販", "価格", "値段", "ランキング", "おすすめ", "取扱店", "店舗"
]

KNOWN_SUFFIXES = [
    "100均", "ダイソー", "セリア", "キャンドゥ", "ワッツ",
    "おすすめ", "口コミ", "評判", "違い", "比較", "ランキング",
    "使い方", "作り方", "危険性", "デメリット", "メリット", "効果",
    "体に悪い", "買ってはいけないメーカー", "買ってはいけない", "太る", "痩せる",
    "低い", "高い", "サブスク", "レンタル", "知育", "売ってない", "どこで買える"
]

def score_term(t: str) -> int:
    """高維持キーワード優先度スコアリング"""
    for hr in HIGH_RETENTION_TERMS:
        if hr in t:
            return 10
    for lr in LOW_RETENTION_TERMS:
        if lr in t:
            return -5
    return 1

def smart_split_seed(text: str) -> Tuple[str, str]:
    """
    シードキーワードを安全にスロットAとスロットBに分割する（互換性提供）
    """
    clean = re.sub(r'[\s\u3000]+', ' ', text).strip()
    parts = clean.split(" ")
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    for s in sorted(KNOWN_SUFFIXES, key=len, reverse=True):
        if clean.endswith(s) and len(clean) > len(s):
            return clean[:-len(s)].strip(), s
    return clean, ""

# =============================================================
# 3語モード展開オーケストレーター: [A B] 〇〇 と 〇〇 [B C]
# =============================================================
def _generate_3word_axes(tokens: List[str], clean_seed: str) -> Dict[str, any]:
    """
    3語キーワード [A] [B] [C] の前後2大固定軸展開
    軸①: [A B] 〇〇 (前2語固定25個) - 対象と属性を固定し、悩み・手順・ハウツーを深掘り
    軸②: 〇〇 [B C] (後2語固定25個) - 目的と属性を固定し、Aの同族ジャンル・手段・スケールを横展開
    """
    token_a = tokens[0]
    token_b = tokens[1]
    token_c = " ".join(tokens[2:])

    pair_ab = f"{token_a} {token_b}"
    pair_bc = f"{token_b} {token_c}"

    # ---------------------------------------------------------
    # 軸① [A B] 〇〇 の生成 (前2語固定)
    # ---------------------------------------------------------
    raw_axis1_terms = []

    # 1. Googleサジェストから "A B " の候補を取得
    suggs_ab = fetch_search_suggestions(f"{pair_ab} ")
    for s in suggs_ab:
        term = s.replace(pair_ab, "").strip()
        if term and not is_prohibited_term(term) and term not in raw_axis1_terms:
            raw_axis1_terms.append(term)

    # 2. 全体シード "A B C " の派生サジェストも取得
    suggs_seed = fetch_search_suggestions(f"{clean_seed} ")
    for s in suggs_seed:
        term = s.replace(pair_ab, "").strip()
        if term and not is_prohibited_term(term) and term not in raw_axis1_terms:
            raw_axis1_terms.append(term)

    # 3. 高維持キーワードでスコアリング＆補完
    sorted_a1 = sorted(raw_axis1_terms, key=score_term, reverse=True)
    for hr in HIGH_RETENTION_TERMS:
        if hr not in sorted_a1 and hr != token_c and not is_prohibited_term(hr):
            sorted_a1.append(hr)
        if len(sorted_a1) >= 35:
            break

    # 4. 汎用優遇ワードで25個まで埋める
    fallbacks_a1 = ["おすすめ", "選び方", "人気", "無料", "評判", "使い方", "初心者", "コツ", "比較", "違い", "注意点"]
    for fb in fallbacks_a1:
        if fb not in sorted_a1 and fb != token_c and not is_prohibited_term(fb):
            sorted_a1.append(fb)
        if len(sorted_a1) >= 30:
            break

    # 元シードおよび禁止語を排除してきっかり25個
    final_a1_terms = []
    for t in sorted_a1:
        full_kw = f"{pair_ab} {t}".strip()
        if full_kw != clean_seed and not is_prohibited_term(t) and t not in final_a1_terms:
            final_a1_terms.append(t)
        if len(final_a1_terms) >= 25:
            break

    full_axis1 = [f"{pair_ab} {t}".strip() for t in final_a1_terms]

    # ---------------------------------------------------------
    # 軸② 〇〇 [B C] の生成 (後2語固定・同族横展開)
    # ---------------------------------------------------------
    raw_axis2_terms = []

    # ★最重要: token_a の同族（同ジャンルアプリ、調理器具、号数、合数、色など）を最優先注入
    fam_a = detect_semantic_family(token_a)
    if fam_a:
        _, siblings_a = fam_a
        for sa in siblings_a:
            if sa != token_a and not is_prohibited_term(sa) and sa not in raw_axis2_terms:
                raw_axis2_terms.append(sa)

    # 2. Googleサジェストから "B C " の前候補を取得
    suggs_bc = fetch_search_suggestions(f"{pair_bc} ")
    for s in suggs_bc:
        term = s.replace(pair_bc, "").strip()
        if term and term != token_a and not is_prohibited_term(term) and term not in raw_axis2_terms:
            raw_axis2_terms.append(term)

    # 3. 25個に満たない場合のスマート補完（ブログ優遇・属性・悩み補完）
    blog_attributes = [
        "ダサい", "疲れない", "歩きやすい", "痛い", "身長", "黒", "白", "安い", "コスパ", "おすすめ",
        "人気", "かっこいい", "選び方", "デメリット", "注意点", "後悔", "手入れ", "寿命", "コーデ", "比較"
    ]
    for ba in blog_attributes:
        if ba != token_a and not is_prohibited_term(ba) and ba not in raw_axis2_terms:
            raw_axis2_terms.append(ba)
        if len(raw_axis2_terms) >= 35:
            break

    final_a2_terms = []
    for t in raw_axis2_terms:
        full_kw = f"{t} {pair_bc}".strip()
        if full_kw != clean_seed and not is_prohibited_term(t) and t not in final_a2_terms:
            final_a2_terms.append(t)
        if len(final_a2_terms) >= 25:
            break

    full_axis2 = [f"{t} {pair_bc}".strip() for t in final_a2_terms]

    return {
        "mode": "3_words",
        "slot_a": pair_ab,
        "slot_b": pair_bc,
        "axis1_label": f"軸①: [{pair_ab}] 〇〇 (前固定)",
        "axis2_label": f"軸②: 〇〇 [{pair_bc}] (後固定)",
        "fam_a": fam_a[0] if fam_a else None,
        "axis1_terms": final_a1_terms,
        "axis2_terms": final_a2_terms,
        "axis1": full_axis1,
        "axis2": full_axis2,
        "total_count": len(full_axis1) + len(full_axis2)
    }

# =============================================================
# 2語モード展開オーケストレーター: [A] 〇〇 と 〇〇 [B]
# =============================================================
def _generate_2word_axes(tokens: List[str], clean_seed: str) -> Dict[str, any]:
    """
    2語キーワード [A] [B] の前後2大固定軸展開（対称性の原則）
    軸①: [A] 〇〇 (前固定25個)
    軸②: 〇〇 [B] (後固定25個・同族横展開)
    """
    if len(tokens) >= 2:
        slot_a = tokens[0]
        slot_b = tokens[1]
    else:
        slot_a = tokens[0] if tokens else clean_seed
        slot_b = ""
        for s in sorted(KNOWN_SUFFIXES, key=len, reverse=True):
            if clean_seed.endswith(s) and len(clean_seed) > len(s):
                slot_a = clean_seed[:-len(s)].strip()
                slot_b = s
                break

    fam_a = detect_semantic_family(slot_a)
    fam_b = detect_semantic_family(slot_b) if slot_b else None

    # 軸① [A] 〇〇
    raw_axis1_terms = []
    if fam_b:
        _, siblings_b = fam_b
        for sb in siblings_b:
            if sb != slot_b and not is_prohibited_term(sb) and sb not in raw_axis1_terms:
                raw_axis1_terms.append(sb)

    if slot_b:
        suggs_combo = fetch_search_suggestions(f"{clean_seed} ")
        for s in suggs_combo:
            term = s.replace(clean_seed, "").strip()
            if term and not is_prohibited_term(term) and term not in raw_axis1_terms:
                raw_axis1_terms.append(term)

    suggs_a = fetch_search_suggestions(f"{slot_a} ")
    for s in suggs_a:
        term = s.replace(slot_a, "").strip()
        if term and term != slot_b and not is_prohibited_term(term) and term not in raw_axis1_terms:
            raw_axis1_terms.append(term)

    if fam_a and fam_a[0] == "colors":
        color_craft_terms = [
            "絵の具", "配合", "混色", "比率", "三原色", "パレット", "作り方 絵の具", "アクリル",
            "水彩", "色見本", "補色", "調色", "種類", "代用", "自作", "コツ", "濃淡"
        ]
        for cct in color_craft_terms:
            if cct != slot_b and cct not in raw_axis1_terms:
                raw_axis1_terms.insert(0, cct)

    sorted_a1 = sorted(raw_axis1_terms, key=score_term, reverse=True)
    for hr in HIGH_RETENTION_TERMS:
        if hr not in sorted_a1 and hr != slot_b and not is_prohibited_term(hr):
            sorted_a1.append(hr)
        if len(sorted_a1) >= 35:
            break

    final_a1_terms = []
    for t in sorted_a1:
        full_kw = f"{slot_a} {t}".strip()
        if full_kw != clean_seed and not is_prohibited_term(t) and t not in final_a1_terms:
            final_a1_terms.append(t)
        if len(final_a1_terms) >= 25:
            break
    full_axis1 = [f"{slot_a} {t}".strip() for t in final_a1_terms]

    # 軸② 〇〇 [B]
    raw_axis2_terms = []
    if fam_a:
        _, siblings_a = fam_a
        for sa in siblings_a:
            if sa != slot_a and not is_prohibited_term(sa) and sa not in raw_axis2_terms:
                raw_axis2_terms.append(sa)

    if slot_b in ["100均", "ダイソー", "セリア", "キャンドゥ", "ワッツ"]:
        for hp in HARDWARE_PARTS:
            if hp != slot_a and hp not in raw_axis2_terms:
                raw_axis2_terms.append(hp)
    elif "メーカー" in slot_b or "買ってはいけない" in slot_b:
        for ap in APPLIANCES_LIST:
            if ap != slot_a and ap not in raw_axis2_terms:
                raw_axis2_terms.append(ap)
    elif "体に悪い" in slot_b or "太る" in slot_b or "効果" in slot_b:
        for hd in HEALTH_DRINKS:
            if hd != slot_a and hd not in raw_axis2_terms:
                raw_axis2_terms.append(hd)
    elif "低い" in slot_b or "高い" in slot_b:
        for mt in MENTAL_TRAITS:
            if mt != slot_a and mt not in raw_axis2_terms:
                raw_axis2_terms.append(mt)
    elif "洗車" in slot_b:
        for cw in CAR_WASH_STYLES:
            if cw != slot_a and cw not in raw_axis2_terms:
                raw_axis2_terms.append(cw)

    if len(raw_axis2_terms) < 25 and slot_b:
        suggs_b = fetch_search_suggestions(f"{slot_b} ")
        for s in suggs_b:
            term = s.replace(slot_b, "").strip()
            if term and term != slot_a and not is_prohibited_term(term) and term not in raw_axis2_terms:
                raw_axis2_terms.append(term)

    blog_quality_items = [
        "やり方", "使い方", "コツ", "手順", "洗い方", "水洗い", "時間", "料金", "相場", "値段",
        "手洗い", "自宅", "初心者", "雨の日", "冬", "夏", "洗剤", "傷つく", "デメリット", "注意点", "失敗"
    ]
    for bq in blog_quality_items:
        if bq != slot_a and not is_prohibited_term(bq) and bq not in raw_axis2_terms:
            raw_axis2_terms.append(bq)
        if len(raw_axis2_terms) >= 30:
            break

    final_a2_terms = []
    for t in raw_axis2_terms:
        full_kw = f"{t} {slot_b}".strip()
        if full_kw != clean_seed and not is_prohibited_term(t) and t not in final_a2_terms:
            final_a2_terms.append(t)
        if len(final_a2_terms) >= 25:
            break
    full_axis2 = [f"{t} {slot_b}".strip() for t in final_a2_terms]

    return {
        "mode": "2_words",
        "slot_a": slot_a,
        "slot_b": slot_b,
        "axis1_label": f"軸①: [{slot_a}] 〇〇 (前固定)",
        "axis2_label": f"軸②: 〇〇 [{slot_b}] (後固定)",
        "fam_a": fam_a[0] if fam_a else None,
        "fam_b": fam_b[0] if fam_b else None,
        "axis1_terms": final_a1_terms,
        "axis2_terms": final_a2_terms,
        "axis1": full_axis1,
        "axis2": full_axis2,
        "total_count": len(full_axis1) + len(full_axis2)
    }

def generate_axes(seed: str) -> Dict[str, any]:
    """
    シードキーワードを語数（2語/3語）に応じて自動判別し、前後2大固定軸を展開
    """
    clean_seed = re.sub(r'[\s\u3000]+', ' ', seed).strip()
    tokens = clean_seed.split(" ")

    if len(tokens) >= 3:
        return _generate_3word_axes(tokens, clean_seed)
    else:
        return _generate_2word_axes(tokens, clean_seed)

if __name__ == "__main__":
    import sys
    test_queries = [
        "カメラ アプリ ロゴ",
        "茶色 作り方",
        "5号 ケーキ 切り方",
        "炊飯器 ケーキ 作り方",
        "3合 お米"
    ]
    for q in test_queries:
        res = generate_axes(q)
        print(f"\n=======================================================")
        print(f"Seed: [{q}] Mode: {res['mode']}")
        print(f"{res['axis1_label']} ({len(res['axis1'])} items):")
        for x in res['axis1'][:5]:
            print(f"  {x}")
        print(f"{res['axis2_label']} ({len(res['axis2'])} items):")
        for y in res['axis2'][:5]:
            print(f"  {y}")
