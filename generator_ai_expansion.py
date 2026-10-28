# -*- coding: utf-8 -*-
"""
generator_ai_expansion.py
責務: シード構文解析・前後2大固定軸展開（対称性の原則）・50件メガバッチ軸生成オーケストレーション
依存:
  - api_suggest_client.py: 外部サジェストAPI通信
  - filter_prohibited_terms.py: 地元名・エンタメ系キーワード事前排除判定
  - engine_semantic_family.py: 同族判定・単位スケール生成
Pure single-responsibility orchestration module.
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

def smart_split_seed(text: str) -> Tuple[str, str]:
    """
    シードキーワードを語数および文脈に応じて [A] と [B] に分割
    """
    clean = re.sub(r'[\s\u3000]+', ' ', text).strip()
    tokens = clean.split(" ")
    if len(tokens) >= 3:
        # スケール単位（号数・合数・人前等）があればそれを最優先スロットAとして抽出
        scale_idx = -1
        for idx, tok in enumerate(tokens):
            if detect_scale_family(tok):
                scale_idx = idx
                break
        if scale_idx != -1:
            slot_a = tokens[scale_idx]
            other_toks = [t for i, t in enumerate(tokens) if i != scale_idx]
            slot_b = " ".join(other_toks)
            return slot_a, slot_b
        return tokens[0], " ".join(tokens[1:])
    elif len(tokens) == 2:
        return tokens[0], tokens[1]
    
    for s in sorted(KNOWN_SUFFIXES, key=len, reverse=True):
        if clean.endswith(s) and len(clean) > len(s):
            return clean[:-len(s)].strip(), s
    return clean, ""

def generate_axes(seed: str) -> Dict[str, any]:
    """
    シードキーワードを文脈・同族・構文解析し、
    軸①: [A] 〇〇 (前固定) 25個 (元KW除外)
    軸②: 〇〇 [B] (後固定) 25個 (元KW除外)
    合計50個を自動思考・生成する。
    """
    slot_a, slot_b = smart_split_seed(seed)
    clean_seed = f"{slot_a} {slot_b}".strip() if slot_b else slot_a

    # 同族（ファミリー）検出
    fam_a = detect_semantic_family(slot_a)
    fam_b = detect_semantic_family(slot_b) if slot_b else None

    # =========================================================
    # 軸① [A] 〇〇 の生成
    # =========================================================
    raw_axis1_terms = []

    # B側が同族を持つ場合、Bの同族を軸①の最優先として配置
    if fam_b:
        _, siblings_b = fam_b
        for sb in siblings_b:
            if sb != slot_b and not is_prohibited_term(sb) and sb not in raw_axis1_terms:
                raw_axis1_terms.append(sb)

    # Googleサジェストから文脈サジェストを取得
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

    # 色作りなどの特定文脈におけるスマート専門補完
    if fam_a and fam_a[0] == "colors":
        color_craft_terms = [
            "絵の具", "配合", "混色", "比率", "三原色", "パレット", "作り方 絵の具", "アクリル",
            "水彩", "色見本", "補色", "調色", "種類", "代用", "自作", "コツ", "濃淡"
        ]
        for cct in color_craft_terms:
            if cct != slot_b and cct not in raw_axis1_terms:
                raw_axis1_terms.insert(0, cct)

    # 高維持キーワード（悩み・トラブル・手順・代用）で優先スコアリング補完
    def score_term(t: str) -> int:
        for hr in HIGH_RETENTION_TERMS:
            if hr in t:
                return 10
        for lr in LOW_RETENTION_TERMS:
            if lr in t:
                return -5
        return 1

    sorted_a1 = sorted(raw_axis1_terms, key=score_term, reverse=True)

    for hr in HIGH_RETENTION_TERMS:
        if hr not in sorted_a1 and hr != slot_b and not is_prohibited_term(hr):
            sorted_a1.append(hr)
        if len(sorted_a1) >= 35:
            break

    final_a1_terms = [t for t in sorted_a1 if t != slot_b and not is_prohibited_term(t)][:25]
    full_axis1 = [f"{slot_a} {t}".strip() for t in final_a1_terms]

    # =========================================================
    # 軸② 〇〇 [B] の生成
    # =========================================================
    raw_axis2_terms = []

    # ★最重要: slot_a が同族（色、スケール号・合・人前、家電、飲料、スイーツ等）を持つ場合
    # slot_a の同族リストを軸②の先頭に最優先で直接注入！
    if fam_a:
        _, siblings_a = fam_a
        for sa in siblings_a:
            if sa != slot_a and not is_prohibited_term(sa) and sa not in raw_axis2_terms:
                raw_axis2_terms.append(sa)

    # 固定カテゴリ対応（100均、買ってはいけない、体に悪い、低い/高い、洗車等）
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

    # slot_a に同族がない、または25個に満たない場合サジェストと優遇ワードで補完
    if len(raw_axis2_terms) < 25 and slot_b:
        suggs_b = fetch_search_suggestions(f"{slot_b} ")
        for s in suggs_b:
            term = s.replace(slot_b, "").strip()
            if term and term != slot_a and not is_prohibited_term(term) and term not in raw_axis2_terms:
                raw_axis2_terms.append(term)

    # 汎用ブログ優遇ワードで25個まで埋める
    blog_quality_items = [
        "やり方", "使い方", "コツ", "手順", "洗い方", "水洗い", "時間", "料金", "相場", "値段",
        "手洗い", "自宅", "初心者", "雨の日", "冬", "夏", "洗剤", "傷つく", "デメリット", "注意点", "失敗"
    ]
    for bq in blog_quality_items:
        if bq != slot_a and not is_prohibited_term(bq) and bq not in raw_axis2_terms:
            raw_axis2_terms.append(bq)
        if len(raw_axis2_terms) >= 30:
            break

    final_a2_terms = [t for t in raw_axis2_terms if t != slot_a and not is_prohibited_term(t)][:25]
    full_axis2 = [f"{t} {slot_b}".strip() for t in final_a2_terms]

    return {
        "slot_a": slot_a,
        "slot_b": slot_b,
        "fam_a": fam_a[0] if fam_a else None,
        "fam_b": fam_b[0] if fam_b else None,
        "axis1_terms": final_a1_terms,
        "axis2_terms": final_a2_terms,
        "axis1": full_axis1,
        "axis2": full_axis2,
        "total_count": len(full_axis1) + len(full_axis2)
    }

if __name__ == "__main__":
    import sys
    seed = sys.argv[1] if len(sys.argv) > 1 else "茶色 作り方"
    res = generate_axes(seed)
    print(f"Seed: {seed} (FamA: {res['fam_a']}, FamB: {res['fam_b']})")
    print(f"Slot A: {res['slot_a']}, Slot B: {res['slot_b']}")
    print(f"\nAxis 1 ({len(res['axis1'])} items):")
    for x in res['axis1'][:5]:
        print("  ", x)
    print(f"\nAxis 2 ({len(res['axis2'])} items):")
    for y in res['axis2'][:5]:
        print("  ", y)
