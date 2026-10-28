# -*- coding: utf-8 -*-
"""
==============================================================================
【モジュール設計メモ】
■ モジュール名: main.py
■ カテゴリ: HTTP Server / Webルーティング専用ディスパッチャー
■ 責務・役割（Single Responsibility）:
  - サイドパネル用ローカルHTTPサーバー（デフォルトポート: 8899）の起動と維持。
  - Webリクエストのエンドポイント振り分け（ルーティング）のみに特化。
  - 実処理（ビジネスロジック）は単一責任サービスモジュールにすべて委譲する。
    - 状態・進捗・DB結果: service_state_manager
    - CSV入出力: service_csv_manager
    - リサーチ実行: service_research_runner
    - OAuth認証・状態: service_oauth_handler
    - 軸展開: generator_ai_expansion

■ 設計思想・背景:
  - 単一責任の原則（SRP）を徹底し、ファイルIOやビジネスロジックを一切排除。
  - 100行台の極めてクリーンで読みやすいディスパッチャーとして維持する。
==============================================================================
"""

import os
import sys
import json
from typing import Any
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 単一責任サービスモジュール群
from service_state_manager import get_form_state, save_form_state, get_research_progress, get_research_results
from service_csv_manager import export_research_csv, import_research_csv
from service_research_runner import start_research_job
from service_oauth_handler import check_system_api_status

PORT = int(os.environ.get("ANTIGRAVITY_SIDECAR_WEB_PORT", 8899))
HERE = Path(__file__).parent.resolve()

class WideStudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path
        query_params = parse_qs(parsed.query)

        if clean_path in ["", "/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            with open(HERE / "index.html", "rb") as f:
                self.wfile.write(f.read())
            return

        elif clean_path == "/api/state":
            self.send_json_response(get_form_state())
            return

        elif clean_path == "/api/status":
            api_status = check_system_api_status()
            resp = {
                "auth": {},
                "stats": {},
                "api_status": api_status,
                "quota_exhausted": api_status.get("quota_exhausted", False)
            }
            self.send_json_response(resp)
            return

        elif clean_path == "/oauth/login":
            try:
                from ubersuggest_token_manager import generate_oauth_authorization_url
                auth_url, _ = generate_oauth_authorization_url()
                self.send_response(302)
                self.send_header("Location", auth_url)
                self.end_headers()
            except Exception as e:
                self.send_error_response(500, f"Error starting OAuth: {e}")
            return

        elif clean_path == "/oauth/callback":
            code = query_params.get("code", [""])[0]
            state = query_params.get("state", [""])[0]
            err = query_params.get("error", [""])[0]
            if err or not code:
                self.send_html_response(400, f"<h2>OAuth Error: {err or 'Missing code'}</h2><p><a href='/'>Back</a></p>")
                return
            try:
                from ubersuggest_token_manager import exchange_code_for_token
                ok, err_msg = exchange_code_for_token(code, state)
                if ok:
                    html = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>OAuth Success</title><style>body{background:#0f172a;color:#f8fafc;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}.card{background:#1e293b;padding:32px;border-radius:12px;border:1px solid #38bdf8;text-align:center;box-width:400px;}h2{color:#38bdf8;}p{color:#94a3b8;font-size:14px;}</style></head><body><div class="card"><h2>Ubersuggest Connected!</h2><p>Auto-refresh active.</p></div><script>setTimeout(function(){if(window.opener){window.close();}else{window.location.href='/';}}, 2000);</script></body></html>'''
                    self.send_html_response(200, html)
                else:
                    self.send_html_response(400, f"<h2>Token Exchange Failed: {err_msg}</h2>")
            except Exception as e:
                self.send_html_response(500, f"<h2>Server Exception: {e}</h2>")
            return

        elif clean_path == "/api/progress":
            self.send_json_response(get_research_progress())
            return

        elif clean_path == "/api/results":
            target_seed = query_params.get("seed", [""])[0].strip()
            self.send_json_response(get_research_results(target_seed))
            return

        elif clean_path == "/api/expand":
            seed = query_params.get("seed", [""])[0]
            try:
                from generator_ai_expansion import generate_axes
                axes = generate_axes(seed)
            except Exception as e:
                axes = {"slot_a": "", "slot_b": "", "axis1": [], "axis2": [], "error": str(e)}
            self.send_json_response(axes)
            return

        elif clean_path == "/api/export_csv":
            target_seed = query_params.get("seed", [""])[0].strip()
            csv_bytes, export_path = export_research_csv(target_seed)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="wide_research_results.csv"')
            self.send_header("X-Saved-Path", export_path)
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        # 静的ファイル（JS, CSS等）にも Cache-Control を付与してブラウザキャッシュを根絶
        self.send_response(200)
        ctype = self.guess_type(clean_path)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        file_path = HERE / clean_path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")
        return

    def do_POST(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path
        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else ""

        if clean_path == "/api/state":
            try:
                state_data = json.loads(body) if body else {}
                save_form_state(state_data)
            except Exception:
                pass
            self.send_json_response({"status": "saved"})
            return

        elif clean_path == "/api/import_csv":
            res = import_research_csv(body)
            self.send_json_response(res)
            return

        elif clean_path == "/api/run":
            try:
                payload = json.loads(body) if body else {}
                res = start_research_job(payload)
                self.send_json_response(res)
            except Exception as e:
                self.send_json_response({"status": "ERROR", "message": str(e)}, status=500)
            return

        self.send_error(404, "Not Found")

    # ヘルパーメソッド
    def send_json_response(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_html_response(self, status: int, html_str: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_str.encode("utf-8"))

    def send_error_response(self, status: int, msg: str):
        self.send_response(status)
        self.end_headers()
        self.wfile.write(msg.encode("utf-8"))

def run():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, WideStudioHandler)
    print(f"wide Studio UI server listening on http://127.0.0.1:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run()
