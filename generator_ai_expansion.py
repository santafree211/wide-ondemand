# -*- coding: utf-8 -*-
# generator_ai_expansion.py
import urllib.request
import urllib.parse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def fetch_search_suggestions(query: str) -> List[str]:
    """
    GoogleサジェストAPIから検索候補を取得
    """
    url = "https://suggestqueries.google.com/complete/search?client=firefox&hl=ja&q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if len(data) > 1 and isinstance(data[1], list):
                return data[1]
    except Exception:
        pass
    return []

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

# -------------------------------------------------------------
# 【完全排除対象】地元系キーワード（地域・店舗・場所）
# -------------------------------------------------------------
LOCAL_EXCLUDE_TERMS = [
    "東京", "大阪", "名古屋", "福岡", "北海道", "沖縄", "京都", "横浜", "埼玉", "千葉", "神戸", "仙台", "広島",
    "新宿", "渋谷", "池袋", "銀座", "難波", "梅田", "天神", "博多",
    "都", "道", "府", "県", "市", "区", "町", "村", "駅", "駅前",
    "近く", "周辺", "店舗", "取扱店", "売り場", "コーナー", "売ってる場所", "どこで買える", "買える場所",
    "販売店", "ショップ", "実店舗", "店", "アクセス", "地図", "営業時間", "場所", "行き方", "フロア"
]

# -------------------------------------------------------------
# 【完全排除対象】エンタメ系キーワード（芸能・アニメ・ゲーム・漫画・音楽など）
# -------------------------------------------------------------
ENTERTAINMENT_EXCLUDE_TERMS = [
    "アニメ", "漫画", "マンガ", "キャラクター", "キャラ", "声優", "作画", "原作", "ネタバレ", "最終回", "打ち切り",
    "コスプレ", "フィギュア", "聖地", "作者", "登場人物", "イラスト", "同人", "グッズ",
    "芸能人", "タレント", "アイドル", "熱愛", "結婚", "彼氏", "彼女", "本名", "年齢", "身長", "wiki",
    "出身", "学歴", "炎上", "脱退", "解散", "事務所",
    "ゲーム", "攻略", "リセマラ", "最強", "ガチャ", "コード", "実況", "配信", "vtuber", "youtuber", "mod",
    "曲", "歌", "歌詞", "主題歌", "op", "ed", "ライブ", "コンサート", "映画", "ドラマ", "動画", "ファン", "pv", "mv"
]

# -------------------------------------------------------------
# 【全国市区町村マスター辞書のロード】
# -------------------------------------------------------------
MUNICIPALITIES_FILE = Path(__file__).parent / "japan_municipalities.json"
ALL_LOCALITIES = set()
if MUNICIPALITIES_FILE.exists():
    try:
        with open(MUNICIPALITIES_FILE, "r", encoding="utf-8") as f:
            ALL_LOCALITIES = set(json.load(f))
    except Exception:
        pass

def is_prohibited_term(term: str) -> bool:
    """
    地元系・エンタメ系・物販場所系の禁止キーワードが含まれているか判定
    """
    clean = term.lower().strip()
    if not clean:
        return True

    # 1. 全国市区町村マスターとの完全照合
    if clean in ALL_LOCALITIES:
        return True

    # 2. スペース区切りトークン照合
    tokens = clean.split()
    for tok in tokens:
        if tok in ALL_LOCALITIES:
            return True
        for loc in ALL_LOCALITIES:
            if len(loc) >= 2 and (tok == loc or tok.startswith(loc) or tok.endswith(loc)):
                return True

    # 3. 固定地元ワード照合
    for loc in LOCAL_EXCLUDE_TERMS:
        if loc in clean:
            return True

    # 4. 末尾行政区分・施設パターン照合
    if re.search(r'(都|道|府|県|市|区|町|村|駅|駅前|口|店|通り|線|ic|インター|丁目|番地)$', clean):
        return True

    if clean.endswith("写真") or clean.startswith("写真"):
        return True

    # 5. エンタメ系チェック
    for ent in ENTERTAINMENT_EXCLUDE_TERMS:
        if ent in clean:
            return True

    return False

# =============================================================
# 同族（ファミリー）定義辞書群
# =============================================================

# 色マスター（「〜色」および基本色）
COLORS_FULL = [
    "茶色", "緑色", "青色", "赤色", "黄色", "紫色", "肌色", "ピンク", "黒色", "白色",
    "水色", "黄緑", "灰色", "オレンジ", "金色", "銀色", "ベージュ", "紺色", "こげ茶",
    "えんじ色", "朱色", "藍色", "アイボリー", "カーキ", "オリーブ", "キャメル", "藤色",
    "深緑", "山吹色", "エメラルドグリーン", "ラベンダー", "ボルドー", "ターコイズ", "ワインレッド"
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
    単語の意味・カテゴリ（色、スイーツ、穀物、家電、健康飲料、メンタル等）を判定し、同族単語リストを返す
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

    # 2. 洋菓子・スイーツ
    for sw in SWEETS_LIST:
        if clean == sw or (len(sw) >= 2 and (clean in sw or sw in clean)):
            res = [s for s in SWEETS_LIST if s != clean]
            return "sweets", res

    # 3. 主食・穀物
    for st in STAPLES_LIST:
        if clean == st or (len(st) >= 2 and (clean in st or st in clean)):
            res = [s for s in STAPLES_LIST if s != clean]
            return "staples", res

    # 4. 家電
    for ap in APPLIANCES_LIST:
        if clean == ap or (len(ap) >= 3 and (clean in ap or ap in clean)):
            res = [a for a in APPLIANCES_LIST if a != clean]
            return "appliances", res

    # 5. 健康飲料・食品
    for hd in HEALTH_DRINKS:
        if clean == hd or (len(hd) >= 3 and (clean in hd or hd in clean)):
            res = [h for h in HEALTH_DRINKS if h != clean]
            return "health_drinks", res

    # 6. 金具・手芸パーツ
    for hp in HARDWARE_PARTS:
        if clean == hp or (len(hp) >= 3 and (clean in hp or hp in clean)):
            res = [p for p in HARDWARE_PARTS if p != clean]
            return "hardware_parts", res

    # 7. メンタル・人間特性
    for mt in MENTAL_TRAITS:
        if clean == mt or (len(mt) >= 3 and (clean in mt or mt in clean)):
            res = [m for m in MENTAL_TRAITS if m != clean]
            return "mental_traits", res

    # 8. 洗車
    for cw in CAR_WASH_STYLES:
        if clean == cw or (len(cw) >= 3 and (clean in cw or cw in clean)):
            res = [c for c in CAR_WASH_STYLES if c != clean]
            return "car_wash", res

    return None

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
    
    ★文脈と同族を見抜く機能:
    1. slot_aが色・号数・合数・家電・スイーツ等の同族を持つ場合、
       軸②「〇〇 [B]」の〇〇にその同族（緑色、青色、4号、6号、1合、4合等）を最優先で配置。
    2. 地元系（市区町村・店舗・場所）およびエンタメ系（アニメ・芸能・ゲーム）は完全事前排除。
    3. 知恵袋・個人ブログが居座る悩み・手順・代用系を最優先。
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

    # 高維持キーワード（悩み・トラブル・手順・代用）で優先補完
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

    # 軸①の確定（元KW完全除外、地元・エンタメ完全除外、きっかり25個）
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

    # 軸②の確定（元KW完全除外、地元・エンタメ完全除外、きっかり25個）
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
    for x in res['axis1']:
        print("  ", x)
    print(f"\nAxis 2 ({len(res['axis2'])} items):")
    for y in res['axis2']:
        print("  ", y)
    print(f"\nTotal generated: {res['total_count']}")
