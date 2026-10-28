// -*- coding: utf-8 -*-
/**
 * ==============================================================================
 * 【モジュール設計メモ】
 * ■ モジュール名: app.js
 * ■ カテゴリ: Frontend Logic / wide Studio クライアント処理エンジン
 * ■ 責務・役割（Single Responsibility）:
 *   - フォーム状態（シード、軸①、軸②）の保存・復元（ローカルストレージ & サーバー state.json）。
 *   - 前後2大固定軸のメーター進捗計算および自動展開API通信（/api/expand）。
 *   - Google公式実測SERP星判定（/api/run mode: serp_only）およびリアルタイム進行ポーリング。
 *   - Ubersuggest API実行（/api/run mode: ubersuggest）および最新リサーチ結果表示（/api/results）。
 *   - CSVエクスポート・インポートのクライアント制御。
 *   - Ubersuggest API接続状態（HTTP 200/401/403/429）の監視と警告バナー制御。
 * ==============================================================================
 */

function saveState() {
      const seed = document.getElementById("seed-input").value;
      const a1 = document.getElementById("axis1-input").value;
      const a2 = document.getElementById("axis2-input").value;
      const stateObj = { seed, a1, a2 };
      
      // 1. ローカルストレージに即時保存
      localStorage.setItem("wide_studio_seed", seed);
      localStorage.setItem("wide_studio_axis1", a1);
      localStorage.setItem("wide_studio_axis2", a2);

      // 2. サーバー側 state.json にも永続保存（ブラウザキャッシュクリアされても復元保証）
      fetch("/api/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(stateObj)
      }).catch(() => {});
    }

    async function loadSavedState() {
      // 1. サーバーの state.json から完全復元を試みる
      try {
        const res = await fetch(`/api/state?_t=${Date.now()}`);
        const state = await res.json();
        if (state && state.seed && state.seed.trim().length > 0) {
          document.getElementById("seed-input").value = state.seed;
          if (state.a1 !== undefined) document.getElementById("axis1-input").value = state.a1;
          if (state.a2 !== undefined) document.getElementById("axis2-input").value = state.a2;
          updateLabels(state.seed);
          updateMeter();
          return true;
        }
      } catch (e) {}

      // 2. フォールバック: ローカルストレージから復元
      const savedSeed = localStorage.getItem("wide_studio_seed");
      if (savedSeed !== null && savedSeed.trim().length > 0) {
        document.getElementById("seed-input").value = savedSeed;
        const savedA1 = localStorage.getItem("wide_studio_axis1");
        const savedA2 = localStorage.getItem("wide_studio_axis2");
        if (savedA1 !== null) document.getElementById("axis1-input").value = savedA1;
        if (savedA2 !== null) document.getElementById("axis2-input").value = savedA2;
        updateLabels(savedSeed);
        updateMeter();
        return true;
      }
      return false;
    }

    let seedDebounce = null;
    function onSeedChanged(val) {
      saveState();
      updateLabels(val);
      updateMeter();
      clearResults();
      clearTimeout(seedDebounce);
      seedDebounce = setTimeout(() => {
        if (val.trim().length > 1) {
          autoGenerateAxes();
        }
      }, 600);
    }

    async function autoGenerateAxes() {
      const seed = document.getElementById("seed-input").value.trim();
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


    const KNOWN_SUFFIXES = [
      "100均", "ダイソー", "セリア", "キャンドゥ", "ワッツ",
      "おすすめ", "口コミ", "評判", "違い", "比較", "ランキング",
      "使い方", "作り方", "危険性", "デメリット", "メリット", "効果",
      "体に悪い", "買ってはいけないメーカー", "買ってはいけない", "太る", "痩せる",
      "低い", "高い", "サブスク", "レンタル", "知育", "売ってない", "どこで買える"
    ];

    function smartSplit(text) {
      const clean = text.trim();
      const parts = clean.split(/\s+/);
      if (parts.length >= 3) {
        return {
          is3words: true,
          a: parts[0] + " " + parts[1],
          b: parts[1] + " " + parts.slice(2).join(" "),
          slotA: parts[0],
          slotB: parts.slice(1).join(" ")
        };
      }
      if (parts.length === 2) {
        return { is3words: false, a: parts[0], b: parts[1] };
      }
      for (const s of KNOWN_SUFFIXES.sort((x, y) => y.length - x.length)) {
        if (clean.endsWith(s) && clean.length > s.length) {
          return { is3words: false, a: clean.slice(0, -s.length).trim(), b: s };
        }
      }
      return { is3words: false, a: clean, b: "" };
    }

    function updateLabels(seed) {
      const res = smartSplit(seed);
      if (res.is3words) {
        document.getElementById("axis1-label").innerText = `軸①: [${res.a}] 〇〇 (前固定)`;
        document.getElementById("axis2-label").innerText = `軸②: 〇〇 [${res.b}] (後固定)`;
      } else {
        document.getElementById("axis1-label").innerText = `軸①: [${res.a || "A"}] 〇〇 (前固定)`;
        document.getElementById("axis2-label").innerText = `軸②: 〇〇 [${res.b || "B"}] (後固定)`;
      }
    }

    function updateMeter() {
      saveState();
      const seed = document.getElementById("seed-input").value.trim();
      updateLabels(seed);
      const a1 = document.getElementById("axis1-input").value.split("\n").filter(x => x.trim().length > 0);
      const a2 = document.getElementById("axis2-input").value.split("\n").filter(x => x.trim().length > 0);

      const { a: slotA, b: slotB } = smartSplit(seed);

      const set = new Set();
      if (seed) set.add(seed);
      if (slotA) set.add(slotA);
      if (slotB) set.add(slotB);
      a1.forEach(t => {
        const cleanT = t.trim();
        if (cleanT.startsWith(slotA)) set.add(cleanT);
        else if (slotA) set.add(`${slotA} ${cleanT}`);
        else set.add(cleanT);
      });
      a2.forEach(t => {
        const cleanT = t.trim();
        if (cleanT.endsWith(slotB)) set.add(cleanT);
        else if (slotB) set.add(`${cleanT} ${slotB}`);
        else set.add(cleanT);
      });

      const count = set.size;
      const fill = document.getElementById("meter-fill");
      const text = document.getElementById("meter-text");
      const status = document.getElementById("meter-status");
      const btn = document.getElementById("btn-run");

      text.innerText = `合計: ${count} / 25件`;
      fill.style.width = Math.min((count / 25) * 100, 100) + "%";

      if (isQuotaExhausted) {
        fill.style.background = "#ef4444";
        status.innerText = "❌ API上限到達 (実行停止中)";
        status.style.color = "#ef4444";
        btn.disabled = true;
        btn.style.background = "#475569";
        btn.style.cursor = "not-allowed";
        btn.innerText = "🛑 API上限到達のため一時停止中";
        return;
      }

      if (count >= 25) {
        fill.style.background = "var(--success)";
        status.innerText = "✔ 閾値達成 (実行可能)";
        status.style.color = "var(--success)";
        btn.disabled = false;
        btn.style.background = "#2563eb";
        btn.style.cursor = "pointer";
        btn.innerText = "🚀 1-Shot メガバッチ実行 (API: 1回)";
      } else {
        fill.style.background = "var(--warning)";
        status.innerText = `あと ${25 - count} 件不足`;
        status.style.color = "var(--warning)";
        btn.disabled = true;
        btn.style.background = "#475569";
        btn.style.cursor = "not-allowed";
        btn.innerText = "🚀 1-Shot メガバッチ実行 (API: 1回)";
      }
    }

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
          loadResults();

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

    async function executeSerpOnly() {
      clearResults();
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
        const data = await res.json();
      } catch (e) {
        alert("SERP実行エラー: " + e);
      }
    }

    async function executeBatch() {
      // 星付きKWのみを対象にVol/SDを取得
      const tbody = document.getElementById("results-tbody");
      const titleSpan = document.getElementById("results-count-title");
      if (titleSpan) titleSpan.innerText = "🚀 Ubersuggest API実測中 (星付き精鋭KWのみ)...";

      // ボタンを押した瞬間に進捗バーを表示
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
        const data = await res.json();
      } catch (e) {
        alert("実行エラー: " + e);
        const btn = document.getElementById("btn-run");
        if (btn) {
          btn.disabled = false;
        }
      }
    }

    let currentResultsList = [];

    async function clearResults() {
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
      // 1. サーバー側エンドポイントへ直接リダイレクト/ダウンロード (現在のシードKWのみを出力)
      const seed = document.getElementById("seed-input") ? document.getElementById("seed-input").value.trim() : "";
      const url = seed ? `/api/export_csv?seed=${encodeURIComponent(seed)}&_t=${Date.now()}` : `/api/export_csv?_t=${Date.now()}`;
      window.location.href = url;
      
      // 2. 完了メッセージ表示
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

    let isQuotaExhausted = false;

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
        const statusType = apiStat.status || "OK";

        if (statusCode === 401) {
          // HTTP 401: トークン失効・再認証必要
          isQuotaExhausted = true;
          if (banner) banner.style.display = "block";
          if (bannerTitle) bannerTitle.innerText = "🔑 Ubersuggest 認証期限切れ (HTTP 401)";
          if (bannerDesc) bannerDesc.innerHTML = "OAuthアクセストークンの有効期限が切れたため、API接続が拒絶されました。<br>下のボタンから1クリックで再認証を行うと、以後は<strong>完全自動でトークン延命</strong>が継続します。<div style='margin-top:10px;'><a href='/oauth/login' target='_blank' style='display:inline-block;background:#0284c7;color:#fff;font-weight:bold;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:13px;'>🔑 Ubersuggest再認証（ブラウザを開く）</a></div>";
          if (badge) {
            badge.innerText = "要再認証 (HTTP 401)";
            badge.style.background = "#7f1d1d";
            badge.style.color = "#fca5a5";
          }
        } else if (statusCode === 403 || data.quota_exhausted) {
          // HTTP 403: 日次100枠枯渇
          isQuotaExhausted = true;
          if (banner) banner.style.display = "block";
          if (bannerTitle) bannerTitle.innerText = "⚠️ Ubersuggest 日次レポート上限到達 (HTTP 403)";
          if (bannerDesc) bannerDesc.innerHTML = "本日分の日次レポート枠（100回/日）が枯渇したため、新規のVol/SD取得が一時停止されています。<br>日付変更（0時リセット）後に自動再開されます。";
          if (badge) {
            badge.innerText = "上限到達 (100/100)";
            badge.style.background = "#7f1d1d";
            badge.style.color = "#f87171";
          }
        } else if (statusCode === 429) {
          // HTTP 429: レート制限
          isQuotaExhausted = true;
          if (banner) banner.style.display = "block";
          if (bannerTitle) bannerTitle.innerText = "⏳ 一時的なアクセス過多 (HTTP 429: Rate Limited)";
          if (bannerDesc) bannerDesc.innerHTML = "短時間に連続アクセスがあったため制限されています。1分ほどお待ちいただくと自動解除されます。";
          if (badge) {
            badge.innerText = "レート制限中 (429)";
            badge.style.background = "#78350f";
            badge.style.color = "#fde68a";
          }
        } else {
          // 正常稼働
          isQuotaExhausted = false;
          if (banner) banner.style.display = "none";
          if (badge) {
            badge.innerText = "認証済 (OK)";
            badge.style.background = "#064e3b";
            badge.style.color = "#34d399";
          }
        }
        updateMeter();
      } catch (e) {
        console.error("Status check error:", e);
      }
    }

    // 初期化 (非同期復元完了を待ってからロード)
    (async function init() {
      const restored = await loadSavedState();
      if (!restored) {
        updateLabels(document.getElementById("seed-input").value || "");
        updateMeter();
      }
      await loadResults();
      await checkSystemStatus();
    })();
    // 30秒ごとに上限状態を自動ポーリング確認
    setInterval(checkSystemStatus, 30000);
