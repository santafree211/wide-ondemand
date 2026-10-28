// -*- coding: utf-8 -*-
/**
 * ==============================================================================
 * 【モジュール設計メモ】
 * ■ モジュール名: ui_state_manager.js
 * ■ カテゴリ: Frontend State / フォーム状態・メーター進捗計算専任モジュール
 * ■ 責務・役割（Single Responsibility）:
 *   - シードKWおよび軸①・軸②の入力値の永続化（localStorage & /api/state）。
 *   - シードKWの構文分解（smartSplit）および軸ラベル（軸①: [A] 〇〇）の動的更新。
 *   - 25件閾値メーターの充足率計算・カラー変更および実行ボタンの活性制御。
 * ==============================================================================
 */

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
  const a1El = document.getElementById("axis1-label");
  const a2El = document.getElementById("axis2-label");
  if (!a1El || !a2El) return;
  if (res.is3words) {
    a1El.innerText = `軸①: [${res.a}] 〇〇 (前固定)`;
    a2El.innerText = `軸②: 〇〇 [${res.b}] (後固定)`;
  } else {
    a1El.innerText = `軸①: [${res.a || "A"}] 〇〇 (前固定)`;
    a2El.innerText = `軸②: 〇〇 [${res.b || "B"}] (後固定)`;
  }
}

function saveState() {
  const seedInput = document.getElementById("seed-input");
  const a1Input = document.getElementById("axis1-input");
  const a2Input = document.getElementById("axis2-input");
  if (!seedInput) return;

  const seed = seedInput.value;
  const a1 = a1Input ? a1Input.value : "";
  const a2 = a2Input ? a2Input.value : "";
  const stateObj = { seed, a1, a2 };

  // 1. ローカルストレージに即時保存
  localStorage.setItem("wide_studio_seed", seed);
  localStorage.setItem("wide_studio_axis1", a1);
  localStorage.setItem("wide_studio_axis2", a2);

  // 2. サーバー側 state.json にも永続保存
  fetch("/api/state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(stateObj)
  }).catch(() => {});
}

async function loadSavedState() {
  // 1. サーバーの state.json から復元を試みる
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
  if (typeof clearResults === "function") clearResults();
  clearTimeout(seedDebounce);
  seedDebounce = setTimeout(() => {
    if (val.trim().length > 1 && typeof autoGenerateAxes === "function") {
      autoGenerateAxes();
    }
  }, 600);
}

function updateMeter() {
  saveState();
  const seedInput = document.getElementById("seed-input");
  const a1Input = document.getElementById("axis1-input");
  const a2Input = document.getElementById("axis2-input");
  if (!seedInput || !a1Input || !a2Input) return;

  const seed = seedInput.value.trim();
  updateLabels(seed);
  const a1 = a1Input.value.split("\n").filter(x => x.trim().length > 0);
  const a2 = a2Input.value.split("\n").filter(x => x.trim().length > 0);

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

  if (text) text.innerText = `合計: ${count} / 25件`;
  if (fill) fill.style.width = Math.min((count / 25) * 100, 100) + "%";

  if (window.isQuotaExhausted) {
    if (fill) fill.style.background = "#ef4444";
    if (status) {
      status.innerText = "❌ API上限到達 (実行停止中)";
      status.style.color = "#ef4444";
    }
    if (btn) {
      btn.disabled = true;
      btn.style.background = "#475569";
      btn.style.cursor = "not-allowed";
      btn.innerText = "🛑 API上限到達のため一時停止中";
    }
    return;
  }

  if (count >= 25) {
    if (fill) fill.style.background = "var(--success)";
    if (status) {
      status.innerText = "✔ 閾値達成 (実行可能)";
      status.style.color = "var(--success)";
    }
    if (btn) {
      btn.disabled = false;
      btn.style.background = "#2563eb";
      btn.style.cursor = "pointer";
      btn.innerText = "🚀 1-Shot メガバッチ実行 (API: 1回)";
    }
  } else {
    if (fill) fill.style.background = "var(--warning)";
    if (status) {
      status.innerText = `あと ${25 - count} 件不足`;
      status.style.color = "var(--warning)";
    }
    if (btn) {
      btn.disabled = true;
      btn.style.background = "#475569";
      btn.style.cursor = "not-allowed";
      btn.innerText = "🚀 1-Shot メガバッチ実行 (API: 1回)";
    }
  }
}
