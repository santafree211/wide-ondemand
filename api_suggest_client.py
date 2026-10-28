# -*- coding: utf-8 -*-
"""
api_suggest_client.py
責務: 外部検索サジェストAPI（Google Suggest等）との通信・クエリ候補取得
Pure single-responsibility module.
"""

import json
import urllib.request
import urllib.parse
from typing import List

SUGGEST_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
SUGGEST_TIMEOUT_SECONDS = 5

def fetch_search_suggestions(query: str) -> List[str]:
    """
    GoogleサジェストAPIから検索候補文字列のリストを取得して返却する。
    通信失敗時やタイムアウト時は安全に空リスト [] を返す。
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    url = "https://suggestqueries.google.com/complete/search?client=firefox&hl=ja&q=" + urllib.parse.quote(clean_q)
    req = urllib.request.Request(url, headers={"User-Agent": SUGGEST_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=SUGGEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if len(data) > 1 and isinstance(data[1], list):
                return data[1]
    except Exception:
        pass
    return []

if __name__ == "__main__":
    import sys
    test_q = sys.argv[1] if len(sys.argv) > 1 else "茶色 作り方 "
    suggs = fetch_search_suggestions(test_q)
    print(f"Suggestions for '{test_q}' ({len(suggs)} items):")
    for s in suggs:
        print(" -", s)
