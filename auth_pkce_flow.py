# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: auth_pkce_flow.py
■ カテゴリ: Auth / OAuth 2.0 PKCE 認証フロー専用モジュール
■ 責務・役割（Single Responsibility）:
  - Ubersuggest MCPのPKCE（Proof Key for Code Exchange）認証チャレンジコード生成。
  - ブラウザログイン用の認可URL生成（generate_oauth_authorization_url）。
  - コールバックで受信した認可コードとアクセストークンの安全な交換（exchange_code_for_token）。

■ 設計思想・背景:
  - 初回ログイン・再認証時のみに使用されるPKCEコード交換フローを、
    常時稼働するトークン自動リフレッシュ管理から完全に分離・独立させる。

■ 入出力仕様:
  - [generate_oauth_authorization_url]: Input: redirect_uri -> Output: (auth_url, state)
  - [exchange_code_for_token]: Input: (code, state, redirect_uri) -> Output: (success, err_msg)
==============================================================================
"""

import json
import base64
import hashlib
import secrets
import urllib.request
import urllib.parse
from typing import Dict, Tuple, Optional

CLIENT_ID = "ubersuggest-mcp"
SCOPE = "profile domain keywords serp backlinks site_audit content projects utility"
TOKEN_ENDPOINT = "https://ubersuggest-mcp.neilpatelapi.com/token"

_pkce_state_store: Dict[str, str] = {}  # state -> verifier

def generate_oauth_authorization_url(redirect_uri: str = "http://localhost:8899/oauth/callback") -> Tuple[str, str]:
    """
    PKCEチャレンジと認可URLを生成
    Returns: (authorization_url, state)
    """
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")
    state = secrets.token_urlsafe(16)
    
    _pkce_state_store[state] = verifier
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state
    }
    auth_url = f"https://ubersuggest-mcp.neilpatelapi.com/authorize?{urllib.parse.urlencode(params)}"
    return auth_url, state

def exchange_code_for_token(code: str, state: str, redirect_uri: str = "http://localhost:8899/oauth/callback") -> Tuple[bool, Optional[str]]:
    """
    認可コードをアクセストークンおよびリフレッシュトークンと交換して保存
    """
    from ubersuggest_token_manager import save_oauth_entry

    verifier = _pkce_state_store.get(state)
    if not verifier:
        verifier = _pkce_state_store.get("latest", "")
    
    post_fields = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier
    }
    encoded_data = urllib.parse.urlencode(post_fields).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=encoded_data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "AntigravityMCP/2.0"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            res_json = json.loads(resp_body)
            new_acc = res_json.get("access_token")
            new_ref = res_json.get("refresh_token")
            expires_in = int(res_json.get("expires_in", 172800))
            if new_acc and new_ref:
                save_oauth_entry(new_acc, new_ref, expires_in)
                return True, None
            return False, "Response missing access_token or refresh_token."
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        return False, f"HTTPError {e.code}: {err_body}"
    except Exception as e:
        return False, str(e)
