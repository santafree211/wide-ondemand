// -*- coding: utf-8 -*-
/**
 * ==============================================================================
 * 【モジュール設計メモ】
 * ■ モジュール名: ui_results_table.js
 * ■ カテゴリ: Frontend UI / リサーチ結果描画・CSV入出力・ステータス監視モジュール
 * ■ 責務・役割（Single Responsibility）:
 *   - /api/results からの最新キーワード実測結果（★星・Vol・SD）のテーブル描画。
 *   - Excel互換CSVのエクスポート（/api/export_csv）およびインポート（/api/import_csv）。
 *   - Ubersuggest API接続状態（HTTP 200/401/403/429）の定期監視と警告バナー描画。
 * ==============================================================================
 */

window.isQuotaExhausted = false;
let currentResultsList = [];

function clearResults() {
  currentResultsList = [];
  const tbody = document.getElementById("results-tbody");
  const titleSpan = document.getElementById("results-count-title");
  if (titleSpan) titleSpan.innerText = "最新リサーチ結果 (0 件)";
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 10px;">リサーチを実行するとここに結果が表示されます</td></tr>`;
  }
}

async function loadResults() {
  try {
    const seed = document.getElementById("seed-input") ? document.getElementById("seed-input").value.trim() : "";
    const url = seed ? `/api/results?seed=${encodeURIComponent(seed)}&_t=${Date.now()}` : `/api/results?_t=${Date.now()}`;
    const res = await fetch(url);
    const list = await res.json();
    currentResultsList = list || [];
    const tbody = document.getElementById("results-tbody");
    const titleSpan = document.getElementById("results-count-title");
    if (list && list.length > 0) {
      if (titleSpan) titleSpan.innerText = `最新リサーチ結果 (全 ${list.length} 件)`;
      tbody.innerHTML = list.map(row => `
        <tr>
          <td><span class="star-badge">${row.star_rating || "-"}</span></td>
          <td>${row.keyword}</td>
          <td>${row.volume != null ? row.volume.toLocaleString() : "N/A"}</td>
          <td>${row.sd != null ? row.sd : "N/A"}</td>
        </tr>
      `).join("");
    } else {
      if (titleSpan) titleSpan.innerText = `最新リサーチ結果 (0 件)`;
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 10px;">リサーチを実行するとここに結果が表示されます</td></tr>`;
    }
  } catch (e) {
    console.error("loadResults error:", e);
  }
}

function exportToExcel() {
  const seed = document.getElementById("seed-input") ? document.getElementById("seed-input").value.trim() : "";
  const url = seed ? `/api/export_csv?seed=${encodeURIComponent(seed)}&_t=${Date.now()}` : `/api/export_csv?_t=${Date.now()}`;
  window.location.href = url;
  
  setTimeout(() => {
    alert("📊 ダウンロードフォルダ（C:\\Users\\santa\\Downloads）にCSVを直接保存しました！\n（Excelでそのまま文字化けせず開けます）");
  }, 500);
}

async function importCsv(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const text = e.target.result;
    try {
      const res = await fetch("/api/import_csv", {
        method: "POST",
        headers: { "Content-Type": "text/plain; charset=utf-8" },
        body: text
      });
      const data = await res.json();
      if (data.status === "ok") {
        if (data.seed_keyword) {
          document.getElementById("seed-input").value = data.seed_keyword;
          updateLabels(data.seed_keyword);
          updateMeter();
        }
        alert(`✅ CSVから ${data.count} 件のキーワード（★星付き含む）を最新リサーチ結果に読み込みました！\nこのまま「🚀 2. Ubersuggest API実行」を押すと、星付きKWのみのボリュームを一括実測できます。`);
        loadResults();
      } else {
        alert("CSV読み込み失敗: " + (data.message || "形式を確認してください"));
      }
    } catch (err) {
      alert("CSV読込通信エラー: " + err);
    } finally {
      event.target.value = "";
    }
  };
  reader.readAsText(file, "UTF-8");
}

async function checkSystemStatus() {
  try {
    const res = await fetch(`/api/status?_t=${Date.now()}`);
    const data = await res.json();
    const banner = document.getElementById("quota-warning-banner");
    const bannerTitle = document.getElementById("quota-warning-title");
    const bannerDesc = document.getElementById("quota-warning-desc");
    const badge = document.getElementById("auth-badge");

    const apiStat = data.api_status || {};
    const statusCode = apiStat.code || 200;

    if (statusCode === 401) {
      window.isQuotaExhausted = true;
      if (banner) banner.style.display = "block";
      if (bannerTitle) bannerTitle.innerText = "🔑 Ubersuggest 認証期限切れ (HTTP 401)";
      if (bannerDesc) bannerDesc.innerHTML = "OAuthアクセストークンの有効期限が切れたため、API接続が拒絶されました。<br>下のボタンから1クリックで再認証を行うと、以後は<strong>完全自動でトークン延命</strong>が継続します。<div style='margin-top:10px;'><a href='/oauth/login' target='_blank' style='display:inline-block;background:#0284c7;color:#fff;font-weight:bold;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:13px;'>🔑 Ubersuggest再認証（ブラウザを開く）</a></div>";
      if (badge) {
        badge.innerText = "要再認証 (HTTP 401)";
        badge.style.background = "#7f1d1d";
        badge.style.color = "#fca5a5";
      }
    } else if (statusCode === 403 || data.quota_exhausted) {
      window.isQuotaExhausted = true;
      if (banner) banner.style.display = "block";
      if (bannerTitle) bannerTitle.innerText = "⚠️ Ubersuggest 日次レポート上限到達 (HTTP 403)";
      if (bannerDesc) bannerDesc.innerHTML = "本日分の日次レポート枠（100回/日）が枯渇したため、新規のVol/SD取得が一時停止されています。<br>日付変更（0時リセット）後に自動再開されます。";
      if (badge) {
        badge.innerText = "上限到達 (100/100)";
        badge.style.background = "#7f1d1d";
        badge.style.color = "#f87171";
      }
    } else if (statusCode === 429) {
      window.isQuotaExhausted = true;
      if (banner) banner.style.display = "block";
      if (bannerTitle) bannerTitle.innerText = "⏳ 一時的なアクセス過多 (HTTP 429: Rate Limited)";
      if (bannerDesc) bannerDesc.innerHTML = "短時間に連続アクセスがあったため制限されています。1分ほどお待ちいただくと自動解除されます。";
      if (badge) {
        badge.innerText = "レート制限中 (429)";
        badge.style.background = "#78350f";
        badge.style.color = "#fde68a";
      }
    } else {
      window.isQuotaExhausted = false;
      if (banner) banner.style.display = "none";
      if (badge) {
        badge.innerText = "認証済 (OK)";
        badge.style.background = "#064e3b";
        badge.style.color = "#34d399";
      }
    }
    if (typeof updateMeter === "function") updateMeter();
  } catch (e) {
    console.error("Status check error:", e);
  }
}
