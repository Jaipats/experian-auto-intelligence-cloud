// Inventory & Risk Co-Pilot — frontend logic
const $ = (id) => document.getElementById(id);

// tab switching
document.querySelectorAll("nav button").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll("nav button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    ["acquire", "risk", "radar", "ask"].forEach((t) => {
      $(t).style.display = t === b.dataset.tab ? "block" : "none";
    });
  };
});

function table(rows) {
  if (!rows || !rows.length) return "<p>No results.</p>";
  const cols = Object.keys(rows[0]);
  const head = cols.map((c) => `<th>${c.replace(/_/g, " ")}</th>`).join("");
  const body = rows
    .map((r) => "<tr>" + cols.map((c) => `<td>${fmt(r[c])}</td>`).join("") + "</tr>")
    .join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}
function fmt(v) {
  if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(2);
  return v ?? "—";
}
function srcLabel(el, resp) {
  if (!el) return;
  const live = resp.source === "live";
  el.className = "src" + (live ? "" : " sample");
  const text = live
    ? "Live data — governed query against Unity Catalog"
    : "Sample data — connect UC tables / models / Genie to go live" +
      (resp.note ? " (" + resp.note + ")" : "");
  el.innerHTML = `<span class="dot"></span>${text}`;
}

async function loadAcquire() {
  const r = await fetch(`/api/acquire?state=${$("acq-state").value}&body_style=${$("acq-body").value}`).then((x) => x.json());
  srcLabel($("acq-src"), r);
  $("acq-table").innerHTML = table(r.rows);
}

async function loadVin() {
  const vin = $("vin-input").value.trim();
  if (!vin) return;
  const r = await fetch(`/api/vin/${encodeURIComponent(vin)}`).then((x) => x.json());
  srcLabel($("vin-src"), r);
  const v = r.vehicle || {};
  $("vin-detail").innerHTML = `
    <div class="kpis">
      <div class="kpi"><div class="n">${fmt(v.accs_score)}</div><div class="l">ACCS score</div></div>
      <div class="kpi"><div class="n">$${fmt(v.predicted_residual_value)}</div><div class="l">Predicted residual</div></div>
      <div class="kpi"><div class="n">${v.segment_default_risk != null ? (v.segment_default_risk*100).toFixed(1)+"%" : "—"}</div><div class="l">Segment default risk</div></div>
      <div class="kpi"><div class="n">${fmt(v.accident_count)}</div><div class="l">Accidents</div></div>
    </div>
    <div class="card">${table([v])}</div>`;
}

async function loadRadar() {
  const r = await fetch(`/api/market-radar?region=${$("radar-region").value}`).then((x) => x.json());
  srcLabel($("radar-src"), r);
  $("radar-share").innerHTML = table(r.lender_share);
  $("radar-under").innerHTML = table(r.underserved);
}

// Genie status order for the stepper
const GENIE_STEPS = [
  ["FILTERING_CONTEXT", "Understanding"],
  ["ASKING_AI", "Generating SQL"],
  ["PENDING_WAREHOUSE", "Running query"],
  ["COMPLETED", "Done"],
];

function renderSteps(current) {
  const idx = GENIE_STEPS.findIndex(([s]) => s === current);
  $("ask-steps").innerHTML = GENIE_STEPS.map(([s, label], i) => {
    let cls = "step";
    if (current === "COMPLETED") cls += " done";
    else if (i < idx) cls += " done";
    else if (i === idx) cls += " active";
    const dot = cls.includes("done") ? "✓" : cls.includes("active") ? "●" : "○";
    return `<span class="${cls}">${dot} ${label}</span>`;
  }).join("");
}

function renderAskResult(r) {
  srcLabel($("ask-src"), r);
  // thinking
  const hasThink = (r.thoughts && r.thoughts.trim()) || (r.description && r.description.trim());
  $("ask-think-wrap").style.display = hasThink ? "block" : "none";
  $("ask-desc").textContent = r.description || "";
  $("ask-thoughts").textContent = r.thoughts || "";
  // answer
  $("ask-answer").textContent = r.answer || "(no answer)";
  // sql
  if (r.sql) {
    $("ask-sql-wrap").style.display = "block";
    $("ask-sql").textContent = r.sql;
    $("ask-rowcount").textContent = r.row_count != null ? `· ${r.row_count} rows` : "";
  } else {
    $("ask-sql-wrap").style.display = "none";
  }
  // result table
  const res = r.result || { columns: [], rows: [] };
  if (res.rows && res.rows.length) {
    const objs = res.rows.map((row) =>
      Object.fromEntries(res.columns.map((c, i) => [c, row[i]])));
    $("ask-result").innerHTML = table(objs);
  } else {
    $("ask-result").innerHTML = "";
  }
  // suggested follow-ups
  const sq = r.suggested_questions || [];
  $("ask-suggest").innerHTML = sq
    .map((q) => `<span class="chip" onclick="askThis('${q.replace(/'/g, "\\'")}')">${q}</span>`)
    .join("");
}

function askThis(q) {
  $("ask-input").value = q;
  loadAsk();
}

async function loadAsk() {
  const q = $("ask-input").value.trim();
  if (!q) return;
  // reset panel
  $("ask-answer").textContent = "Thinking…";
  $("ask-think-wrap").style.display = "none";
  $("ask-sql-wrap").style.display = "none";
  $("ask-result").innerHTML = "";
  $("ask-suggest").innerHTML = "";
  renderSteps("FILTERING_CONTEXT");

  // stream via SSE (POST + ReadableStream)
  try {
    const resp = await fetch("/api/ask/stream", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop();
      for (const part of parts) {
        const line = part.replace(/^data: /, "").trim();
        if (!line) continue;
        const evt = JSON.parse(line);
        if (evt.type === "status") renderSteps(evt.status);
        else if (evt.type === "result") { renderSteps("COMPLETED"); renderAskResult(evt); }
        else if (evt.type === "error") $("ask-answer").textContent = "Error: " + evt.message;
      }
    }
  } catch (e) {
    // fallback to blocking endpoint
    const r = await fetch("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    }).then((x) => x.json());
    renderSteps("COMPLETED");
    renderAskResult(r);
  }
}

// seed example prompts for the Ask tab (mirror the certified Genie queries)
const ASK_EXAMPLES = [
  "Top 10 fastest-turning SUVs in California this month",
  "Which segments have the highest default rate relative to their APR?",
  "Build a composite investability index across all three datasets",
  "Where is demand high but lender coverage low?",
  "How does AutoCheck condition relate to default rate by make?",
];
function renderExamples() {
  const el = $("ask-examples");
  if (!el) return;
  el.innerHTML = ASK_EXAMPLES
    .map((q) => `<span class="example" onclick="askThis('${q.replace(/'/g, "\\'")}')">${q}</span>`)
    .join("");
}

// initial load
renderExamples();
loadAcquire();
