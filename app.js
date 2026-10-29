// -*- coding: utf-8 -*-
/**
 * ==============================================================================
 * 【モジュール設計メモ】
 * ■ モジュール名: app.js
 * ■ カテゴリ: Frontend Entry / wide Studio アプリケーション起動・統括
 * ■ 責務・役割（Single Responsibility）:
 *   - ページ起動時の初期化フロー（非同期復元 ➡ ラベル更新 ➡ 結果ロード ➡ 認証診断）。
 *   - 定期監視タイマー（30秒ごとのAPIステータス確認）の起動・維持。
 * ==============================================================================
 */

(async function init() {
  const restored = await loadSavedState();
  if (!restored) {
    const seedInput = document.getElementById("seed-input");
    updateLabels(seedInput ? seedInput.value : "");
    updateMeter();
  }
  await loadResults();
  if (typeof updateStockSummary === "function") await updateStockSummary();
  await checkSystemStatus();
})();

// 15秒ごとに星付きKW蓄積サマリー＆ステータスを自動更新
setInterval(async () => {
  if (typeof updateStockSummary === "function") await updateStockSummary();
  await checkSystemStatus();
}, 15000);
