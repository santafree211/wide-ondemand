import os
import sys
import json
import time
import glob
import subprocess
import urllib.request
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("ANTIGRAVITY_SIDECAR_WEB_PORT", 8899))
HERE = Path(__file__).parent.resolve()
WIDE_DIR = Path(r"C:\Users\santa\OneDrive\prideall\projects\wide").resolve()
ONDEMAND_DIR = Path(r"C:\Users\santa\OneDrive\prideall\projects\wide-オンデマンド").resolve()

# サービスモジュールのインポート
if str(ONDEMAND_DIR) not in sys.path:
    sys.path.insert(0, str(ONDEMAND_DIR))

try:
    from service_data_manager import DataManager
except Exception:
    DataManager = None

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
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
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
            auth_info = {}
            stats = {}
            if DataManager:
                try:
                    auth_info = DataManager.check_ubersuggest_auth_status()
                    stats = DataManager.get_summary_stats()
                except Exception:
                    pass

            # UbersuggestのリアルタイムHTTPエラーステータス診断
            api_status = {
                "status": "OK",
                "code": 200,
                "quota_exhausted": False,
                "message": "API正常稼働中"
            }
            token = ""
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
                                    token = d["access_token"]
                                for _, v in d.items():
                                    if isinstance(v, dict) and "token" in v and "access_token" in v["token"]:
                                        token = v["token"]["access_token"]
                                    if isinstance(v, dict) and "access_token" in v:
                                        token = v["access_token"]
                    except Exception:
                        pass
                if token:
                    break

            if not token:
                api_status = {
                    "status": "NO_TOKEN",
                    "code": 401,
                    "quota_exhausted": True,
                    "message": "認証トークンが見つかりません"
                }
            else:
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
                        res_bytes = resp.read()
                        res_str = res_bytes.decode("utf-8", errors="ignore")
                        for line in res_str.split("\n"):
                            if line.startswith("data:"):
                                p = json.loads(line[5:].strip())
                                if p.get("result", {}).get("isError"):
                                    txt = p.get("result", {}).get("content", [{}])[0].get("text", "")
                                    if "401" in txt or "invalid token" in txt.lower():
                                        # Attempt silent auto-refresh
                                        refreshed = False
                                        try:
                                            from ubersuggest_token_manager import refresh_access_token
                                            ok, new_tk, _ = refresh_access_token()
                                            if ok and new_tk:
                                                refreshed = True
                                        except Exception:
                                            pass
                                        if refreshed:
                                            api_status = {
                                                "status": "OK",
                                                "code": 200,
                                                "quota_exhausted": False,
                                                "message": "トークン自動更新成功 (API正常稼働中)"
                                            }
                                        else:
                                            api_status = {
                                                "status": "TOKEN_EXPIRED",
                                                "code": 401,
                                                "quota_exhausted": False,
                                                "message": "認証トークン期限切れ (HTTP 401: Invalid Token - 再認証が必要です)"
                                            }
                                    elif "403" in txt or "daily reports limit" in txt.lower() or "quota is exhausted" in txt.lower():
                                        api_status = {
                                            "status": "QUOTA_EXHAUSTED",
                                            "code": 403,
                                            "quota_exhausted": True,
                                            "message": "日次レポート上限到達 (HTTP 403: Daily Limit 100到達)"
                                        }
                                    elif "429" in txt or "rate limit" in txt.lower():
                                        api_status = {
                                            "status": "RATE_LIMITED",
                                            "code": 429,
                                            "quota_exhausted": False,
                                            "message": "短時間アクセス過多 (HTTP 429: Rate Limited - 1分お待ちください)"
                                        }
                                    else:
                                        api_status = {
                                            "status": "API_ERROR",
                                            "code": 500,
                                            "quota_exhausted": False,
                                            "message": f"APIエラー: {txt[:80]}"
                                        }
                except urllib.error.HTTPError as e:
                    if e.code == 401:
                        # Attempt silent auto-refresh
                        refreshed = False
                        try:
                            from ubersuggest_token_manager import refresh_access_token
                            ok, new_tk, _ = refresh_access_token()
                            if ok and new_tk:
                                refreshed = True
                        except Exception:
                            pass
                        if refreshed:
                            api_status = {
                                "status": "OK",
                                "code": 200,
                                "quota_exhausted": False,
                                "message": "トークン自動更新成功 (API正常稼働中)"
                            }
                        else:
                            api_status = {
                                "status": "TOKEN_EXPIRED",
                                "code": 401,
                                "quota_exhausted": False,
                                "message": "認証トークン期限切れ (HTTP 401: Invalid Token - 再認証が必要です)"
                            }
                    elif e.code == 403:
                        api_status = {
                            "status": "QUOTA_EXHAUSTED",
                            "code": 403,
                            "quota_exhausted": True,
                            "message": "日次レポート上限到達 (HTTP 403: Daily Limit 100到達)"
                        }
                    elif e.code == 429:
                        api_status = {
                            "status": "RATE_LIMITED",
                            "code": 429,
                            "quota_exhausted": False,
                            "message": "短時間アクセス過多 (HTTP 429: Rate Limited)"
                        }
                    else:
                        api_status = {
                            "status": "API_ERROR",
                            "code": e.code,
                            "quota_exhausted": False,
                            "message": f"HTTP Error {e.code}: {e.reason}"
                        }
                except Exception as e:
                    api_status = {
                        "status": "NET_ERROR",
                        "code": 0,
                        "quota_exhausted": False,
                        "message": f"通信エラー: {str(e)[:60]}"
                    }

            resp = {
                "auth": auth_info,
                "stats": stats,
                "api_status": api_status,
                "quota_exhausted": api_status.get("quota_exhausted", False)
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        elif clean_path == "/oauth/login":
            try:
                from ubersuggest_token_manager import generate_oauth_authorization_url
                auth_url, state = generate_oauth_authorization_url()
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

            if err:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h2>OAuth Authentication Error: {err}</h2><p><a href='/'>Back to panel</a></p>".encode("utf-8"))
                return

            if not code:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<h2>Missing authorization code.</h2><p><a href='/'>Back to panel</a></p>".encode("utf-8"))
                return

            try:
                from ubersuggest_token_manager import exchange_code_for_token
                ok, err_msg = exchange_code_for_token(code, state)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if ok:
                    html = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>OAuth Success</title><style>body{background:#0f172a;color:#f8fafc;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}.card{background:#1e293b;padding:32px;border-radius:12px;border:1px solid #38bdf8;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.5);max-width:400px;}h2{color:#38bdf8;margin-top:0;}p{color:#94a3b8;font-size:14px;line-height:1.6;}.btn{display:inline-block;margin-top:16px;background:#0284c7;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold;}</style></head><body><div class="card"><h2>Ubersuggest Connected!</h2><p>New OAuth tokens saved.<br>Auto-refresh is now active and will keep tokens refreshed automatically.</p><a class="btn" href="javascript:window.close()">Close Window</a></div><script>setTimeout(function(){ if(window.opener){ window.close(); } else { window.location.href='/'; } }, 2500);</script></body></html>'''
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.wfile.write(f"<h2>Token Exchange Failed: {err_msg}</h2><p><a href='/'>Back to panel</a></p>".encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h2>Server Exception: {e}</h2><p><a href='/'>Back to panel</a></p>".encode("utf-8"))
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

            # クエリパラメータ seed が指定されている場合、現在のシードキーワードに一致するレコードのみをフィルタリング
            query_params = parse_qs(parsed.query)
            target_seed = query_params.get("seed", [""])[0].strip()
            if target_seed and items:
                norm_seed = target_seed.replace(" ", "").replace("　", "")
                filtered = []
                for it in items:
                    it_seed = it.get("seed_keyword", "").replace(" ", "").replace("　", "")
                    if norm_seed and (norm_seed == it_seed or norm_seed in it_seed or it_seed in norm_seed):
                        filtered.append(it)
                if filtered:
                    items = filtered

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
            # サーバー側で直接CSVを生成してダウンロードさせるエンドポイント
            db_file = WIDE_DIR / "keywords_db.json"
            items = []
            if db_file.exists():
                try:
                    with open(db_file, "r", encoding="utf-8-sig") as f:
                        raw = json.load(f)
                        items = raw.get("keywords", [])
                except Exception:
                    pass

            query_params = parse_qs(parsed.query)
            target_seed = query_params.get("seed", [""])[0].strip()
            if target_seed and items:
                norm_seed = target_seed.replace(" ", "").replace("　", "")
                filtered = []
                for it in items:
                    it_seed = it.get("seed_keyword", "").replace(" ", "").replace("　", "")
                    if norm_seed and (norm_seed == it_seed or norm_seed in it_seed or it_seed in norm_seed):
                        filtered.append(it)
                if filtered:
                    items = filtered

            headers = ["判定(星)", "キーワード", "月間検索Vol", "SEO難易度(SD)", "DA一桁サイト数", "知恵袋Q&Aサイト数", "調査日時"]
            csv_lines = [",".join(headers)]
            for r in items:
                m = r.get("da_meta", {})
                star = str(r.get("star_rating", "-")).replace('"', '""')
                kw = str(r.get("keyword", "")).replace('"', '""')
                vol = str(r.get("volume", "")) if r.get("volume") is not None else ""
                sd = str(r.get("sd", "")) if r.get("sd") is not None else ""
                da1 = str(m.get("single_digit_count", "")) if m.get("single_digit_count") is not None else ""
                qa = str(m.get("qa_count", "")) if m.get("qa_count") is not None else ""
                up = str(r.get("updated_at", ""))
                csv_lines.append(f'"{star}","{kw}",{vol},{sd},{da1},{qa},"{up}"')

            csv_text = "\ufeff" + "\r\n".join(csv_lines)
            csv_bytes = csv_text.encode("utf-8")

            # 1. プロジェクトの reports/ に実体ファイルとして保存
            reports_dir = WIDE_DIR / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = time.strftime('%Y%m%d_%H%M%S')
            export_file = reports_dir / f"wide_export_{timestamp_str}.csv"
            with open(export_file, "wb") as ef:
                ef.write(csv_bytes)

            # 2. ユーザーの「ダウンロード」フォルダ (C:\Users\santa\Downloads) にも直接自動保存！
            user_downloads_dir = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
            if user_downloads_dir.exists():
                dl_file = user_downloads_dir / f"wide_リサーチ結果_{timestamp_str}.csv"
                try:
                    with open(dl_file, "wb") as df:
                        df.write(csv_bytes)
                except Exception:
                    pass

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="wide_research_results.csv"')
            self.send_header("X-Saved-Path", str(export_file))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        elif clean_path == "/api/database":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            db_items = []
            if DataManager:
                try:
                    db_items = DataManager.load_keywords_db()
                except Exception:
                    pass
            self.wfile.write(json.dumps(db_items, ensure_ascii=False).encode("utf-8"))
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

        if clean_path == "/api/run":
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            payload = json.loads(body)

            seed = payload.get("seed", "").strip()
            axis1_terms = payload.get("axis1", [])
            axis2_terms = payload.get("axis2", [])

            # 一時クエリファイル作成
            query_file = WIDE_DIR / "temp_sidecar_query.json"
            from generator_ai_expansion import smart_split_seed
            slot_a, slot_b = smart_split_seed(seed)

            all_kw = set()
            if seed: all_kw.add(seed)
            if slot_a: all_kw.add(slot_a)
            if slot_b: all_kw.add(slot_b)
            for t in axis1_terms:
                ct = t.strip()
                if ct: all_kw.add(ct)
            for t in axis2_terms:
                ct = t.strip()
                if ct: all_kw.add(ct)

            q_data = {
                "mode": payload.get("mode", "full"),
                "seed_keyword": seed,
                "seed_keywords": [s for s in [slot_a, slot_b] if s],
                "axis1_terms": [],
                "axis2_terms": [],
                "keywords": sorted(list(all_kw))
            }

            with open(query_file, "w", encoding="utf-8") as f:
                json.dump(q_data, f, ensure_ascii=False, indent=2)

            # 前回の結果をクリア（クリーンスタート保証）
            db_file = WIDE_DIR / "keywords_db.json"
            norm_seed = seed.replace(" ", "").replace("　", "")
            if db_file.exists():
                try:
                    with open(db_file, "r", encoding="utf-8-sig") as f:
                        raw = json.load(f)
                    # 現在のシードおよび今回の対象キーワードに該当する古いレコードを削除
                    retained = []
                    for it in raw.get("keywords", []):
                        it_seed = it.get("seed_keyword", "").replace(" ", "").replace("　", "")
                        it_kw = it.get("keyword", "")
                        if norm_seed and (norm_seed == it_seed or norm_seed in it_seed or it_seed in norm_seed):
                            continue
                        if it_kw in all_kw:
                            continue
                        retained.append(it)
                    raw["keywords"] = retained
                    raw["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    with open(db_file, "w", encoding="utf-8") as f:
                        json.dump(raw, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print("Error clearing previous results:", e)

            # バックグラウンドリサーチワーカーを実行
            worker_py = WIDE_DIR / "batch_research_worker.py"
            cmd = [
                sys.executable,
                "-u",
                str(worker_py),
                str(query_file)
            ]

            log_file = WIDE_DIR / "reports" / "sidecar_latest_run.log"
            with open(log_file, "w", encoding="utf-8") as lf:
                proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, text=True, cwd=str(WIDE_DIR))

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "RUNNING",
                "pid": proc.pid,
                "total_count": len(all_kw)
            }).encode("utf-8"))
            return

def run_server():
    server = HTTPServer(("127.0.0.1", PORT), WideStudioHandler)
    print(f"[wide-studio] Sidecar server running on port {PORT}...")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
