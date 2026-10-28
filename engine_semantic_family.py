# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: engine_semantic_family.py
■ カテゴリ: Engine / 文脈・同族・スケール判定エンジン
■ 責務・役割（Single Responsibility）:
  - 入力単語の文脈（ジャンル・単位・スケール）を読み取り、同列・並列に展開すべき「同族（ファミリー）リスト」を特定・生成する。
  - 数値単位パターン（号数、合数、人前、年代、寸法、容量等）を正規表現で検出し、近接順の同族スケールを動的算出する。
  - 意味カテゴリ（色、スイーツ、主食、調理器具、アプリジャンル、家電、健康飲料、メンタル等）の辞書照合を行う。

■ 設計思想・背景:
  - 検索者が「茶色 作り方」と調べた時、軸②（〇〇 作り方）には「緑色 作り方」「青色 作り方」という同族カラーが並ぶべきである。
    （従来の単純サジェストでは「紙飛行機 作り方」のように文脈が崩壊してしまう問題を解決する）
  - 「5号 ケーキ 切り方」であれば「4号/6号/3号 ケーキ 切り方」、「炊飯器 ケーキ 作り方」であれば「オーブン/電子レンジ/フライパン ケーキ 作り方」
    のように、検索意図の文脈を完全維持した高品質な並列横展開を実現する。

■ 入出力仕様:
  - [Input]:
    - term: str （判定対象の単語。例: "5号", "3合", "茶色", "カメラ", "炊飯器", "ケーキ"）
  - [Output]:
    - Optional[Tuple[str, List[str]]]
      - 検出成功時: (カテゴリ名, [同族単語のリスト（元KW除外・優先度順）])
      - 検出失敗時: None

■ 内部アルゴリズム / 処理フロー:
  1. 数値スケール判定 (detect_scale_family):
     - 号数 (`^\d+号$`): 一般号数 [1〜20号] から現在の数値を基準に差分の絶対値が小さい順にソート。
     - 合数 (`^\d+合$`, 半合, 一升): 炊飯等で使われる合数配列から現在の合数を除外。
     - 人前・人分 (`^\d+(人前|人分|人)$`): 近接人数、疑問形（何人前）を含めた同族リストを動的生成。
     - 年代・年齢・月齢・寸法・容量・重量も同様に近接ソート生成。
  2. ドメイン意味属性判定 (detect_semantic_family):
     - 色（COLORS_FULL）: 入力が「〜色」形式か基本色名かを判定し、表記統一された同族色リストを返却。
     - アプリジャンル（APP_GENRES）: カメラ、写真加工、動画編集、イラスト、SNS、家計簿 等。
     - 調理器具・手段（COOKING_APPLIANCES）: 炊飯器、オーブン、電子レンジ、フライパン、トースター 等。
     - スイーツ（SWEETS_LIST）、主食（STAPLES_LIST）、家電（APPLIANCES_LIST）、健康飲料（HEALTH_DRINKS）等。

■ 厳格な制約・禁止事項:
  - 生成・返却する同族リストの中に、元キーワード（入力単語）自身を含めてはならない（完全除外）。
  - このモジュール内でGoogleサジェスト通信や軸の結合（〇〇 [B]）を行ってはならない（generator_ai_expansion の責務）。

■ 保守・修正時のガイドライン:
  - 新たなドメイン（例: 車の車種・工具・文具など）を追加する場合は、定数リストを定義し detect_semantic_family に走査ループを追加すること。
==============================================================================
"""

import re
from typing import Dict, List, Tuple, Optional

# =============================================================
# 同族（ファミリー）マスター辞書群
# =============================================================

# 色マスター（「〜色」および基本色）
COLORS_FULL = [
    "茶色", "緑色", "青色", "赤色", "黄色", "紫色", "肌色", "ピンク", "黒色", "白色",
    "水色", "黄緑", "灰色", "オレンジ", "金色", "銀色", "ベージュ", "紺色", "こげ茶",
    "えんじ色", "朱色", "藍色", "アイボリー", "カーキ", "オリーブ", "キャメル", "藤色",
    "深緑", "山吹色", "エメラルドグリーン", "ラベンダー", "ボルドー", "ターコイズ", "ワインレッド"
]

# 靴・フットウェア
FOOTWEAR_LIST = [
    "スニーカー", "革靴", "ブーツ", "サンダル", "ローファー", "スリッポン", "ミュール",
    "パンプス", "ダッドスニーカー", "ハイカットスニーカー", "ビジネスシューズ",
    "ドレスシューズ", "安全靴", "ランニングシューズ", "ウォーキングシューズ",
    "ショートブーツ", "サイドゴアブーツ", "スノーブーツ", "レインブーツ", "長靴"
]

# 洋菓子・スイーツ
SWEETS_LIST = [
    "ケーキ", "タルト", "シフォンケーキ", "チーズケーキ", "ガトーショコラ", "ロールケーキ",
    "パウンドケーキ", "スポンジケーキ", "ショートケーキ", "パイ", "クッキー", "シュークリーム",
    "プリン", "マフィン", "バウムクーヘン", "クレープ", "パンケーキ", "スフレ", "スコーン",
    "マカロン", "ドーナツ", "ワッフル", "ゼリー", "カステラ", "ブラウニー", "ティラミス"
]

# 主食・穀物
STAPLES_LIST = [
    "お米", "白米", "玄米", "無洗米", "雑穀米", "もち米", "麦ご飯", "パスタ", "うどん",
    "そば", "そうめん", "ラーメン", "焼きそば", "食パン", "フランスパン", "ベーグル",
    "ナン", "フォー", "オートミール", "ピザ生地"
]

# 調理器具・手段
COOKING_APPLIANCES = [
    "炊飯器", "オーブン", "電子レンジ", "フライパン", "トースター", "鍋", "ホットクック",
    "圧力鍋", "グリル", "ホットプレート", "蒸し器", "せいろ", "湯煎", "土鍋", "トースターレンジ",
    "ノンフライヤー", "電気圧力鍋", "低温調理器", "魚焼きグリル", "スキレット"
]

# スマホアプリ・ツールジャンル
APP_GENRES = [
    "カメラ", "写真加工", "動画編集", "イラスト", "お絵かき", "コラージュ", "スキャン",
    "SNS", "音楽", "家計簿", "カレンダー", "メモ", "天気", "時計", "地図", "決済",
    "ゲーム", "ニュース", "ラジオ", "電子書籍", "乗り換え", "歩数計", "睡眠", "ポイ活",
    "英語学習", "辞書", "電卓", "健康管理", "タスク管理"
]

# 定番料理・メニュー
DISHES_LIST = [
    "カレー", "シチュー", "ハンバーグ", "オムライス", "唐揚げ", "餃子", "麻婆豆腐",
    "肉じゃが", "豚汁", "生姜焼き", "チャーハン", "グラタン", "ドリア", "お好み焼き",
    "たこ焼き", "コロッケ", "春巻き", "回鍋肉", "ハヤシライス"
]

# 調味料
SEASONINGS_LIST = [
    "醤油", "味噌", "みりん", "料理酒", "酢", "砂糖", "塩", "マヨネーズ", "ケチャップ",
    "ポン酢", "めんつゆ", "白だし", "だし", "ごま油", "オリーブオイル", "バター",
    "マーガリン", "ウスターソース", "オイスターソース", "コチュジャン", "豆板醤"
]

# 日用金具・手芸・DIYパーツ
HARDWARE_PARTS = [
    "ボールチェーン", "ナスカン", "二重カン", "カニカン", "丸カン", "ヒートン", "カラビナ",
    "ワイヤーリング", "安全ピン", "キーリング", "ストラップパーツ", "キーホルダーパーツ",
    "リールキーホルダー", "チャーム", "留め具", "フック", "S字フック", "押しピン", "ネジ",
    "ボルト", "ナット", "ワッシャー", "リング", "チェーン", "クリップ"
]

# 家電・生活電気
APPLIANCES_LIST = [
    "モバイルバッテリー", "ソーラーパネル", "蓄電池", "ポータブル電源", "ロボット掃除機",
    "冷蔵庫", "ドラム式洗濯機", "洗濯機", "テレビ", "エアコン", "パソコン", "電子レンジ",
    "オーブンレンジ", "IHクッキングヒーター", "加湿器", "空気清浄機", "除湿機", "ドライヤー",
    "電気ケトル", "炊飯器", "掃除機", "食洗機", "スマートウォッチ", "ワイヤレスイヤホン",
    "プロジェクター", "ホットプレート", "トースター", "ミキサー"
]

# 健康飲料・食品
HEALTH_DRINKS = [
    "レモン水", "リンゴ酢", "トマトジュース", "豆乳", "プロテイン", "炭酸水", "白湯",
    "お茶", "コーヒー", "緑茶", "青汁", "甘酒", "アーモンドミルク", "黒酢", "ルイボスティー",
    "エナジードリンク", "スポーツドリンク", "オートミール", "グラノーラ", "ヨーグルト", "納豆",
    "はちみつ", "MCTオイル", "ココア", "ゼロカロリー飲料"
]

# メンタル・心理・人間特性
MENTAL_TRAITS = [
    "自己効力感", "自尊心", "コミュ力", "精神年齢", "語彙力", "集中力", "幸福度", "意欲",
    "感受性", "免疫力", "運動神経", "基礎代謝", "自己評価", "自己肯定感", "忍耐力", "共感力",
    "判断力", "行動力", "知的好奇心", "ストレス耐性", "記憶力", "EQ", "IQ", "自己管理能力", "モチベーション"
]

# 洗車・カーケア
CAR_WASH_STYLES = [
    "手洗い洗車", "コイン洗車", "ガソリンスタンド洗車", "洗車機", "ドライブスルー洗車",
    "出張洗車", "自宅洗車", "セルフ洗車", "高圧洗浄機洗車", "水なし洗車"
]

def detect_scale_family(term: str) -> Optional[Tuple[str, List[str]]]:
    """
    数値＋単位パターン（号数、合数、人前、年代など）を判定し、同族スケールリストを動的生成
    """
    clean = term.strip()

    # 1. 号数 (^d+号$)
    m_gou = re.match(r'^(\d+)号$', clean)
    if m_gou:
        curr = int(m_gou.group(1))
        common_gous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 20]
        sorted_gous = sorted([g for g in common_gous if g != curr], key=lambda x: abs(x - curr))
        return "scale_gou", [f"{g}号" for g in sorted_gous]

    # 2. 合数 (^d+合$, 半合, 一升, 1升)
    if re.match(r'^(\d+|半|一|1)合$', clean) or clean in ["一升", "1升"]:
        all_gous = ["1合", "2合", "3合", "4合", "5合", "6合", "半合", "一升", "1升", "0.5合", "1.5合", "2.5合", "3.5合", "7合", "8合", "10合"]
        res = [g for g in all_gous if g != clean]
        return "scale_goh", res

    # 3. 人前・人分・人数 (^d+(人前|人分|人)$)
    m_nin = re.match(r'^(\d+)(人前|人分|人)$', clean)
    if m_nin:
        curr_num = int(m_nin.group(1))
        unit = m_nin.group(2)
        common_nums = [1, 2, 3, 4, 5, 6, 8, 10]
        sorted_nums = sorted([n for n in common_nums if n != curr_num], key=lambda x: abs(x - curr_num))
        res = [f"{n}{unit}" for n in sorted_nums]
        alt_unit = "人分" if unit == "人前" else "人前"
        res.extend([f"{n}{alt_unit}" for n in sorted_nums[:5]])
        res.extend([f"何{unit}", "一人前", "二人前", "三人前"])
        return "scale_nin", [r for r in res if r != clean]

    # 4. 年代 (^d+0代$ or ^d+代$)
    m_dai = re.match(r'^(\d+)代$', clean)
    if m_dai:
        all_dais = ["10代", "20代", "30代", "40代", "50代", "60代", "70代", "80代", "アラサー", "アラフォー", "アラフィフ"]
        return "scale_dai", [d for d in all_dais if d != clean]

    # 5. 年齢・月齢
    m_age = re.match(r'^(\d+)(歳|才)$', clean)
    if m_age:
        curr_age = int(m_age.group(1))
        unit = m_age.group(2)
        common_ages = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        sorted_ages = sorted([a for a in common_ages if a != curr_age], key=lambda x: abs(x - curr_age))
        return "scale_age", [f"{a}{unit}" for a in sorted_ages]

    m_mon = re.match(r'^(\d+)(ヶ月|カ月|か月|ヵ月)$', clean)
    if m_mon:
        curr_m = int(m_mon.group(1))
        unit = m_mon.group(2)
        common_ms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        sorted_ms = sorted([m for m in common_ms if m != curr_m], key=lambda x: abs(x - curr_m))
        return "scale_month", [f"{m}{unit}" for m in sorted_ms]

    # 6. 寸法 (cm, mm, m)
    m_len = re.match(r'^(\d+)(cm|mm|m)$', clean, re.IGNORECASE)
    if m_len:
        curr_len = int(m_len.group(1))
        unit = m_len.group(2).lower()
        if unit == "cm":
            c_lens = [5, 10, 15, 20, 30, 40, 50, 60, 100]
        elif unit == "mm":
            c_lens = [1, 2, 3, 5, 8, 10, 12, 15, 20]
        else:
            c_lens = [1, 2, 3, 5, 10]
        sorted_lens = sorted([l for l in c_lens if l != curr_len], key=lambda x: abs(x - curr_len))
        return "scale_len", [f"{l}{unit}" for l in sorted_lens]

    # 7. 重量・容量 (g, kg, ml, l, L)
    m_wt = re.match(r'^(\d+)(g|kg|ml|l|cc)$', clean, re.IGNORECASE)
    if m_wt:
        curr_wt = int(m_wt.group(1))
        unit = m_wt.group(2)
        if unit.lower() in ["g", "グラム"]:
            c_wts = [50, 100, 150, 200, 250, 300, 500, 1000]
        elif unit.lower() == "kg":
            c_wts = [1, 2, 3, 5, 10]
        else:
            c_wts = [100, 200, 300, 500, 1000]
        sorted_wts = sorted([w for w in c_wts if w != curr_wt], key=lambda x: abs(x - curr_wt))
        return "scale_weight", [f"{w}{unit}" for w in sorted_wts]

    return None

def detect_semantic_family(term: str) -> Optional[Tuple[str, List[str]]]:
    """
    単語の意味・カテゴリ（色、スイーツ、穀物、調理器具、アプリ、家電、健康飲料、メンタル等）を判定し、同族単語リストを返す
    """
    clean = term.strip()

    # まずスケールパターンをチェック
    scale_res = detect_scale_family(clean)
    if scale_res:
        return scale_res

    # 1. 色ファミリー判定
    color_hit = False
    for c in COLORS_FULL:
        if clean == c or (clean.endswith("色") and c.startswith(clean[:-1])):
            color_hit = True
            break
    if color_hit:
        has_iro = clean.endswith("色")
        res = []
        for c in COLORS_FULL:
            if c == clean:
                continue
            if has_iro:
                formatted = c if c.endswith("色") or c in ["ピンク", "オレンジ", "ベージュ", "カーキ", "キャメル", "アイボリー"] else f"{c}色"
            else:
                formatted = c[:-1] if c.endswith("色") and len(c) > 1 else c
            if formatted not in res and formatted != clean:
                res.append(formatted)
        return "colors", res

    # 2. スマホアプリ・ツールジャンル
    for ag in APP_GENRES:
        if clean == ag or (len(clean) >= 2 and (clean in ag or ag in clean)):
            res = [a for a in APP_GENRES if a != clean]
            return "app_genres", res

    # 3. 調理器具・手段
    for ca in COOKING_APPLIANCES:
        if clean == ca or (len(clean) >= 2 and (clean in ca or ca in clean)):
            res = [c for c in COOKING_APPLIANCES if c != clean]
            return "cooking_appliances", res

    # 靴・フットウェア
    for fw in FOOTWEAR_LIST:
        if clean == fw or (len(clean) >= 3 and (clean in fw or fw in clean)):
            res = [f for f in FOOTWEAR_LIST if f != clean]
            return "footwear", res

    # 4. 洋菓子・スイーツ
    for sw in SWEETS_LIST:
        if clean == sw or (len(sw) >= 2 and (clean in sw or sw in clean)):
            res = [s for s in SWEETS_LIST if s != clean]
            return "sweets", res

    # 5. 主食・穀物
    for st in STAPLES_LIST:
        if clean == st or (len(st) >= 2 and (clean in st or st in clean)):
            res = [s for s in STAPLES_LIST if s != clean]
            return "staples", res

    # 6. 家電
    for ap in APPLIANCES_LIST:
        if clean == ap or (len(ap) >= 3 and (clean in ap or ap in clean)):
            res = [a for a in APPLIANCES_LIST if a != clean]
            return "appliances", res

    # 7. 健康飲料・食品
    for hd in HEALTH_DRINKS:
        if clean == hd or (len(hd) >= 3 and (clean in hd or hd in clean)):
            res = [h for h in HEALTH_DRINKS if h != clean]
            return "health_drinks", res

    # 8. 金具・手芸パーツ
    for hp in HARDWARE_PARTS:
        if clean == hp or (len(hp) >= 3 and (clean in hp or hp in clean)):
            res = [p for p in HARDWARE_PARTS if p != clean]
            return "hardware_parts", res

    # 9. メンタル・人間特性
    for mt in MENTAL_TRAITS:
        if clean == mt or (len(mt) >= 3 and (clean in mt or mt in clean)):
            res = [m for m in MENTAL_TRAITS if m != clean]
            return "mental_traits", res

    # 10. 洗車
    for cw in CAR_WASH_STYLES:
        if clean == cw or (len(cw) >= 3 and (clean in cw or cw in clean)):
            res = [c for c in CAR_WASH_STYLES if c != clean]
            return "car_wash", res

    return None

if __name__ == "__main__":
    for word in ["カメラ", "炊飯器", "茶色", "5号", "3合", "ケーキ"]:
        detected = detect_semantic_family(word)
        if detected:
            cat, sibs = detected
            print(f"[{word}] Category: {cat}, Siblings: {sibs[:5]}")
