# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: api_serp_client.py
■ カテゴリ: API / Ubersuggest serp_analysis 公式通信専用クライアント
■ 責務・役割（Single Responsibility）:
  - Ubersuggest公式 `serp_analysis` API（JSON-RPC 2.0 / 1日2,000枠）とのHTTP通信に特化。
  - OAuthトークンを取得し、Googleオーガニック検索上位1〜10位の生実測データ（順位・URL・ドメイン・公式DA）を取得して返却する。
  - ネットワーク遅延・タイムアウト等の例外を安全に捕捉・吸収する。

■ 設計思想・背景:
  - 通信レイヤー（HTTP・トークン管理・JSONパース）を星判定ロジックから完全に分離し、
    ネットワーク処理の単一責任を担保する。

■ 入出力仕様:
  - Input: keyword: str, token: str (任意)
  - Output: List[Dict[str, Any]] (SERPエントリ配列)
==============================================================================
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any

def get_ubersuggest_token() -> str:
    """OAuthアクセストークンを取得"""
    try:
        from ubersuggest_token_manager import get_current_access_token
        tok = get_current_access_token(auto_refresh=True)
        if tok:
            return tok
    except Exception:
        pass
    user_home = Path(os.environ.get("USERPROFILE", "~")).expanduser()
    candidate_tokens = [
        user_home / ".gemini" / "antigravity" / "mcp_oauth_tokens.json",
        user_home / ".gemini" / "antigravity-cli" / "mcp_oauth_tokens.json"
    ]
    for tf in candidate_tokens:
        if tf.exists():
            try:
                with open(tf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "access_token" in data:
                            return data["access_token"]
                        for _, v in data.items():
                            if isinstance(v, dict) and "token" in v and "access_token" in v["token"]:
                                return v["token"]["access_token"]
                            if isinstance(v, dict) and "access_token" in v:
                                return v["access_token"]
            except Exception:
                pass
    return ""

def fetch_serp_analysis_ubersuggest(keyword: str, token: str = "") -> List[Dict[str, Any]]:
    """
    Ubersuggest公式 serp_analysis (Google実測SERP ＆ 公式実測DA) を1発取得
    1日2,000回規模の公式リソースを直接活用
    """
    if not token:
        token = get_ubersuggest_token()
    if not token:
        return []

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "serp_analysis",
            "arguments": {
                "keyword": keyword,
                "language": "ja",
                "locId": 2392
            }
        }
    }

    req = urllib.request.Request(
        "https://ubersuggest-mcp.neilpatelapi.com/mcp",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            content = resp.read().decode("utf-8")
            for line in content.split("\n"):
                if line.startswith("data:"):
                    raw_json = line[5:].strip()
                    parsed = json.loads(raw_json)
                    if "result" in parsed and "content" in parsed["result"]:
                        for c in parsed["result"]["content"]:
                            if c.get("type") == "text":
                                inner = json.loads(c.get("text", "{}"))
                                entries = inner.get("serpEntries", [])
                                if entries:
                                    return entries
    except Exception as e:
        print(f"[fetch_serp_analysis_ubersuggest error] {keyword}: {e}")
    return []
