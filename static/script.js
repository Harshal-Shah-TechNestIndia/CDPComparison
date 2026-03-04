// static/compare.js

const state = {
  files: [],
  jsonCache: new Map(),     // filename -> parsed JSON
  sectionMaps: {            // derived per file
    left: new Map(),        // question_no -> {question, answer}
    right: new Map()
  }
};

document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  loadJsonList();
});

function bindUI() {
  document.getElementById("refreshBtn").addEventListener("click", loadJsonList);

  document.getElementById("fileSelect1").addEventListener("change", async (e) => {
    await loadJsonForSide("left", e.target.value);
    populateSections("left");
    clearQA("left");
  });

  document.getElementById("fileSelect2").addEventListener("change", async (e) => {
    await loadJsonForSide("right", e.target.value);
    populateSections("right");
    clearQA("right");
  });

  document.getElementById("sectionSelect1").addEventListener("change", (e) => {
    showQA("left", e.target.value);
  });

  document.getElementById("sectionSelect2").addEventListener("change", (e) => {
    showQA("right", e.target.value);
  });
}

async function loadJsonList() {
  try {
    const res = await fetch("/list_json");
    const data = await res.json();
    state.files = data.files || [];
    fillFileDropdown("fileSelect1", state.files);
    fillFileDropdown("fileSelect2", state.files);
  } catch (err) {
    console.error("Failed to load JSON list:", err);
  }
}

function fillFileDropdown(selectId, files) {
  const sel = document.getElementById(selectId);
  sel.innerHTML = "";
  if (!files.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "No output_*.json found";
    sel.appendChild(opt);
    return;
  }
  const firstEmpty = document.createElement("option");
  firstEmpty.value = "";
  firstEmpty.textContent = "Select a JSON file";
  sel.appendChild(firstEmpty);

  files.forEach((f) => {
    const opt = document.createElement("option");
    opt.value = f;
    opt.textContent = f;
    sel.appendChild(opt);
  });
}

async function loadJsonForSide(side, filename) {
  state.sectionMaps[side] = new Map();
  if (!filename) return;

  // cache to avoid repeated fetches
  if (!state.jsonCache.has(filename)) {
    const res = await fetch(`/json?file=${encodeURIComponent(filename)}`);
    const js = await res.json();
    state.jsonCache.set(filename, js);
  }
  const data = state.jsonCache.get(filename);
  buildSectionMap(side, data);
}

function buildSectionMap(side, jsonData) {
  const map = new Map(); // question_no -> {question, answer}

  // Expected shape from save_results(): { company_name, pdf_source, pages: { "1": [ {section, question, answer}, ...], ... } }
  const pages = jsonData?.pages || {};
  for (const pageNo of Object.keys(pages)) {
    const entries = pages[pageNo] || [];
    for (const item of entries) {
      const qno = (item.section || "").trim();
      const qtext = (item.question || "").trim();
      const ans = (item.answer || "").trim();
      if (!qno) continue;

      // If duplicates appear across pages, prefer the first seen (or override; your call)
      if (!map.has(qno)) {
        map.set(qno, { question: qtext, answer: ans });
      }
    }
  }
  state.sectionMaps[side] = map;
}

function populateSections(side) {
  const selectId = side === "left" ? "sectionSelect1" : "sectionSelect2";
  const sel = document.getElementById(selectId);
  sel.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "drop down to select section";
  sel.appendChild(placeholder);

  // Sort by numeric-ish question_no if possible
  const map = state.sectionMaps[side];
  const keys = Array.from(map.keys());

  keys.sort((a, b) => {
    // naive numeric compare of dot-separated ids
    const aa = a.split(".").map(n => parseInt(n, 10));
    const bb = b.split(".").map(n => parseInt(n, 10));
    for (let i = 0; i < Math.max(aa.length, bb.length); i++) {
      const av = aa[i] ?? -1, bv = bb[i] ?? -1;
      if (av !== bv) return av - bv;
    }
    return 0;
  });

  keys.forEach(k => {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = k;
    sel.appendChild(opt);
  });
}

function clearQA(side) {
  if (side === "left") {
    document.getElementById("question1").textContent = "";
    document.getElementById("answer1").textContent = "";
  } else {
    document.getElementById("question2").textContent = "";
    document.getElementById("answer2").textContent = "";
  }
}

function showQA(side, qno) {
  const map = state.sectionMaps[side];
  const rec = map.get(qno) || { question: "", answer: "" };

  if (side === "left") {
    document.getElementById("question1").textContent = rec.question || "";
    document.getElementById("answer1").innerHTML = (rec.answer || "").replace(/\n/g, "<br>");
  } else {
    document.getElementById("question2").textContent = rec.question || "";
    document.getElementById("answer2").innerHTML = (rec.answer || "").replace(/\n/g, "<br>");
  }
}