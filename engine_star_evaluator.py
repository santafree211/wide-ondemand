# engine_star_evaluator.py
import re
import json
import urllib.request
import urllib.parse
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Q&A sites definition (知恵袋、教えてgoo、OKWave、発言小町等)
QA_DOMAINS = [
    "chiebukuro.yahoo.co.jp",
    "detail.chiebukuro.yahoo.co.jp",
    "oshiete.goo.ne.jp",
    "okwave.jp",
    "komachi.yomiuri.co.jp",
    "q.hatena.ne.jp",
    "teratail.com"
]

HERE = Path(__file__).parent.resolve()
DA_CACHE_FILE = HERE / "domain_da_cache.json"

def get_ubersuggest_token() -> str:
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

def load_da_cache() -> Dict[str, int]:
    if DA_CACHE_FILE.exists():
        try:
            with open(DA_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_da_cache(cache: Dict[str, int]):
    try:
        with open(DA_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def fetch_domain_da(domain: str, token: str = "") -> int:
    """
    Ubersuggest API (domain_overview) を呼び出してDAを取得（キャッシュ優先）
    """
    clean_domain = domain.lower().strip()
    # ポータルやサブドメインの正規化
    if clean_domain.startswith("www."):
        clean_domain = clean_domain[4:]

    cache = load_da_cache()
    if clean_domain in cache:
        return cache[clean_domain]

    # 明らかな超大手・公的機関・ECはAPI節約のため高DA扱い
    high_da_keywords = ["yahoo.co.jp", "rakuten.co.jp", "amazon.co.jp", "kakaku.com", "my-best.com", "dji.com", "ecoflow.com", "ankerjapan.com", "jackery.jp", "apple.com", "google.com", "mhlw.go.jp", "go.jp", "ac.jp", "lg.jp"]
    for h in high_da_keywords:
        if clean_domain.endswith(h) or clean_domain == h:
            cache[clean_domain] = 50
            save_da_cache(cache)
            return 50

    if not token:
        token = get_ubersuggest_token()

    if not token:
        return 0

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "domain_overview",
            "arguments": {
                "domain": clean_domain,
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
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8")
            da = 0
            for line in content.split("\n"):
                if line.startswith("data:"):
                    raw_json = line[5:].strip()
                    parsed = json.loads(raw_json)
                    if "result" in parsed and "content" in parsed["result"]:
                        for c in parsed["result"]["content"]:
                            if c.get("type") == "text":
                                inner = json.loads(c.get("text", "{}"))
                                if "domainAuthority" in inner:
                                    da = int(inner["domainAuthority"])
                                    break
            cache[clean_domain] = da
            save_da_cache(cache)
            return da
    except Exception:
        return 0

def fetch_serp_analysis_ubersuggest(keyword: str, token: str = "") -> List[Dict[str, Any]]:
    """
    Ubersuggest公式 serp_analysis (Google実測SERP ＆ 公式実測DA) を1発取得
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
        with urllib.request.urlopen(req, timeout=12) as resp:
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
        print(f"[fetch_serp_analysis_ubersuggest error] {e}")
    return []

def fetch_serp_domains(keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    検索上位10件のドメイン・URL・種別（QA/note）を取得 (Googleフォールバック用)
    """
    url = "https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(keyword)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    
    entries = []
    seen_domains = set()
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            links = re.findall(r'<a\s+[^>]*href=["\'](https?://[^"\']+)["\']', html)
            
            for link in links:
                try:
                    parsed = urllib.parse.urlparse(link)
                    host = parsed.netloc.lower()
                    if not host:
                        continue
                    
                    if "yahoo.co.jp" in host and "chiebukuro.yahoo.co.jp" not in host:
                        continue
                    if any(x in host for x in ["google.", "search.yahoo", "support.yahoo", "help.yahoo", "w3.org", "schema.org"]):
                        continue
                    
                    if host in seen_domains:
                        continue
                    
                    seen_domains.add(host)
                    
                    is_qa = any(qa in host for qa in QA_DOMAINS)
                    is_note = "note.com" in host
                    
                    entries.append({
                        "domain": host,
                        "url": link,
                        "is_qa": is_qa,
                        "is_note": is_note
                    })
                    
                    if len(entries) >= limit:
                        break
                except Exception:
                    continue
    except Exception as e:
        print(f"[fetch_serp_domains error] {e}")
        
    return entries

def evaluate_keyword_stars(keyword: str, token: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    真の星判定ロジック（Google SERP実測最優先パイプライン）:
    1. Ubersuggest serp_analysis から Google 検索上位10位の生実測データ（ドメイン・DA）を取得
    2. DAが一桁 (1〜9) のサイト数 ＝ ★
    3. 知恵袋などのQ&Aサイト ＝ ☆扱い (加点)
    4. noteは除外
    5. serp_analysis が取得できない場合のみフォールバック
    """
    if not token:
        token = get_ubersuggest_token()

    # パイプライン1: Ubersuggest Google公式SERP実測
    serp_entries = fetch_serp_analysis_ubersuggest(keyword, token=token)
    
    single_digit_da_domains = []
    qa_domains = []
    analyzed_details = []

    if serp_entries:
        # 上位10位のオーガニック枠を精査
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

            is_qa = any(qa in domain for qa in QA_DOMAINS)
            is_note = "note.com" in domain

            # 1. noteは除く
            if is_note:
                analyzed_details.append({"rank": organic_rank, "domain": domain, "da": da, "url": url, "type": "NOTE_EXCLUDED"})
                continue

            # 2. 知恵袋などのQ&Aサイトは☆扱い
            if is_qa:
                qa_domains.append(domain)
                analyzed_details.append({"rank": organic_rank, "domain": domain, "da": da, "url": url, "type": "QA_SITE_STAR"})
                continue

            # 3. 通常ドメインのDA判定 (公式実測DA)
            if da is not None and 1 <= int(da) <= 9:
                single_digit_da_domains.append({"domain": domain, "da": int(da)})
                analyzed_details.append({"rank": organic_rank, "domain": domain, "da": int(da), "url": url, "type": "SINGLE_DIGIT_DA"})
            else:
                analyzed_details.append({"rank": organic_rank, "domain": domain, "da": da, "url": url, "type": "NORMAL_DOMAIN"})

    else:
        # フォールバックパイプライン
        entries = fetch_serp_domains(keyword, limit=10)
        for item in entries:
            domain = item["domain"]
            is_qa = item.get("is_qa", False)
            is_note = item.get("is_note", False)
            
            if is_note:
                analyzed_details.append({"domain": domain, "da": None, "type": "NOTE_EXCLUDED"})
                continue
                
            if is_qa:
                qa_domains.append(domain)
                analyzed_details.append({"domain": domain, "da": None, "type": "QA_SITE_STAR"})
                continue
                
            da = fetch_domain_da(domain, token=token)
            if 1 <= da <= 9:
                single_digit_da_domains.append({"domain": domain, "da": da})
                analyzed_details.append({"domain": domain, "da": da, "type": "SINGLE_DIGIT_DA"})
            else:
                analyzed_details.append({"domain": domain, "da": da, "type": "NORMAL_DOMAIN"})

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
        "source": "UBERSUGGEST_GOOGLE_SERP" if serp_entries else "FALLBACK_SERP"
    }
    return star_str, meta

if __name__ == "__main__":
    kw = "ポータブル電源 寿命"
    stars, meta = evaluate_keyword_stars(kw)
    print(f"Keyword: {kw}")
    print(f"Rating: {stars} (Total: {meta['total_stars']})")
    print(f"Single Digit DAs ({meta['single_digit_count']}):", meta['single_digit_domains'])
    print(f"QA Sites ({meta['qa_count']}):", meta['qa_domains'])
