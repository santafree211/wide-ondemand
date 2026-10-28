# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: api_suggest_client.py
■ カテゴリ: API / 外部通信クライアント
■ 責務・役割（Single Responsibility）:
  - 外部検索エンジン（Google Suggest API）との通信に特化し、候補クエリ文字列を取得する。
  - ネットワーク遅延・タイムアウト・HTTPエラー等の例外を自己完結で吸収し、安全なリスト型データを返す。

■ 設計思想・背景:
  - キーワード展開において、実際の検索者が打ち込んでいる生のサジェスト候補を1次情報として利用する。
  - 通信処理を他のロジック（構文解析やフィルタリング）と完全に分離することで、将来的なサジェストプロバイダの
    切り替え（Bing、Yahoo、Ubersuggest等）やモックテストへの差し替えを容易にする。

■ 入出力仕様:
  - [Input]:
    - query: str （例: "茶色 作り方 ", "カメラ アプリ "）
  - [Output]:
    - List[str] （検索候補の文字列配列。通信失敗やタイムアウト時は例外を送出せず空リスト [] を返却）

■ 内部アルゴリズム / 処理フロー:
  1. 入力クエリの前後の空白をトリム。空文字の場合は即座に空配列を返す。
  2. Googleサジェスト（client=firefox, hl=ja）のエンドポイントにURLエンコードしてリクエスト。
  3. User-Agentヘッダーを付与し、タイムアウト値（5秒）を設定して通信実行。
  4. レスポンスJSON（配列構造: [query, [suggestions]]）をパースし、候補リスト（data[1]）を取り出して返却。
  5. いかなる例外（タイムアウト、403、ネットワーク切断等）も捕捉し、ログ破綻を防ぐため安全に [] を返す。

■ 厳格な制約・禁止事項:
  - このモジュール内でキーワードのフィルタリングや加工を行ってはならない（filter_prohibited_terms の責務）。
  - 推定データやダミーデータを捏造して返却してはならない。失敗時は正直に空配列を返すこと。

■ 保守・修正時のガイドライン:
  - タイムアウト秒数（SUGGEST_TIMEOUT_SECONDS）は負荷とUXのバランスを考慮し、最大5秒以内を維持すること。
==============================================================================
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
