# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: generator_blue_ocean.py
■ カテゴリ: Blue Ocean / 第3の軸（AI創造性・視点ずらし枠）生成エンジン
■ 責務・役割（Single Responsibility）:
  - 1st Priority: Gemini API（AI意味推論）により、シードキーワードの深層心理と
    文脈に100%適合した「2語中心（15件）」＋「自然な3語インテント（10件）」を生成。
  - 2nd Priority (Fallback / オフライン): 精密なオントロジー分類エンジンにより、
    ゲーム/学習/料理/酒/美容/汎用抽象概念の文脈不一致語（100均・一人暮らし等）を
    完全排除した安全な25件を即座に生成する。
==============================================================================
"""

import re
from typing import List
from filter_prohibited_terms import is_prohibited_term
from engine_gemini_client import generate_keywords_via_gemini

def detect_seed_ontology(seed: str) -> str:
    s = seed.lower()
    # 学習・教育・ゲーム・パズル・試験
    if any(w in s for w in ["アルゴロジック", "解答", "答え", "過去問", "数学", "英語", "プログラミング", "問題", "攻略", "検定", "資格", "模試", "テスト", "ドリル", "勉強"]):
        return "edu_game"
    # 酒・嗜好品・飲料
    if any(w in s for w in ["ウイスキー", "シーバスリーガル", "山崎", "白州", "響", "マッカラン", "ハイボール", "酒", "ワイン", "ビール", "コーヒー", "紅茶"]):
        return "whisky_drink"
    # 料理・食品・調理
    if any(w in s for w in ["レシピ", "フライパン", "料理", "食べる", "肉", "焼き", "煮", "ケーキ", "スイーツ", "食材", "調理"]):
        return "cooking"
    # 美容・コスメ・スキンケア
    if any(w in s for w in ["リップ", "コスメ", "メイク", "肌", "化粧", "シャンプー", "ネイル", "髪", "スキンケア"]):
        return "beauty"
    # 色・アート・美術
    if any(w in s for w in ["色", "絵の具", "水彩", "アクリル", "混色", "カラー", "イラスト"]):
        return "art"
    return "abstract_general"

def generate_blue_ocean_keywords(seed: str, slot_a: str = "", slot_b: str = "") -> List[str]:
    """
    シードキーワードから「堅牢な2語（15件）」＋「キラー意図3語（10件）」を生成する。
    Gemini APIが有効ならAI意味推論を優先し、未設定時はオントロジー安全網で生成。
    """
    clean_seed = re.sub(r'[\s\u3000]+', ' ', seed).strip()
    tokens = clean_seed.split()

    # 1st Priority: Gemini AI による動的意味推論
    ai_results = generate_keywords_via_gemini(clean_seed)
    if ai_results and len(ai_results) >= 20:
        return ai_results[:25]

    # 2nd Priority: 精密オントロジー安全網（フォールバック）
    p_entity = slot_a.split()[0] if slot_a else (tokens[0] if tokens else "対象")
    p_action = slot_b if slot_b else (" ".join(tokens[1:]) if len(tokens) > 1 else "方法")
    s_action = tokens[-1] if len(tokens) > 1 else "方法"

    ontology = detect_seed_ontology(clean_seed)

    if ontology == "edu_game":
        # 学習・パズル・教育: ズル、最少手順、星3、ループなど（100均や一人暮らしは完全排除）
        two_words = [
            f"{p_entity} 最少手順", f"{p_entity} ループ", f"{p_entity} ズル判定",
            f"{p_entity} 星3", f"{p_entity} 裏ワザ", f"{p_entity} 旗スキップ",
            f"{p_entity} 思考力", f"{p_entity} 最短ルート", f"{p_entity} つまずき",
            f"{p_entity} 小学生", f"{p_entity} 自力", f"{p_entity} 解き方 コツ",
            f"{p_entity} 応用問題", f"{p_entity} 発展", f"{p_entity} やり直し"
        ]
        three_words = [
            f"自力で解く {clean_seed} コツ",
            f"答えを見ない {clean_seed} 方法",
            f"最少ステップ {clean_seed} 裏ワザ",
            f"星3を取る {clean_seed} 手順",
            f"小学生 わかりやすい {clean_seed}",
            f"プログラミング的思考 {clean_seed}",
            f"最短クリア {clean_seed} コツ",
            f"つまずきやすい {clean_seed} 解説",
            f"失敗しない {clean_seed} 考え方",
            f"授業で使える {clean_seed} 活用"
        ]

    elif ontology == "whisky_drink":
        two_words = [
            f"シングルモルト {s_action}", f"ブレンデッド {s_action}", f"スコッチ {s_action}",
            f"ジャパニーズ {s_action}", f"バーボン {s_action}",
            f"{p_entity} ハイボール", f"{p_entity} ロック", f"{p_entity} 水割り",
            f"{p_entity} ストレート", f"{p_entity} トワイスアップ",
            f"{p_entity} 定価", f"{p_entity} プレ値", f"{p_entity} 終売",
            f"{p_entity} 旧ボトル", f"{p_entity} 特級"
        ]
        three_words = [
            f"{clean_seed} 飲み方", f"{clean_seed} 定価", f"{clean_seed} 評価",
            f"{clean_seed} 味", f"{clean_seed} ハイボール 比率",
            f"{clean_seed} ミズナラ 違い", f"{p_entity} 12年 18年 比較",
            f"{clean_seed} まずい 理由", f"{clean_seed} 美味しい 飲み方",
            f"{clean_seed} おすすめ グラス"
        ]

    elif ontology == "cooking":
        two_words = [
            f"塊肉 {s_action}", f"ジビエ {s_action}", f"ラム肉 {s_action}",
            f"鹿肉 {s_action}", f"鴨肉 {s_action}",
            f"{p_entity} 焼きすぎ", f"{p_entity} 生焼け", f"{p_entity} パサパサ",
            f"{p_entity} 救済", f"{p_entity} 再加熱",
            f"メイラード 焼き色", f"塊肉 芯温", f"{p_entity} 肉汁",
            f"{p_entity} 火入れ", f"塊肉 休ませる"
        ]
        three_words = [
            f"コツ {p_action}", f"デメリット {p_action}", f"失敗しない {p_action}",
            f"注意点 {p_action}", f"メリット {p_action}",
            f"{p_entity} {p_action} ホイルなし", f"{p_entity} {p_action} タコ糸なし",
            f"{p_entity} {p_action} 温度計なし", f"{p_entity} {p_action} 前日仕込み",
            f"{p_entity} {p_action} 少量2人分"
        ]

    elif ontology == "beauty":
        two_words = [
            f"{p_entity} 荒れる", f"{p_entity} 皮剥け", f"{p_entity} 落ちない",
            f"{p_entity} ブルベ", f"{p_entity} イエベ", f"{p_entity} 色素沈着",
            f"{p_entity} 成分", f"{p_entity} 落とし方", f"{p_entity} 下地",
            f"{p_entity} 乾燥対策", f"{p_entity} 塗り直し", f"{p_entity} 縦じわ",
            f"{p_entity} 密着", f"{p_entity} 発色", f"{p_entity} 似合わない"
        ]
        three_words = [
            f"荒れない {clean_seed} 塗り方", f"落ちない {clean_seed} コツ",
            f"ブルベ夏 {clean_seed} 選び方", f"乾燥しない {clean_seed} 下地",
            f"皮剥けしない {clean_seed} 対策", f"クレンジング不要 {clean_seed}",
            f"マスクにつかない {clean_seed}", f"初心者 {clean_seed} 失敗しない",
            f"買ってよかった {clean_seed} 比較", f"パーソナルカラー {clean_seed}"
        ]

    else: # abstract_general（絶対に100均・一人暮らし等の生活偏重単語を使わない汎用安全枠）
        two_words = [
            f"{p_entity} 原理", f"{p_entity} 仕組み", f"{p_entity} 基礎知識",
            f"{p_entity} 向き不向き", f"{p_entity} メリット", f"{p_entity} デメリット",
            f"{p_entity} 注意点", f"{p_entity} 失敗原因", f"{p_entity} つまずき",
            f"{p_entity} プロ視点", f"{p_entity} 本質", f"{p_entity} 比較基準",
            f"{p_entity} 選び方", f"{p_entity} 見落とし", f"{p_entity} リスク"
        ]
        three_words = [
            f"失敗しない {p_entity} コツ", f"知っておくべき {p_entity} 注意点",
            f"初心者向け {p_entity} 基礎", f"プロが教える {p_entity} ポイント",
            f"後悔しない {p_entity} 選び方", f"{p_entity} メリット デメリット 比較",
            f"よくある {p_entity} 失敗パターン", f"効率的な {p_entity} 手順",
            f"安全な {p_entity} 進め方", f"おすすめの {p_entity} 活用法"
        ]

    merged = []
    seen = set()
    for kw in two_words + three_words:
        kw_clean = re.sub(r'[\s\u3000]+', ' ', kw).strip()
        if kw_clean and kw_clean != clean_seed and kw_clean not in seen and not is_prohibited_term(kw_clean):
            seen.add(kw_clean)
            merged.append(kw_clean)

    return merged[:25]
