# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: engine_gemini_client.py
■ カテゴリ: LLM Bridge / Gemini API 直接推論クライアント
■ 責務・役割（Single Responsibility）:
  - Google Gemini API (gemini-2.0-flash / gemini-1.5-flash) を呼び出し、
    シードキーワードから「文脈完全合致のブルーオーシャンKW（25件）」を直接生成する。
  - APIキー（GEMINI_API_KEY）が存在しない、またはネットワーク障害時は None を返し、
    上位モジュールがオフラインのオントロジー安全網へフォールバックできるようにする。
  - 応答形式のJSONパース・25件厳格整形に特化。
==============================================================================
"""

import os
import re
import json
from typing import List, Optional
from pathlib import Path

# .env の自動ロード（カレントまたは親階層）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except Exception:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

PROMPT_TEMPLATE = """あなたはSEOと検索心理の最高峰の専門家です。
以下のシードキーワードを徹底的に分析し、Googleサジェストの表面にはまだ現れていないが、
検索者が切実に抱えている「盲点・トラブル予防・深層ペイン・プロの極意」を突いた
【ブルーオーシャンキーワード（25件）】を考案・出力してください。

【対象シード】: {seed}

【絶対ルール】:
1. 対象の性質（オントロジー: ゲーム・学習・食品・道具・美容・制度など）を正確に理解すること。
   ※ 例: 学習やゲームに対して「一人暮らし」「100均」「業務用」などの不適切な単語を絶対に混ぜないこと。
2. 構成比率:
   - 【鋭い2語キーワード】: 15件（検索者がピンポイントで求める本質2語）
   - 【キラー意図3語キーワード】: 10件（「コツ 〇〇」「デメリット 〇〇」「失敗しない 〇〇」等、自然な3語）
3. 合計きっかり25件を出力すること。
4. 出力は余計な解説を一切含めず、キーワードのみを1行1件（改行区切り）で出力すること。
"""

def generate_keywords_via_gemini(seed: str) -> Optional[List[str]]:
    """
    Gemini APIを叩き、25件のブルーオーシャンキーワードを生成する。
    APIキー未設定やエラー時は None を返す。
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        # google-genai または google.generativeai を試行
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = PROMPT_TEMPLATE.format(seed=seed)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            raw_text = response.text
        except Exception:
            import google.generativeai as gai
            gai.configure(api_key=api_key)
            model = gai.GenerativeModel("gemini-1.5-flash")
            prompt = PROMPT_TEMPLATE.format(seed=seed)
            response = model.generate_content(prompt)
            raw_text = response.text

        if not raw_text:
            return None

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        cleaned = []
        for line in lines:
            # 番号やビュレット（1. や - ）を除去
            c = re.sub(r'^[\d\.\-\*\s]+', '', line).strip()
            c = re.sub(r'[\s\u3000]+', ' ', c)
            if c and len(c.split()) in [2, 3]:
                cleaned.append(c)

        if len(cleaned) >= 15:
            return cleaned[:25]
        return None

    except Exception as e:
        print(f"[Gemini Client Warning] {e}")
        return None
