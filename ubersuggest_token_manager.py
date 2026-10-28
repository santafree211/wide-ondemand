# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: ubersuggest_token_manager.py
■ カテゴリ: Auth Infrastructure / OAuthトークンライフサイクル管理
■ 責務・役割（Single Responsibility）:
  - Ubersuggest MCPのOAuthアクセストークンおよびリフレッシュトークンの自動延命・管理。
  - 有効期限前のプロアクティブ自動リフレッシュ（バッファ2時間）およびHTTP 401受信時のリアクティブリフレッシュ。
  - Antigravity各ディレクトリ間でのトークンファイル同期。
==============================================================================
"""

import os
import sys
import json
import time
import base64
import hashlib
import secrets
import threading
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

USER_HOME = Path(os.environ.get("USERPROFILE", "~")).expanduser()
PRIMARY_TOKEN_FILE = USER_HOME / ".gemini" / "antigravity" / "mcp_oauth_tokens.json"
SECONDARY_TOKEN_FILE = USER_HOME / ".gemini" / "antigravity-cli" / "mcp_oauth_tokens.json"
CREDENTIALS_FILE = USER_HOME / "ubersuggest_mcp_credentials.json"

TOKEN_ENDPOINT = "https://ubersuggest-mcp.neilpatelapi.com/token"
CLIENT_ID = "ubersuggest-mcp"
SCOPE = "profile domain keywords serp backlinks site_audit content projects utility"

_token_lock = threading.Lock()
_pkce_state_store: Dict[str, str] = {}  # state -> verifier


def get_token_file_paths():
    return [PRIMARY_TOKEN_FILE, SECONDARY_TOKEN_FILE]


def read_oauth_entry() -> Tuple[Optional[dict], Optional[dict]]:
    """Reads the stored OAuth data and the Ubersuggest entry."""
    for p in get_token_file_paths():
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                entry = data.get("https://ubersuggest-mcp.neilpatelapi.com/mcp")
                if entry and isinstance(entry, dict):
                    return data, entry
            except Exception:
                continue
    return None, None


def save_oauth_entry(access_token: str, refresh_token: str, expires_in: int = 172800) -> bool:
    """Saves new access and refresh tokens to all known configuration files."""
    with _token_lock:
        expiry_dt = datetime.now() + timedelta(seconds=expires_in)
        # Format as ISO 8601 string
        expiry_str = expiry_dt.strftime("%Y-%m-%dT%H:%M:%S.0000000+09:00")

        # 1. Update primary and secondary token files
        success = False
        for p in get_token_file_paths():
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                data = {}
                if p.exists():
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        data = {}
                
                if "https://ubersuggest-mcp.neilpatelapi.com/mcp" not in data:
                    data["https://ubersuggest-mcp.neilpatelapi.com/mcp"] = {}
                
                entry = data["https://ubersuggest-mcp.neilpatelapi.com/mcp"]
                entry["token_url"] = TOKEN_ENDPOINT
                entry["client_id"] = CLIENT_ID
                entry["token"] = {
                    "token_type": "Bearer",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expiry": expiry_str
                }
                
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                success = True
            except Exception as e:
                print(f"[TokenManager] Error saving to {p}: {e}", file=sys.stderr)

        # 2. Update credentials file if it exists
        if CREDENTIALS_FILE.exists():
            try:
                with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                if "auth" in cdata:
                    cdata["auth"]["access_token"] = access_token
                    cdata["auth"]["refresh_token"] = refresh_token
                    cdata["auth"]["expires_in"] = expires_in
                if "mcp_config" in cdata:
                    cdata["mcp_config"]["mcpServers"]["ubersuggest"]["headers"]["Authorization"] = f"Bearer {access_token}"
                with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
                    json.dump(cdata, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[TokenManager] Error saving to credentials file: {e}", file=sys.stderr)

        return success


def is_token_expiring_soon(buffer_hours: float = 2.0) -> bool:
    """Checks if the access token will expire within buffer_hours."""
    _, entry = read_oauth_entry()
    if not entry or "token" not in entry:
        return True
    
    expiry_str = entry["token"].get("expiry")
    if not expiry_str:
        return True
    
    try:
        clean_exp = expiry_str.split(".")[0]
        exp_dt = datetime.strptime(clean_exp, "%Y-%m-%dT%H:%M:%S")
        if datetime.now() + timedelta(hours=buffer_hours) >= exp_dt:
            return True
        return False
    except Exception:
        return True


def refresh_access_token() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Attempts to refresh the access token using the stored refresh_token.
    Returns: (success: bool, access_token: Optional[str], error_message: Optional[str])
    """
    _, entry = read_oauth_entry()
    if not entry or "token" not in entry:
        return False, None, "No token entry found."
    
    refresh_token = entry["token"].get("refresh_token")
    if not refresh_token:
        return False, None, "No refresh_token found in configuration."
    
    post_fields = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token
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
            new_ref = res_json.get("refresh_token") or refresh_token
            expires_in = int(res_json.get("expires_in", 172800))
            
            if new_acc:
                save_oauth_entry(new_acc, new_ref, expires_in)
                print(f"[TokenManager] Successfully refreshed access token. Valid for {expires_in} seconds.")
                return True, new_acc, None
            else:
                return False, None, "access_token missing in response."
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        if "invalid_grant" in err_body:
            return False, None, "INVALID_GRANT: Refresh token has been revoked or expired on server."
        return False, None, f"HTTPError {e.code}: {err_body}"
    except Exception as e:
        return False, None, str(e)


def get_current_access_token(auto_refresh: bool = True) -> Optional[str]:
    """
    Retrieves a valid access token. If near expiration and auto_refresh is True,
    it refreshes before returning.
    """
    _, entry = read_oauth_entry()
    if not entry or "token" not in entry:
        return None
    
    acc = entry["token"].get("access_token")
    if not acc:
        return None
    
    if auto_refresh and is_token_expiring_soon():
        ok, new_acc, _ = refresh_access_token()
        if ok and new_acc:
            return new_acc
    
    return acc


def generate_oauth_authorization_url(redirect_uri: str = "http://localhost:8899/oauth/callback") -> Tuple[str, str]:
    """
    Generates a PKCE challenge and authorization URL for interactive login.
    Returns (authorization_url, verifier)
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
    Exchanges an authorization code for access and refresh tokens.
    """
    verifier = _pkce_state_store.get(state)
    if not verifier:
        # Fallback to general verifier if state lost
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


if __name__ == "__main__":
    print("Testing token manager...")
    print("Expiring soon:", is_token_expiring_soon())
    print("Attempting refresh...")
    ok, token, err = refresh_access_token()
    print("Result:", ok, token[:15] if token else None, err)
