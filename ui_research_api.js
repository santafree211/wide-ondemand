// -*- coding: utf-8 -*-
/**
 * ==============================================================================
 * 【モジュール設計メモ】
 * ■ モジュール名: ui_research_api.js
 * ■ カテゴリ: Frontend API / サーバー通信・リサーチ実行専任モジュール
 * ■ 責務・役割（Single Responsibility）:
 *   - 前後2大固定軸のAI自動展開リクエスト送信（/api/expand）。
 *   - Google公式SERP実測実行（/api/run mode: serp_only）のトリガー。
 *   - Ubersuggest APIメガバッチ実行（/api/run mode: ubersuggest）のトリガー。
 *   - バックグラウンド実行中の進行ポーリング（/api/progress）およびプログレスバー更新。
 * ==============================================================================
 */

let progressPollingTimer = null;

function startProgressPolling() {
  const box = document.getElementById("live-progress-box");
  const btn = document.getElementById("btn-run");
  if (box) box.style.display = "block";
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⚡ メガバッチ実測中...";
  }

  clearInterval(progressPollingTimer);
  progressPollingTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/progress?_t=${Date.now()}`);
      const data = await res.json();
      if (!data) return;

      const pctEl = document.getElementById("live-prog-pct");
      const barEl = document.getElementById("live-prog-bar");
      const kwEl = document.getElementById("live-prog-kw");
      const countEl = document.getElementById("live-prog-count");
      const titleEl = document.getElementById("live-prog-title");

      if (pctEl) pctEl.innerText = `${data.percent || 0}%`;
      if (barEl) barEl.style.width = `${data.percent || 0}%`;
      if (kwEl) kwEl.innerText = data.current_keyword ? `調査中: ${data.current_keyword}` : "準備中...";
      if (countEl) countEl.innerText = `${data.current || 0} / ${data.total || 0} 件`;

      // 途中経過もリアルタイムでテーブルに流し込む
      if (typeof loadResults === "function") loadResults();

      if (data.status === "COMPLETED" || (data.total > 0 && data.current >= data.total)) {
        clearInterval(progressPollingTimer);
        if (titleEl) titleEl.innerText = "✔ メガバッチ実測調査完了！";
        if (pctEl) pctEl.innerText = "100%";
        if (barEl) barEl.style.width = "100%";
        if (btn) {
          btn.disabled = false;
          btn.innerText = "🚀 1-Shot メガバッチ実行 (API: 1回)";
        }
        setTimeout(() => {
          if (box) box.style.display = "none";
          if (titleEl) titleEl.innerText = "⚡ Ubersuggest & Google SERP リアルタイム実測中...";
        }, 6000);
      } else if (data.status === "ERROR") {
        clearInterval(progressPollingTimer);
        if (titleEl) titleEl.innerText = `❌ エラー: ${data.message || ""}`;
        if (btn) {
          btn.disabled = false;
          btn.innerText = "🚀 1-Shot メガバッチ実行 (API: 1回)";
        }
      }
    } catch (e) {
      console.error("Progress poll error:", e);
    }
  }, 1000);
}

async function autoGenerateAxes() {
  const seedInput = document.getElementById("seed-input");
  if (!seedInput) return;
  const seed = seedInput.value.trim();
  if (!seed) return;

  const genBtn = document.getElementById("btn-auto-gen");
  if (genBtn) {
    genBtn.innerText = "⏳ 思考中...";
    genBtn.disabled = true;
  }
  try {
    const res = await fetch(`/api/expand?seed=${encodeURIComponent(seed)}`);
    const data = await res.json();
    if (data.axis1 && data.axis1.length > 0) {
      document.getElementById("axis1-input").value = data.axis1.join("\n");
    }
    if (data.axis2 && data.axis2.length > 0) {
      document.getElementById("axis2-input").value = data.axis2.join("\n");
    }
    updateLabels(seed);
    updateMeter();
  } catch (e) {
    console.error("Expand error:", e);
  } finally {
    if (genBtn) {
      genBtn.innerText = "✨ AI自動展開・思考";
      genBtn.disabled = false;
    }
  }
}

async function executeSerpOnly() {
  if (typeof clearResults === "function") clearResults();
  const tbody = document.getElementById("results-tbody");
  const titleSpan = document.getElementById("results-count-title");
  if (titleSpan) titleSpan.innerText = "🔍 Google実測SERP星判定中 (準備中...)";
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #38bdf8; padding: 16px; font-weight: bold;">🔍 Google公式SERP実測（2,000枠）による星判定を開始しました。前回の結果をクリアし、最新の実測結果をリアルタイム表示します...</td></tr>`;
  }

  startProgressPolling();

  const seed = document.getElementById("seed-input").value.trim();
  const a1 = document.getElementById("axis1-input").value.split("\n").filter(x => x.trim());
  const a2 = document.getElementById("axis2-input").value.split("\n").filter(x => x.trim());

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed, axis1: a1, axis2: a2, mode: "serp_only" })
    });
    await res.json();
  } catch (e) {
    alert("SERP実行エラー: " + e);
  }
}

async function executeBatch() {
  if (typeof clearResults === "function") clearResults();
  const tbody = document.getElementById("results-tbody");
  const titleSpan = document.getElementById("results-count-title");
  if (titleSpan) titleSpan.innerText = "🚀 Ubersuggest API実測中 (準備中...)";
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #38bdf8; padding: 16px; font-weight: bold;">🚀 Ubersuggest API実測を開始しました。前回の結果をクリアし、最新の実測結果をリアルタイム表示します...</td></tr>`;
  }

  startProgressPolling();

  const seed = document.getElementById("seed-input").value.trim();
  const a1 = document.getElementById("axis1-input").value.split("\n").filter(x => x.trim());
  const a2 = document.getElementById("axis2-input").value.split("\n").filter(x => x.trim());

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed, axis1: a1, axis2: a2, mode: "ubersuggest" })
    });
    await res.json();
  } catch (e) {
    alert("実行エラー: " + e);
    const btn = document.getElementById("btn-run");
    if (btn) btn.disabled = false;
  }
}
