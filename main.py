# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: main.py
■ カテゴリ: HTTP Server / Webルーティング・ディスパッチャー
■ 責務・役割（Single Responsibility）:
  - サイドパネル用ローカルHTTPサーバー（デフォルトポート: 8899）の起動と維持。
  - Webリクエストのエンドポイント振り分け（ルーティング）のみに特化。
  - 実処理（ビジネスロジック）は単一責任サービスモジュールにすべて委譲する。
    - CSV入出力: service_csv_manager
    - リサーチ実行: service_research_runner
    - OAuth認証・状態: service_oauth_handler
    - 軸展開: generator_ai_expansion

■ 設計思想・背景:
  - 単一責任の原則（SRP）を徹底し、main.pyが肥大化して不具合の原因となるのを防ぐ。
  - HTTPメソッド（GET/POST）およびパスによるディスパッチ処理のみに専念させ、
    各サービスから返された結果を適切なHTTPステータスおよびContent-Typeでレスポンスする。

■ 入出力仕様:
  - [Port]: 8899 (環境変数 ANTIGRAVITY_SIDECAR_WEB_PORT でオーバーライド可能)
  - [GET エンドポイント]:
    - `/`, `/index.html`: UIフロントエンドHTML配信
    - `/api/state`: 直前のフォーム入力状態取得
    - `/api/status`: Ubersuggest API接続状態・認証診断結果取得
    - `/oauth/login`, `/oauth/callback`: OAuth認証フロー
    - `/api/progress`: リサーチ進行度（%・現在キーワード）取得
    - `/api/results`: keywords_db.json からの最新リサーチ結果取得
    - `/api/expand`: 前後2大固定軸の展開結果取得
    - `/api/export_csv`: リサーチ結果のExcel互換CSVダウンロード
  - [POST エンドポイント]:
    - `/api/state`: フォーム入力状態の保存
    - `/api/import_csv`: 外部SERP結果CSVのインポート
    - `/api/run`: SERP星判定またはUbersuggestリサーチジョブの起動

■ 厳格な制約・禁止事項:
  - main.py 内部で直接ファイルパースや外部APIコールなどの重いロジックを実装してはならない。
  - 常に委譲先サービスモジュール（service_*）を呼び出すこと。
==============================================================================
"""

import os
import sys
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("ANTIGRAVITY_SIDECAR_WEB_PORT", 8899))
HERE = Path(__file__).parent.resolve()
WIDE_DIR = Path(r"C:\Users\santa\OneDrive\prideall\projects\wide").resolve()
ONDEMAND_DIR = Path(r"C:\Users\santa\OneDrive\prideall\projects\wide-オンデマンド").resolve()

for p in [str(WIDE_DIR), str(ONDEMAND_DIR), str(HERE)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from service_csv_manager import export_research_csv, import_research_csv
from service_research_runner import start_research_job
from service_oauth_handler import check_system_api_status

STATE_FILE = HERE / "state.json"

class WideStudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path

        if clean_path in ["", "/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            with open(HERE / "index.html", "rb") as f:
                self.wfile.write(f.read())
            return

        elif clean_path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            state = {}
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        state = json.load(f)
                except Exception:
                    pass
            self.wfile.write(json.dumps(state, ensure_ascii=False).encode("utf-8"))
            return

        elif clean_path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            api_status = check_system_api_status()
            resp = {
                "auth": {},
                "stats": {},
                "api_status": api_status,
                "quota_exhausted": api_status.get("quota_exhausted", False)
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        elif clean_path == "/oauth/login":
            try:
                from ubersuggest_token_manager import generate_oauth_authorization_url
                auth_url, _ = generate_oauth_authorization_url()
                self.send_response(302)
                self.send_header("Location", auth_url)
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error starting OAuth: {e}".encode("utf-8"))
            return

        elif clean_path == "/oauth/callback":
            query_params = parse_qs(parsed.query)
            code = query_params.get("code", [""])[0]
            state = query_params.get("state", [""])[0]
            err = query_params.get("error", [""])[0]

            if err or not code:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h2>OAuth Error: {err or 'Missing code'}</h2><p><a href='/'>Back</a></p>".encode("utf-8"))
                return

            try:
                from ubersuggest_token_manager import exchange_code_for_token
                ok, err_msg = exchange_code_for_token(code, state)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if ok:
                    html = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>OAuth Success</title><style>body{background:#0f172a;color:#f8fafc;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}.card{background:#1e293b;padding:32px;border-radius:12px;border:1px solid #38bdf8;text-align:center;box-width:400px;}h2{color:#38bdf8;}p{color:#94a3b8;font-size:14px;}</style></head><body><div class="card"><h2>Ubersuggest Connected!</h2><p>Auto-refresh active.</p></div><script>setTimeout(function(){if(window.opener){window.close();}else{window.location.href='/';}}, 2000);</script></body></html>'''
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.wfile.write(f"<h2>Token Exchange Failed: {err_msg}</h2>".encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"<h2>Server Exception: {e}</h2>".encode("utf-8"))
            return

        elif clean_path == "/api/progress":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            prog_file = WIDE_DIR / "progress_status.json"
            prog = {"status": "IDLE", "current": 0, "total": 0, "percent": 0, "current_keyword": "", "message": ""}
            if prog_file.exists():
                try:
                    with open(prog_file, "r", encoding="utf-8") as f:
                        prog = json.load(f)
                except Exception:
                    pass
            self.wfile.write(json.dumps(prog, ensure_ascii=False).encode("utf-8"))
            return

        elif clean_path == "/api/results":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            items = []
            db_file = WIDE_DIR / "keywords_db.json"
            if db_file.exists():
                try:
                    with open(db_file, "r", encoding="utf-8-sig") as f:
                        raw = json.load(f)
                        items = raw.get("keywords", [])
                except Exception:
                    pass

            query_params = parse_qs(parsed.query)
            target_seed = query_params.get("seed", [""])[0].strip()
            if target_seed:
                norm_seed = target_seed.replace(" ", "").replace("　", "").lower()
                items = [
                    it for it in items
                    if it.get("seed_keyword", "").replace(" ", "").replace("　", "").lower() == norm_seed
                ]
            else:
                items = []

            self.wfile.write(json.dumps(items, ensure_ascii=False).encode("utf-8"))
            return

        elif clean_path == "/api/expand":
            query_params = parse_qs(parsed.query)
            seed = query_params.get("seed", [""])[0]
            try:
                from generator_ai_expansion import generate_axes
                axes = generate_axes(seed)
            except Exception as e:
                axes = {"slot_a": "", "slot_b": "", "axis1": [], "axis2": [], "error": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(axes, ensure_ascii=False).encode("utf-8"))
            return

        elif clean_path == "/api/export_csv":
            query_params = parse_qs(parsed.query)
            target_seed = query_params.get("seed", [""])[0].strip()
            csv_bytes, export_path = export_research_csv(target_seed)

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="wide_research_results.csv"')
            self.send_header("X-Saved-Path", export_path)
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path

        if clean_path == "/api/state":
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                state_data = json.loads(body)
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"status":"saved"}')
            return

        elif clean_path == "/api/import_csv":
            length = int(self.headers.get("content-length", 0))
            csv_text = self.rfile.read(length).decode("utf-8", errors="ignore") if length > 0 else ""
            res = import_research_csv(csv_text)
            self.send_response(200 if res.get("status") == "ok" else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return

        elif clean_path == "/api/run":
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            payload = json.loads(body)

            job_res = start_research_job(payload)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(job_res).encode("utf-8"))
            return

def run_server():
    server = HTTPServer(("127.0.0.1", PORT), WideStudioHandler)
    print(f"[wide-studio] Sidecar server running on port {PORT}...")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
