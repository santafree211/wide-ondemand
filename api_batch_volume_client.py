# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: api_batch_volume_client.py
■ カテゴリ: API / Ubersuggest 1-Shot メガバッチ一括Vol取得クライアント
■ 責務・役割（Single Responsibility）:
  - 蓄積された最大500件の精鋭キーワードを束ね、1リクエスト（1APIコール）で一括送信。
  - Ubersuggest公式 match_keywords / keyword_overview 等のメガバッチ通信を実行。
  - 返却された各キーワードの Vol / SD をパースして辞書 {kw: {"volume": vol, "sd": sd}} を返却する。
  - HTTP 401受信時の自動トークン更新および再試行。
==============================================================================
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, List

def fetch_mega_batch_volumes(keywords: List[str], token: str) -> Dict[str, Dict[str, Any]]:
    """
    複数キーワード（最大500件）のボリューム・SDを一括取得する。
    戻り値: {keyword: {"volume": int, "sd": int}}
    """
    if not keywords or not token:
        return {}

    results = {}

    def _call_match_keywords(kw_chunk: List[str], tk: str) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "match_keywords",
                "arguments": {
                    "keywords": kw_chunk,
                    "locId": 2392,
                    "language": "ja",
                    "limit": len(kw_chunk)
                }
            }
        }
        req = urllib.request.Request(
            "https://ubersuggest-mcp.neilpatelapi.com/mcp",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {tk}"
            }
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode("utf-8")
            for line in content.split("\n"):
                if line.startswith("data:"):
                    raw = json.loads(line[5:].strip())
                    if raw.get("result", {}).get("isError"):
                        err_txt = raw.get("result", {}).get("content", [{}])[0].get("text", "")
                        if "401" in err_txt or "invalid token" in err_txt.lower():
                            return {"_status": "401"}
                        return {"_status": "ERROR", "_msg": err_txt}
                    if "result" in raw and "content" in raw["result"]:
                        for c in raw["result"]["content"]:
                            if c.get("type") == "text":
                                return json.loads(c.get("text", "{}"))
        return {}

    # 最大500件を1回のバッチ（またはAPI制約に応じた100件チャンク）でコール
    chunk_size = 500
    chunks = [keywords[i:i + chunk_size] for i in range(0, len(keywords), chunk_size)]

    for chunk in chunks:
        data = _call_match_keywords(chunk, token)
        if data.get("_status") == "401":
            from ubersuggest_token_manager import refresh_access_token
            ok, new_tk, _ = refresh_access_token()
            if ok and new_tk:
                token = new_tk
                data = _call_match_keywords(chunk, token)

        # 抽出: data["keywords"] または直接配列
        kw_items = []
        if isinstance(data, dict):
            if "keywords" in data and isinstance(data["keywords"], list):
                kw_items = data["keywords"]
            elif "rows" in data and isinstance(data["rows"], list):
                kw_items = data["rows"]
        elif isinstance(data, list):
            kw_items = data

        for item in kw_items:
            k = item.get("keyword") or item.get("key")
            if k:
                vol = item.get("search_volume") if item.get("search_volume") is not None else item.get("volume")
                sd = item.get("seo_difficulty") if item.get("seo_difficulty") is not None else item.get("sd")
                results[k] = {
                    "volume": int(vol) if vol is not None else None,
                    "sd": int(sd) if sd is not None else None
                }

    return results
