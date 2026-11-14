// SelfCheck front end. All AI work runs in the local Flask backend on this device (ExecuTorch).
// Questions are generated while the student reads, so the assessment is usually ready on time.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const words = (t) => t.trim().split(/\s+/).filter(Boolean).length;
const fmt = (ms) => { const t = Math.floor(ms / 1000); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`; };

// Friendly titles for the practice passages (file name -> title).
const TITLES = {
  sample1: "Photosynthesis", sample2: "The water cycle", sample3: "The Constitution of India",
  sample4: "The human heart", sample5: "The Revolt of 1857", sample6: "Sound",
  sample7: "Money and credit", sample8: "Soils of India", official: "Today's passage",
};

let job = null, questions = [], idx = 0, results = [];
let sessionStart = 0, timerHandle = null, pollToken = 0;

// ---------- Navigation ----------
function show(name) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("active", s.id === "s-" + name));
  window.scrollTo(0, 0);
}
document.addEventListener("click", (e) => {
  const go = e.target.closest("[data-go]");
  if (go) show(go.dataset.go);
});

// ---------- Choose a passage ----------
async function loadSamples() {
  try {
    const list = await (await fetch("/api/samples")).json();
    $("samples").innerHTML = list.map((s, i) => `
      <button class="sample" data-i="${i}">
        <b>${esc(TITLES[s.name] || s.name)}</b>
        <span>${words(s.text)} words</span>
      </button>`).join("");
    $("samples").onclick = (e) => {
      const b = e.target.closest(".sample");
      if (b) openPassage(TITLES[list[b.dataset.i].name] || list[b.dataset.i].name, list[b.dataset.i].text);
    };
  } catch { /* practice passages are optional */ }
}

$("paste").addEventListener("input", () => {
  const n = words($("paste").value);
  $("paste-count").textContent = `${n} words`;
  $("paste-count").className = "count" + (n >= 150 && n <= 300 ? " good" : "");
  $("use-paste").disabled = n < 40 || n > 600;
});
$("use-paste").addEventListener("click", () => openPassage("Your passage", $("paste").value));

// ---------- Reading (generation runs in the background) ----------
async function openPassage(title, text) {
  $("choose-error").textContent = "";
  $("read-title").textContent = title;
  $("read-words").textContent = `${words(text)} words`;
  $("read-text").innerHTML = text.trim().split(/\n\s*\n/).map((p) => `<p>${esc(p)}</p>`).join("");
  setPrep("working", "Preparing your questions…", "Read the passage while this device writes and checks the questions.", 3);
  $("start-assess").disabled = true;
  show("read");

  const token = ++pollToken;  // ignore progress from an earlier passage
  try {
    const res = await fetch("/api/quest", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passage: text }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not start.");
    job = data.job_id;
    poll(token);
  } catch (err) {
    setPrep("failed", "Couldn't prepare questions", err.message, 0);
  }
}

function setPrep(state, title, detail, pct) {
  $("prep").className = "card prep" + (state === "ready" ? " ready" : state === "failed" ? " failed" : "");
  $("prep-title").textContent = title;
  $("prep-detail").textContent = detail;
  $("prep-bar").style.width = pct + "%";
}

async function poll(token) {
  if (token !== pollToken) return;
  try {
    const s = await (await fetch(`/api/quest/${job}`)).json();
    if (s.status === "done") {
      questions = s.questions;
      setPrep("ready", `${questions.length} questions ready`, "Each answer was taken from the passage and checked. Start when you've finished reading.", 100);
      $("start-assess").disabled = false;
      return;
    }
    if (s.status === "error") return setPrep("failed", "Something went wrong", s.error, 0);
    // A typical passage needs about 7-9 model calls; the bar follows real calls and never hits 100% early.
    const pct = Math.min(92, 3 + (s.calls / 8) * 89);
    const step = s.calls === 0 ? "Loading the model" : s.stage_text;
    setPrep("working", "Preparing your questions…", `${step} · ${s.calls} model calls · ${Math.round(s.elapsed_s)}s`, pct);
  } catch {
    $("prep-detail").textContent = "Reconnecting…";
  }
  setTimeout(() => poll(token), 1500);
}

$("start-assess").addEventListener("click", () => {
  idx = 0;
  results = [];
  sessionStart = Date.now();
  clearInterval(timerHandle);
  timerHandle = setInterval(() => { $("timer").textContent = fmt(Date.now() - sessionStart); }, 500);
  $("timer").textContent = "0:00";
  showQuestion();
});

// ---------- Assessment ----------
function renderSteps() {
  $("q-steps").innerHTML = questions.map((_, i) =>
    `<span class="step ${i < idx ? "done" : i === idx ? "now" : ""}"></span>`).join("");
}

function showQuestion() {
  const q = questions[idx];
  $("q-count").textContent = `Question ${idx + 1} of ${questions.length}`;
  $("q-kind").textContent = q.kind === "cloze" ? "Fill in the blank" : "Question";
  $("q-text").textContent = q.question.replace(/^Fill in the blank:\s*/i, "");
  $("attempt").value = "";
  $("submit").disabled = true;
  renderSteps();
  show("assess");
  $("attempt").focus({ preventScroll: true });
}

$("attempt").addEventListener("input", () => { $("submit").disabled = !$("attempt").value.trim(); });
$("attempt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if ($("attempt").value.trim()) submitAnswer(); }
});
$("answer-form").addEventListener("submit", (e) => { e.preventDefault(); submitAnswer(); });
$("unsure").addEventListener("click", () => { $("attempt").value = ""; submitAnswer(); });

async function submitAnswer() {
  const attempt = $("attempt").value.trim();
  $("submit").disabled = true;
  $("unsure").disabled = true;
  try {
    const res = await fetch(`/api/quest/${job}/answer`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: idx, attempt, seconds: null }) });
    const r = await res.json();
    results[idx] = r.correct;
    showReveal(attempt, r);
  } finally {
    $("unsure").disabled = false;
  }
}

// ---------- Evidence reveal ----------
function highlight(source, answer) {
  const s = esc(source), a = esc(answer);
  const i = a ? s.toLowerCase().indexOf(a.toLowerCase()) : -1;
  return i < 0 ? s : `${s.slice(0, i)}<mark>${s.slice(i, i + a.length)}</mark>${s.slice(i + a.length)}`;
}

function showReveal(attempt, r) {
  const v = $("verdict");
  v.className = "verdict card " + (r.correct ? "right" : "wrong");
  $("verdict-icon").textContent = r.correct ? "✓" : attempt ? "✕" : "?";
  $("reveal-title").textContent = r.correct ? "Correct" : attempt ? "Not quite" : "Here's the answer";
  $("r-yours").textContent = attempt || "No answer given";
  $("r-yours").className = "answer-text" + (attempt ? "" : " empty");
  $("r-correct").textContent = r.answer;
  $("r-source").innerHTML = highlight(r.source, r.answer);
  $("next").textContent = idx + 1 < questions.length ? "Next question →" : "See results →";
  show("reveal");
  $("next").focus({ preventScroll: true });  // keep the verdict at the top in view
}

$("next").addEventListener("click", () => {
  idx += 1;
  if (idx < questions.length) showQuestion();
  else finish();
});

// ---------- Results ----------
const METRICS = [
  ["total_run_s", "to prepare", (v) => `${v} s`],
  ["mean_decode_tok_per_s", "writing speed", (v) => `${v} tok/s`],
  ["peak_rss_mb", "peak memory", (v) => `${(v / 1024).toFixed(1)} GB`],
  ["model_mb", "model size", (v) => `${(v / 1024).toFixed(2)} GB`],
  ["llm_calls", "model calls", (v) => v],
];

async function finish() {
  clearInterval(timerHandle);
  const total = Date.now() - sessionStart;
  const d = await (await fetch(`/api/quest/${job}/finish`)).json();
  $("d-score").textContent = `${d.correct} of ${d.total}`;
  $("d-time").textContent = fmt(total);
  $("d-summary").textContent = d.summary || "No summary was produced.";
  $("d-summary-label").textContent = d.summary_source === "passage"
    ? "Key sentences from the passage · review them now"
    : "AI summary · every sentence checked against the passage";
  $("d-metrics").innerHTML = METRICS.filter(([k]) => d.metrics[k] != null)
    .map(([k, label, f]) => `<div class="metric"><b>${esc(f(d.metrics[k]))}</b><span>${label}</span></div>`).join("")
    + `<div class="metric"><b>Llama 3.2 1B</b><span>ExecuTorch &middot; on-device</span></div>`;
  show("done");
}

loadSamples();
