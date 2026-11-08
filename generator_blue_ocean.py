# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: generator_blue_ocean.py
■ カテゴリ: Blue Ocean / 第3の軸（AI創造性・視点ずらし枠）生成エンジン
■ 責務・役割（Single Responsibility）:
  - シードキーワードの深層文脈（調理、美術、清掃、釣り、一般）を解析。
  - 「需要が堅いシャープな2語（約15件）」＋「文脈完全合致のキラー意図3語（約10件）」の
    黄金ハイブリッド設計で、競合不在のブルーオーシャンKWをきっかり25件生成する。
  - 文脈にそぐわない無意味な語（マナー、持ち物等）は完全排除し、
    読者の深い悩み（コツ、デメリット、失敗救済、代用、越境）に特化。
==============================================================================
"""

import re
from typing import List
from filter_prohibited_terms import is_prohibited_term

def detect_seed_theme(seed: str) -> str:
    s = seed.lower()
    if any(w in s for w in ["ウイスキー", "シーバスリーガル", "山崎", "白州", "響", "マッカラン", "ハイボール", "酒", "ワイン"]):
        return "whisky"
    if any(w in s for w in ["魚", "シーバス", "ブラックバス", "釣り", "ルアー", "スズキ", "アジ", "サバ"]):
        return "fishing_eating"
    if any(w in s for w in ["色", "絵の具", "水彩", "アクリル", "混色", "カラー", "イラスト"]):
        return "color_art"
    if any(w in s for w in ["インク", "汚れ", "シミ", "落ちない", "落とす", "染み", "洗濯", "カビ"]):
        return "cleaning"
    if any(w in s for w in ["レシピ", "フライパン", "料理", "食べる", "肉", "焼き", "煮", "ケーキ", "スイーツ"]):
        return "cooking"
    return "general"

def generate_blue_ocean_keywords(seed: str, slot_a: str = "", slot_b: str = "") -> List[str]:
    """
    シードキーワードから「堅牢な2語（15件）」＋「キラー意図3語（10件）」を生成する。
    """
    clean_seed = re.sub(r'[\s\u3000]+', ' ', seed).strip()
    tokens = clean_seed.split()

    p_entity = slot_a.split()[0] if slot_a else (tokens[0] if tokens else "対象")
    p_action = slot_b if slot_b else (" ".join(tokens[1:]) if len(tokens) > 1 else "方法")
    s_action = tokens[-1] if len(tokens) > 1 else "方法"

    theme = detect_seed_theme(clean_seed)

    two_word_cands: List[str] = []
    three_word_cands: List[str] = []

    if theme == "cooking":
        # 【堅牢な2語】越境・失敗救済・プロ質感（15件）
        two_word_cands = [
            f"塊肉 {s_action}", f"ジビエ {s_action}", f"ラム肉 {s_action}",
            f"鹿肉 {s_action}", f"鴨肉 {s_action}",
            f"{p_entity} 焼きすぎ", f"{p_entity} 生焼け", f"{p_entity} パサパサ",
            f"{p_entity} 救済", f"{p_entity} 再加熱",
            f"メイラード 焼き色", f"塊肉 芯温", f"{p_entity} 肉汁",
            f"{p_entity} 火入れ", f"塊肉 休ませる"
        ]
        # 【キラー意図3語】文脈完全合致のノウハウ・制約（10件）
        three_word_cands = [
            f"コツ {p_action}",
            f"デメリット {p_action}",
            f"失敗しない {p_action}",
            f"注意点 {p_action}",
            f"メリット {p_action}",
            f"{p_entity} {p_action} ホイルなし",
            f"{p_entity} {p_action} タコ糸なし",
            f"{p_entity} {p_action} 温度計なし",
            f"{p_entity} {p_action} 前日仕込み",
            f"{p_entity} {p_action} 少量2人分"
        ]

    elif theme == "color_art":
        # 【堅牢な2語】越境・混色トラブル・プロ色名（15件）
        two_word_cands = [
            f"アイシングクッキー {p_entity}", f"レジン {p_entity}",
            f"ネイル {p_entity}", f"革靴 {p_entity}", f"サビ塗装 {p_entity}",
            f"{p_entity} 代用", f"{p_entity} 黒なし", f"混色 3原色",
            f"{p_entity} 濁り", f"混色 濁る", f"{p_entity} 濃すぎ",
            f"絵の具 復活", f"テラコッタ 混色", f"くすみモカ 絵の具",
            f"こげ茶 黄金比"
        ]
        # 【キラー意図3語】（10件）
        intent_prefix = f"コツ {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} {p_action} コツ"
        intent_demerit = f"デメリット {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} {p_action} デメリット"
        intent_fail = f"失敗しない {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} {p_action} 失敗しない"
        intent_caution = f"注意点 {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} {p_action} 注意点"

        three_word_cands = [
            intent_prefix,
            intent_demerit,
            intent_fail,
            intent_caution,
            f"黒を使わない {p_entity} 作り方",
            f"3原色だけで {p_entity} 作り方",
            f"{p_entity} 絵の具 代用",
            f"{p_entity} 濁った 直し方",
            f"水彩 混色 濁らないコツ",
            f"透明感のある{p_entity} 作り方"
        ]

    elif theme == "cleaning":
        # 【堅牢な2語】越境素材・トラブル（15件）
        two_word_cands = [
            f"革靴 {s_action}", f"壁紙 {s_action}", f"スニーカー {s_action}",
            f"カーペット {s_action}", f"車シート {s_action}",
            f"{s_action} 放置", f"{s_action} 乾燥後", f"{s_action} 洗濯後",
            f"輪ジミ 直し方", f"色落ち 補修",
            f"油性水性 見分け方", f"ベンジン 染み抜き",
            f"エタノール 染み抜き", f"熱湯 染み抜き", f"界面活性剤 分解"
        ]
        # 【キラー意図3語】（10件）
        intent_prefix = f"コツ {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} {s_action} コツ"
        intent_demerit = f"注意点 {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} {s_action} 注意点"
        intent_fail = f"失敗しない {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} {s_action} 失敗しない"

        three_word_cands = [
            intent_prefix,
            intent_demerit,
            intent_fail,
            f"{s_action} 除光液なし",
            f"{s_action} ウタマロなし",
            f"水洗いできない {p_entity} {s_action}",
            f"時間が経った {clean_seed}",
            f"外出先 応急処置 {s_action}",
            f"学校 制服 {s_action}",
            f"洗剤を使わない {s_action} 落とし方"
        ]

    elif theme == "fishing_eating":
        # 【堅牢な2語】怪魚・下処理・仕立て（15件）
        two_word_cands = [
            f"深海魚 食べる", f"怪魚 食べる", f"ウツボ 食べる",
            f"エイ 食べる", f"サメ 食べる",
            f"{p_entity} 泥臭い", f"{p_entity} 臭み消し", f"{p_entity} 焼きすぎ",
            f"{p_entity} 血抜き失敗", f"津本式 究極血抜き",
            f"{p_entity} 熟成刺身", f"{p_entity} 潮汁", f"{p_entity} 昆布締め",
            f"{p_entity} 皮パリパリ", f"釣り場 下処理"
        ]
        # 【キラー意図3語】（10件）
        intent_prefix = f"コツ {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} 食べる コツ"
        intent_demerit = f"デメリット {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} 食べる 注意点"
        intent_fail = f"失敗しない {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} 失敗しない 料理"

        three_word_cands = [
            intent_prefix,
            intent_demerit,
            intent_fail,
            f"{p_entity} 生食 危険 回避",
            f"{p_entity} 刺身 アニサキス 冷凍時間",
            f"{p_entity} 臭み消し 牛乳なし",
            f"{p_entity} 釣り場での下処理 手順",
            f"{p_entity} 大量消費 冷凍 保存食",
            f"{p_entity} 津本式 血抜き コツ",
            f"{p_entity} 美味しい 食べ方 コツ"
        ]

    elif theme == "whisky":
        # 【堅牢な2語】洋酒種類・飲み方・ボトル価値（15件）
        two_word_cands = [
            f"シングルモルト {s_action}", f"ブレンデッド {s_action}", f"スコッチ {s_action}",
            f"ジャパニーズ {s_action}", f"バーボン {s_action}",
            f"{p_entity} ハイボール", f"{p_entity} ロック", f"{p_entity} 水割り",
            f"{p_entity} ストレート", f"{p_entity} トワイスアップ",
            f"{p_entity} 定価", f"{p_entity} プレ値", f"{p_entity} 終売",
            f"{p_entity} 旧ボトル", f"{p_entity} 特級"
        ]
        # 【キラー意図3語】（10件）
        three_word_cands = [
            f"{clean_seed} 飲み方",
            f"{clean_seed} 定価",
            f"{clean_seed} 評価",
            f"{clean_seed} 味",
            f"{clean_seed} ハイボール 比率",
            f"{clean_seed} ミズナラ 違い",
            f"{p_entity} 12年 18年 比較",
            f"{clean_seed} まずい 理由",
            f"{clean_seed} 美味しい 飲み方",
            f"{clean_seed} おすすめ グラス"
        ]

    else: # general
        two_word_cands = [
            f"プロ用 {p_entity}", f"海外 {p_entity}", f"業務用 {p_entity}",
            f"自作 {p_entity}", f"{p_entity} やり直し", f"{p_entity} 失敗対処",
            f"{p_entity} 復元", f"{p_entity} 原理", f"{p_entity} 仕組み",
            f"{p_entity} 黄金比", f"{p_entity} 道具なし", f"{p_entity} 100均代用",
            f"一人暮らし {p_entity}", f"忙しい人 {p_entity}", f"{p_entity} 最短"
        ]
        intent_prefix = f"コツ {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} コツ"
        intent_demerit = f"デメリット {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} デメリット"
        intent_fail = f"失敗しない {p_action}" if len(p_action.split()) >= 2 else f"{p_entity} 失敗しない コツ"

        three_word_cands = [
            intent_prefix,
            intent_demerit,
            intent_fail,
            f"お金をかけない {clean_seed}",
            f"専用道具なし {clean_seed}",
            f"{clean_seed} 失敗したときの対処",
            f"{clean_seed} プロが教える裏技",
            f"初心者 失敗しない {clean_seed}",
            f"{clean_seed} 仕組み 原理",
            f"{clean_seed} メリット デメリット"
        ]

    result = []
    seen = set()

    # 1. 堅牢な2語を先頭から最大15件
    for kw in two_word_cands:
        clean_kw = re.sub(r'[\s\u3000]+', ' ', kw).strip()
        if clean_kw and clean_kw not in seen and not is_prohibited_term(clean_kw):
            seen.add(clean_kw)
            result.append(clean_kw)
        if len(result) >= 15:
            break

    # 2. キラー意図の3語を合流させて合計25件を満たす
    for kw in three_word_cands:
        clean_kw = re.sub(r'[\s\u3000]+', ' ', kw).strip()
        if clean_kw and clean_kw not in seen and not is_prohibited_term(clean_kw):
            seen.add(clean_kw)
            result.append(clean_kw)
        if len(result) >= 25:
            break

    # 不足時のセーフティ補充
    if len(result) < 25:
        for kw in two_word_cands + three_word_cands:
            clean_kw = re.sub(r'[\s\u3000]+', ' ', kw).strip()
            if clean_kw and clean_kw not in seen and not is_prohibited_term(clean_kw):
                seen.add(clean_kw)
                result.append(clean_kw)
            if len(result) >= 25:
                break

    return result[:25]
