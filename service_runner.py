"""
================================================================================
【設計メモ (Design Note)】
--------------------------------------------------------------------------------
1. モジュール概要:
   - ファイル名: service_runner.py
   - カテゴリ: service (プロセス制御・実行基盤)
   - 責務: PowerShellスクリプトの非同期実行、標準出力/標準エラーのリアルタイム行単位
     キャプチャ、プロセス強制停止 (Kill)、実行ステータス通知コールバックの管理。

2. 入出力・依存関係:
   - 入力: スクリプトパス、引数リスト、行出力コールバック (on_line)、完了コールバック (on_complete)
   - 出力: プロセス実行ハンドル、リアルタイムテキストストリーム
   - 外部依存: subprocess, threading, queue, os, sys, core_logger

3. AI改修時の指針・注意点:
   - GUIスレッドを絶対にブロックしないこと。全てのプロセス読み取りは独立スレッドで実行する。
   - Windows環境でのUTF-8出力対応のため、`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
     または適切なデコードフォールバック (utf-8, cp932) を備えること。
================================================================================
"""

import os
import sys
import subprocess
import threading
from typing import List, Callable, Optional
from core_logger import log_info, log_warn, log_error

class ProcessRunner:
    """PowerShell / コマンド非同期実行管理クラス"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None

    def run_powershell(
        self,
        script_path: str,
        args: List[str] = None,
        working_dir: Optional[str] = None,
        on_line: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """PowerShellスクリプトをバックグラウンドスレッドで実行する"""
        if self.is_running:
            log_warn("Process is already running. Cannot start new process.")
            return False

        if not os.path.exists(script_path):
            msg = f"Error: Script not found: {script_path}"
            log_error(msg)
            if on_line:
                on_line(msg + "\n")
            if on_complete:
                on_complete(-1)
            return False

        args = args or []
        # powershell 実行コマンド (UTF-8を優先設定)
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; & '{script_path}' " + " ".join(args)
        ]

        cwd = working_dir or os.path.dirname(script_path)
        log_info(f"Starting process: {' '.join(cmd)} (cwd: {cwd})")

        self.is_running = True

        def _worker():
            exit_code = -1
            try:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )

                # 行単位で読み取り
                while True:
                    line_bytes = self.process.stdout.readline()
                    if not line_bytes:
                        break
                    
                    # デコード試行 (utf-8 -> cp932)
                    line_str = ""
                    try:
                        line_str = line_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            line_str = line_bytes.decode("cp932", errors="replace")
                        except Exception:
                            line_str = line_bytes.decode("latin-1", errors="replace")

                    if on_line:
                        on_line(line_str)

                self.process.wait()
                exit_code = self.process.returncode

            except Exception as e:
                err_msg = f"\n[ProcessRunner Exception] {e}\n"
                log_error(err_msg)
                if on_line:
                    on_line(err_msg)
            finally:
                self.is_running = False
                self.process = None
                log_info(f"Process finished with exit code: {exit_code}")
                if on_complete:
                    on_complete(exit_code)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> bool:
        """実行中のプロセスを安全に強制停止する"""
        if not self.is_running or not self.process:
            return False

        log_warn("Terminating process forcefully...")
        try:
            self.process.terminate()
            # Windowsでは taskkill で子プロセスも含めて終了
            if os.name == "nt" and self.process.pid:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            self.is_running = False
            return True
        except Exception as e:
            log_error(f"Failed to terminate process: {e}")
            return False
