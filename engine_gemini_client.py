# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: engine_gemini_client.py
■ カテゴリ: LLM Bridge / Gemini API 直接推論クライアント
■ 責務・役割（Single Responsibility）:
  - Google Gemini API (gemini-3.8-flash等) を呼び出し、
    シードキーワードから「ブルーオーシャンKW（25件）」および「同族カテゴリ・エンティティ（25件）」を直接推論。
  - APIキー未設定やエラー時は None を返し、安全網へフォールバック。
==============================================================================
"""

import os
import re
from typing import List, Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except Exception:
    pass

MODELS_TO_TRY = ["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

PROMPT_TEMPLATE = """あなたはSEOと検索心理の最高峰の専門家です。
以下のシードキーワードを徹底的に分析し、Googleサジェストの表面にはまだ現れていないが、
検索者が切実に抱えている「盲点・トラブル予防・深層ペイン・プロの極意」を突いた
【ブルーオーシャンキーワード（25件）】を考案・出力してください。

【対象シード】: {seed}

【絶対ルール】:
1. 対象の性質（オントロジー: ゲーム・学習・食品・道具・美容・制度など）を正確に理解すること。
2. 構成比率:
   - 【鋭い2語キーワード】: 15件
   - 【キラー意図3語キーワード】: 10件
3. 合計きっかり25件を出力すること。余計な解説は一切不要（1行1件）。
"""

ENTITY_PROMPT_TEMPLATE = """シードキーワード「{entity} {suffix}」において、「{entity}」と同列の業界・カテゴリ・関連アイテム・競合概念を25個挙げてください。
【例】:
- 「登山 ブランド」➡ アウトドア, キャンプ, トレッキング, クライミング, スキー, 登山靴, ザック, ウェア, テント, マウンテンパーカー, ノースフェイス, パタゴニア, モンベル, マムート, コロンビア
- 「万年筆 おすすめ」➡ ボールペン, シャーペン, ガラスペン, 高級筆記具, インク, ノート, 手帳, 万年筆インク

【対象】: 「{entity} {suffix}」の「{entity}」
【条件】: 余計な解説、番号、記号は一切含めず、単語のみを1行1件（改行区切り）で25個出力してください。
"""

def _call_gemini_text(prompt: str) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    raw_text = ""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for m in MODELS_TO_TRY:
            try:
                response = client.models.generate_content(model=m, contents=prompt)
                if response and response.text:
                    return response.text
            except Exception:
                continue
    except Exception:
        pass

    try:
        import google.generativeai as gai
        gai.configure(api_key=api_key)
        for m in MODELS_TO_TRY:
            try:
                model = gai.GenerativeModel(m)
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text
            except Exception:
                continue
    except Exception:
        pass
    return None

def generate_keywords_via_gemini(seed: str) -> Optional[List[str]]:
    """Gemini APIで25件のブルーオーシャンKWを生成"""
    prompt = PROMPT_TEMPLATE.format(seed=seed)
    raw = _call_gemini_text(prompt)
    if not raw:
        return None
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        c = re.sub(r'^[\d\.\-\*\s]+', '', line).strip()
        c = re.sub(r'[\s\u3000]+', ' ', c)
        if c and len(c.split()) in [2, 3]:
            cleaned.append(c)
    return cleaned[:25] if len(cleaned) >= 15 else None

def infer_related_entities_via_gemini(seed_entity: str, suffix: str) -> Optional[List[str]]:
    """Gemini APIで軸②用の同族・関連カテゴリ・アイテム（25件）を推論"""
    prompt = ENTITY_PROMPT_TEMPLATE.format(entity=seed_entity, suffix=suffix)
    raw = _call_gemini_text(prompt)
    if not raw:
        return None
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        c = re.sub(r'^[\d\.\-\*\s]+', '', line).strip()
        c = re.sub(r'[\s\u3000]+', ' ', c)
        if c and len(c) >= 2 and c != seed_entity:
            cleaned.append(c)
    return cleaned[:25] if len(cleaned) >= 10 else None
