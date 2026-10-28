# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: api_overview_client.py
■ カテゴリ: API / Ubersuggest keyword_overview 単体Vol/SD取得クライアント
■ 責務・役割（Single Responsibility）:
  - Ubersuggest公式 `keyword_overview` API（JSON-RPC 2.0）との通信に特化。
  - 星★ありの精鋭キーワードのみを対象に、公式実測ボリューム（search_volume）および難易度（sd）を取得する。
  - HTTP 401（トークン期限切れ）受信時の自動リフレッシュ再試行を自己完結で実行する。

■ 入出力仕様:
  - fetch_keyword_overview(kw: str, token: str) -> Dict[str, Any]
==============================================================================
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any

def fetch_keyword_overview(kw: str, token: str) -> Dict[str, Any]:
    """
    指定キーワードのボリューム・SEO難易度を Ubersuggest keyword_overview API から実測取得する
    """
    def _do_call(tk: str):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "keyword_overview",
                "arguments": {
                    "keyword": kw,
                    "locId": 2392,
                    "language": "ja"
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            for line in content.split("\n"):
                if line.startswith("data:"):
                    raw = json.loads(line[5:].strip())
                    if raw.get("result", {}).get("isError"):
                        err_txt = raw.get("result", {}).get("content", [{}])[0].get("text", "")
                        if "401" in err_txt or "invalid token" in err_txt.lower():
                            return "401"
                    if "result" in raw and "content" in raw["result"]:
                        for c in raw["result"]["content"]:
                            if c.get("type") == "text":
                                return json.loads(c.get("text", "{}"))
        return {}

    try:
        res = _do_call(token)
        if res == "401":
            from ubersuggest_token_manager import refresh_access_token
            ok, new_tk, _ = refresh_access_token()
            if ok and new_tk:
                res = _do_call(new_tk)
        if isinstance(res, dict):
            return res
    except urllib.error.HTTPError as e:
        if e.code == 401:
            try:
                from ubersuggest_token_manager import refresh_access_token
                ok, new_tk, _ = refresh_access_token()
                if ok and new_tk:
                    res = _do_call(new_tk)
                    if isinstance(res, dict):
                        return res
            except Exception:
                pass
    except Exception:
        pass
    return {}
