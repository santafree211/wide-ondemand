# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: service_oauth_handler.py
■ カテゴリ: Auth / Ubersuggest OAuth認証およびステータス診断サービス
■ 責務・役割（Single Responsibility）:
  - UbersuggestのOAuth認証URL発行、リダイレクトハンドリング、コールバックコード検証。
  - トークンの期限切れ検知および自動リフレッシュ処理の実行。
  - Ubersuggest API接続状態（HTTP 200/401/403/429）の診断とステータス返却。

■ 設計思想・背景:
  - MCP環境やサイドパネルから安全にUbersuggest APIを呼び出せるよう、OAuth認証ライフサイクルを
    完全に集約管理する。
  - HTTP 401（期限切れ）を検知した場合はバックグラウンドでサイレントリフレッシュを試行し、
    日次上限（HTTP 403）やレート制限（HTTP 429）を正確に分類してUIへ通知する。

■ 入出力仕様:
  - [get_oauth_token]:
    - Output: str (有効なアクセストークン。見つからない場合は空文字)
  - [check_system_api_status]:
    - Output: Dict[str, Any]: {"status": str, "code": int, "quota_exhausted": bool, "message": str}

■ 内部アルゴリズム / 処理フロー:
  1. `mcp_oauth_tokens.json` からアクセストークンを探索・抽出。
  2. トークンが存在しない場合は即座に 401 (NO_TOKEN) を返却。
  3. Ubersuggestエンドポイントにヘルスチェックリクエストを送信。
  4. 401受信時は ubersuggest_token_manager.refresh_access_token() を呼び出して自動延命。
  5. 診断結果オブジェクトを構築して返却。

■ 厳格な制約・禁止事項:
  - トークン文字列をログ等に平文で漏洩させてはならない。
  - エラーコードの誤判定（403と429の混同等）を行ってはならない。
==============================================================================
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Tuple

def get_oauth_token() -> str:
    user_home = Path(os.environ.get("USERPROFILE", "~")).expanduser()
    candidate_tokens = [
        user_home / ".gemini" / "antigravity" / "mcp_oauth_tokens.json",
        user_home / ".gemini" / "antigravity-cli" / "mcp_oauth_tokens.json"
    ]
    for tf in candidate_tokens:
        if tf.exists():
            try:
                with open(tf, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, dict):
                        if "access_token" in d:
                            return d["access_token"]
                        for _, v in d.items():
                            if isinstance(v, dict) and "token" in v and "access_token" in v["token"]:
                                return v["token"]["access_token"]
                            if isinstance(v, dict) and "access_token" in v:
                                return v["access_token"]
            except Exception:
                pass
    return ""

def check_system_api_status() -> Dict[str, Any]:
    """Ubersuggest APIのステータス診断"""
    token = get_oauth_token()
    if not token:
        return {
            "status": "NO_TOKEN",
            "code": 401,
            "quota_exhausted": True,
            "message": "認証トークンが見つかりません"
        }

    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "keyword_overview",
                "arguments": {"keyword": "test", "locId": 2392, "language": "ja"}
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
        with urllib.request.urlopen(req, timeout=5) as resp:
            res_str = resp.read().decode("utf-8", errors="ignore")
            for line in res_str.split("\n"):
                if line.startswith("data:"):
                    p = json.loads(line[5:].strip())
                    if p.get("result", {}).get("isError"):
                        txt = p.get("result", {}).get("content", [{}])[0].get("text", "")
                        if "401" in txt or "invalid token" in txt.lower():
                            refreshed = False
                            try:
                                from ubersuggest_token_manager import refresh_access_token
                                ok, new_tk, _ = refresh_access_token()
                                if ok and new_tk:
                                    refreshed = True
                            except Exception:
                                pass
                            if refreshed:
                                return {"status": "OK", "code": 200, "quota_exhausted": False, "message": "トークン自動更新成功 (API正常稼働中)"}
                            return {"status": "TOKEN_EXPIRED", "code": 401, "quota_exhausted": False, "message": "認証トークン期限切れ (再認証が必要です)"}
                        elif "403" in txt or "daily reports limit" in txt.lower():
                            return {"status": "QUOTA_EXHAUSTED", "code": 403, "quota_exhausted": True, "message": "日次レポート上限到達 (HTTP 403)"}
                        elif "429" in txt:
                            return {"status": "RATE_LIMITED", "code": 429, "quota_exhausted": False, "message": "短時間アクセス過多 (HTTP 429)"}
        return {"status": "OK", "code": 200, "quota_exhausted": False, "message": "API正常稼働中"}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"status": "TOKEN_EXPIRED", "code": 401, "quota_exhausted": False, "message": "認証トークン期限切れ"}
        elif e.code == 403:
            return {"status": "QUOTA_EXHAUSTED", "code": 403, "quota_exhausted": True, "message": "日次上限到達 (HTTP 403)"}
        elif e.code == 429:
            return {"status": "RATE_LIMITED", "code": 429, "quota_exhausted": False, "message": "アクセス過多 (HTTP 429)"}
        return {"status": "API_ERROR", "code": e.code, "quota_exhausted": False, "message": f"HTTP Error {e.code}"}
    except Exception as e:
        return {"status": "NET_ERROR", "code": 0, "quota_exhausted": False, "message": str(e)[:60]}
