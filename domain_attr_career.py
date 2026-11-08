# -*- coding: utf-8 -*-
"""
=============================================================================
【モジュール設計メモ】
■ モジュール名: domain_attr_career.py
■ カテゴリ: Domain Attribute / ⑪ 仕事・キャリア・転職・退職系属性判定モジュール
■ 責務・役割（Single Responsibility）:
  - キーワード末尾が「転職」「退職」「辞めたい」「面接」「志望動機」「自己PR」
    「職務経歴書」「履歴書」「年収」「初任給」「ボーナス」「手取り」「パワハラ」「残業」等の
    ビジネス・キャリア・就労属性に該当するか判定する。
  - 「美味しい」「隠し味」「女子ウケ」「垢抜け」「修理」「接続」「初期化」「自作」等の
    グルメ・外見・機械工作系プレフィックスとの意味破綻（例: 「美味しい 転職」「女子ウケ 志望動機」等）を検知・排除する。
  - キャリア・転職系に特化した高単価・高CTRキラープレフィックス（例文、書き方、理由、未経験等）を供給する。
=============================================================================
"""

from typing import List

# 仕事・キャリア・転職・退職系サフィックス
CAREER_SUFFIXES = [
    "転職", "退職", "辞めたい", "面接", "志望動機", "自己PR", "職務経歴書",
    "履歴書", "年収", "初任給", "ボーナス", "手取り", "有給", "求人",
    "キャリア", "出世", "異動", "パワハラ", "残業", "退職金", "休職"
]

# キャリア系と衝突して意味破綻を起こすグルメ・外見・機械工作系プレフィックス
CAREER_INCOHERENT_PREFIXES = [
    "美味しい", "隠し味", "黄金比", "女子ウケ", "垢抜け", "体型カバー",
    "修理", "直し方", "接続", "初期化", "自作", "工作", "日持ち", "賞味期限"
]

# 仕事・キャリア系に最適化された高品質キラープレフィックス（30件）
CAREER_KILLER_PREFIXES = [
    "例文", "書き方", "理由", "対策", "質問", "伝え方", "切り出し方", "代行",
    "未経験", "平均", "相場", "スケジュール", "年代別", "タイミング", "相談",
    "エージェント", "成功例", "失敗例", "自己分析", "志望理由", "マナー",
    "いつ言う", "メール", "電話", "準備", "内定", "交渉", "退職理由",
    "転職先", "強み"
]

def match_domain_career(suffix: str) -> bool:
    """
    指定されたsuffixが仕事・キャリア系属性に属するか判定する。
    """
    clean_s = suffix.strip()
    s_tokens = clean_s.split()
    s_last = s_tokens[-1] if s_tokens else clean_s
    return any(s_last == c or s_last.endswith(c) for c in CAREER_SUFFIXES)

def is_incoherent_career(prefix: str, suffix: str) -> bool:
    """
    キャリア系サフィックスに対し、グルメ・外見語が結合して意味破綻していないか判定する。
    破綻している場合は True を返す。
    """
    clean_p = prefix.strip()
    for inc in CAREER_INCOHERENT_PREFIXES:
        if clean_p == inc or clean_p.endswith(inc) or clean_p.startswith(inc):
            return True
    return False

def get_fallback_career_prefixes() -> List[str]:
    """
    仕事・キャリア系に最適なキラープレフィックスリストを返す。
    """
    return list(CAREER_KILLER_PREFIXES)
