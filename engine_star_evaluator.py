# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: engine_star_evaluator.py
■ カテゴリ: Evaluation / Google公式SERP星判定エンジン
■ 責務・役割（Single Responsibility）:
  - Ubersuggest公式の serp_analysis API (1日2,000回規模のGoogle実測リソース) を直接呼び出し、
    Google検索オーガニック1〜10位の生実測データ（順位・URL・ドメイン・公式DA）を取得する。
  - 公式DA（1〜9の一桁DA個人ブログ）および弱小競合パターン（知恵袋、Q&A、ママリ、無料ブログ等）を
    正確に照合し、Google実測に基づく星数（★3〜★0）を判定する。
  - note.comは除外。
==============================================================================
"""

import json
import re
import urllib.request
import urllib.parse
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

HERE = Path(__file__).parent.resolve()
PATTERN_FILE = HERE / "weak_competitor_patterns.json"

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

def load_weak_competitor_patterns() -> Dict[str, Any]:
    if PATTERN_FILE.exists():
        try:
            with open(PATTERN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "categories": {
            "qa_community": {
                "patterns": [
                    r"chiebukuro\.yahoo\.co\.jp",
                    r"detail\.chiebukuro\.yahoo\.co\.jp",
                    r"oshiete\.goo\.ne\.jp",
                    r"okwave\.jp",
                    r"komachi\.yomiuri\.co\.jp",
                    r"jp\.quora\.com",
                    r"q\.hatena\.ne\.jp"
                ]
            },
            "free_blog_diary": {
                "patterns": [
                    r"ameblo\.jp",
                    r"hatenablog\.(com|jp)",
                    r"hateblo\.jp",
                    r"livedoor\.(blog|jp)",
                    r"blog\.jp",
                    r"fc2\.com"
                ]
            }
        }
    }

WEAK_PATTERNS = load_weak_competitor_patterns()

def is_weak_competitor(domain: str, url: str = "") -> Tuple[bool, str, str]:
    """弱小競合（Q&A・知恵袋・無料ブログ・掲示板等）に合致するか判定"""
    clean_domain = domain.lower().strip()
    target_str = f"{clean_domain} {url}".lower()
    for cat_key, cat_val in WEAK_PATTERNS.get("categories", {}).items():
        patterns = cat_val.get("patterns", [])
        for p in patterns:
            try:
                if re.search(p, target_str):
                    return True, cat_key, cat_val.get("reason", "")
            except Exception:
                pass
    return False, "", ""

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

def evaluate_keyword_stars(keyword: str, token: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    純度100% Google公式実測SERP＆公式DAに基づく星判定パイプライン:
    1. Ubersuggest serp_analysis から Google検索上位10位のオーガニック生実測データを取得
    2. 公式DAが一桁 (1〜9) の独立個人ブログ ＝ ★
    3. 知恵袋などの弱小UGC・Q&Aサイト ＝ ★
    4. note.com は除外
    5. 星数（★3〜★0）を厳密算出
    """
    if not token:
        token = get_ubersuggest_token()

    serp_entries = fetch_serp_analysis_ubersuggest(keyword, token=token)

    single_digit_da_domains = []
    qa_domains = []
    analyzed_details = []

    if serp_entries:
        organic_rank = 0
        for entry in serp_entries:
            entry_type = entry.get("type", "")
            domain = entry.get("domain", "").lower()
            url = entry.get("url", "")
            da = entry.get("domainAuthority")

            if not domain or domain == "nodomain":
                continue

            # オーガニック枠のみカウント
            if entry_type == "organic":
                organic_rank += 1
                if organic_rank > 10:
                    break
            else:
                continue

            # 1. note.com は除外
            if "note.com" in domain:
                analyzed_details.append({
                    "rank": organic_rank,
                    "domain": domain,
                    "da": da,
                    "url": url,
                    "type": "NOTE_EXCLUDED"
                })
                continue

            # 2. 弱小競合（知恵袋・Q&A・無料ブログ等）判定
            is_weak, cat, reason = is_weak_competitor(domain, url)
            if is_weak:
                qa_domains.append(domain)
                analyzed_details.append({
                    "rank": organic_rank,
                    "domain": domain,
                    "da": da,
                    "url": url,
                    "type": "WEAK_COMPETITOR_STAR",
                    "category": cat
                })
                continue

            # 3. 公式実測DAによる一桁DA判定 (DA 1〜9)
            if da is not None and 1 <= int(da) <= 9:
                single_digit_da_domains.append({"domain": domain, "da": int(da)})
                analyzed_details.append({
                    "rank": organic_rank,
                    "domain": domain,
                    "da": int(da),
                    "url": url,
                    "type": "SINGLE_DIGIT_DA"
                })
            else:
                analyzed_details.append({
                    "rank": organic_rank,
                    "domain": domain,
                    "da": da,
                    "url": url,
                    "type": "HIGH_DA_AUTHORITY"
                })

    total_stars = len(single_digit_da_domains) + len(qa_domains)
    star_str = "★" * total_stars if total_stars > 0 else "-"

    meta = {
        "star_rating": star_str,
        "total_stars": total_stars,
        "single_digit_count": len(single_digit_da_domains),
        "single_digit_domains": single_digit_da_domains,
        "qa_count": len(qa_domains),
        "qa_domains": qa_domains,
        "details": analyzed_details,
        "source": "UBERSUGGEST_GOOGLE_OFFICIAL_SERP"
    }
    return star_str, meta

# 後方互換ラッパー: preflightでも公式Google実測SERPを直接呼び出す
def evaluate_keyword_stars_preflight(keyword: str) -> Tuple[str, Dict[str, Any]]:
    return evaluate_keyword_stars(keyword)

if __name__ == "__main__":
    kw = "スニーカー 厚底 歩きやすい"
    stars, meta = evaluate_keyword_stars(kw)
    print(f"Keyword: {kw}")
    print(f"Rating: {stars} (Total: {meta['total_stars']})")
    print(f"Single Digit DAs ({meta['single_digit_count']}):", meta["single_digit_domains"])
    print(f"QA/Weak Sites ({meta['qa_count']}):", meta["qa_domains"])
