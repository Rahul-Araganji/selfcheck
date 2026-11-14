// SelfCheck UI. All AI work happens in the local Flask backend on the Pi; timers run here in the browser.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ---------- Saved progress (per browser; the app works without it) ----------
const store = {
  get(k, d) { try { const v = localStorage.getItem("selfcheck." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("selfcheck." + k, JSON.stringify(v)); } catch {} },
};
let xp = store.get("xp", 0);
const XP_PER_LEVEL = 100;

function renderXP() {
  $("lvl").textContent = Math.floor(xp / XP_PER_LEVEL) + 1;
  $("xpnum").textContent = xp;
  $("xpfill").style.width = ((xp % XP_PER_LEVEL) / XP_PER_LEVEL) * 100 + "%";
  $("st-quests").textContent = store.get("quests", 0);
  $("st-correct").textContent = store.get("correct", 0);
}

function addXP(amount, anchor) {
  xp += amount;
  store.set("xp", xp);
  renderXP();
  if (anchor) {
    const r = anchor.getBoundingClientRect();
    const pop = document.createElement("div");
    pop.className = "xp-pop";
    pop.textContent = `+${amount} XP`;
    pop.style.left = r.left + r.width / 2 - 40 + "px";
    pop.style.top = r.top - 10 + "px";
    document.body.appendChild(pop);
    setTimeout(() => pop.remove(), 1200);
  }
}

// ---------- Screens ----------
function show(name) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("active", s.id === "s-" + name));
  window.scrollTo(0, 0);
  if (name === "passage") setTimeout(() => $("passage").focus(), 50);
}
document.addEventListener("click", (e) => {
  const go = e.target.closest("[data-go]");
  if (go) show(go.dataset.go);
});

// ---------- Passage input ----------
async function loadSamples() {
  try {
    const list = await (await fetch("/api/samples")).json();
    $("samples").innerHTML = list.map((s, i) => `<button class="chip" data-i="${i}">${esc(s.name)}</button>`).join("");
    $("samples").onclick = (e) => {
      const b = e.target.closest(".chip");
      if (!b) return;
      $("passage").value = list[b.dataset.i].text;
      updateCount();
    };
  } catch { /* samples are optional */ }
}

function updateCount() {
  const n = $("passage").value.trim().split(/\s+/).filter(Boolean).length;
  $("wc").textContent = n;
  const c = $("counter");
  c.className = "counter " + (n >= 150 && n <= 300 ? "good" : n >= 40 && n <= 600 ? "warn" : "bad");
  $("wc-hint").textContent = n < 40 ? "(need at least 40)" : n >= 150 && n <= 300 ? "(perfect length)" : n > 600 ? "(too long)" : "(aim for 150-300)";
  $("generate").disabled = n < 40 || n > 600;
}
$("passage").addEventListener("input", updateCount);

// ---------- Generation with live progress ----------
let job = null, questions = [], idx = 0, results = [];
let qStart = 0, sStart = 0, timerHandle = null;

$("generate").addEventListener("click", async () => {
  $("pass-error").textContent = "";
  $("load-error").textContent = "";
  $("generate").disabled = true;
  try {
    const res = await fetch("/api/quest", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passage: $("passage").value }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not start the quest.");
    job = data.job_id;
    $("blocks").innerHTML = "<i></i>".repeat(7);
    show("loading");
    poll();
  } catch (err) {
    $("pass-error").textContent = err.message;
  } finally {
    updateCount();
  }
});

async function poll() {
  try {
    const s = await (await fetch(`/api/quest/${job}`)).json();
    $("calls").textContent = s.calls;
    $("elapsed").textContent = Math.round(s.elapsed_s);
    $("stage").textContent = s.status === "queued" ? "Waiting for the model..." : s.calls === 0 ? "Loading the model and picking facts" : s.stage_text + "...";
    document.querySelectorAll("#steps li").forEach((li) => {
      const n = Number(li.dataset.s);
      li.className = n < s.stage ? "done" : n === s.stage ? "now" : "";
    });
    if (s.status === "done") return startQuiz(s.questions);
    if (s.status === "error") { $("load-error").textContent = "Something went wrong: " + s.error; return; }
  } catch {
    $("stage").textContent = "Reconnecting to the Pi...";
  }
  setTimeout(poll, 800);
}

// ---------- Quiz ----------
const fmt = (ms) => { const t = Math.floor(ms / 1000); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`; };

function tick() {
  const now = Date.now();
  $("t-q").textContent = fmt(now - qStart);
  $("t-s").textContent = fmt(now - sStart);
}

function startQuiz(qs) {
  questions = qs;
  idx = 0;
  results = [];
  sStart = Date.now();
  clearInterval(timerHandle);
  timerHandle = setInterval(tick, 250);
  show("quiz");
  showQuestion();
}

function renderHearts() {
  $("progress").innerHTML = questions.map((_, i) => {
    const r = results[i];
    const name = r === undefined ? "heartEmpty" : r ? "heart" : "heartBroken";
    return `<span class="art" style="opacity:${r === undefined && i !== idx ? 0.45 : 1}">${spriteSVG(name, 3)}</span>`;
  }).join("");
}

function showQuestion() {
  const q = questions[idx];
  $("q-count").textContent = `Question ${idx + 1} of ${questions.length}`;
  $("q-text").textContent = q.question;
  const tag = $("q-kind");
  tag.textContent = q.kind === "cloze" ? "FILL IN THE BLANK" : "VERIFIED QUESTION";
  tag.className = "tag" + (q.kind === "cloze" ? " cloze" : "");
  $("attempt").value = "";
  $("attempt").disabled = false;
  $("submit").disabled = false;
  $("answer-form").hidden = false;
  $("reveal").hidden = true;
  renderHearts();
  qStart = Date.now();
  tick();
  $("attempt").focus();
}

function highlight(source, answer) {
  const s = esc(source), a = esc(answer);
  if (!a) return s;
  const i = s.toLowerCase().indexOf(a.toLowerCase());
  return i < 0 ? s : s.slice(0, i) + "<mark>" + s.slice(i, i + a.length) + "</mark>" + s.slice(i + a.length);
}

$("answer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("submit").disabled = true;
  $("attempt").disabled = true;
  const seconds = Math.round((Date.now() - qStart) / 1000);
  try {
    const res = await fetch(`/api/quest/${job}/answer`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: idx, attempt: $("attempt").value, seconds }) });
    const r = await res.json();
    results[idx] = r.correct;
    $("verdict").textContent = r.correct ? "Nice! You got it." : $("attempt").value.trim() ? "Not quite. Here's the answer." : "Here's the answer.";
    $("verdict").className = "verdict " + (r.correct ? "yes" : "no");
    $("r-answer").textContent = r.answer;
    $("r-source").innerHTML = highlight(r.source, r.answer);
    $("answer-form").hidden = true;
    $("reveal").hidden = false;
    $("next").textContent = idx + 1 < questions.length ? "NEXT ▶" : "FINISH QUEST ▶";
    renderHearts();
    addXP(r.correct ? 25 : 5, $("verdict"));
    $("next").focus();
  } catch {
    $("submit").disabled = false;
    $("attempt").disabled = false;
  }
});

$("next").addEventListener("click", () => {
  idx += 1;
  if (idx < questions.length) showQuestion();
  else finishQuest();
});

// ---------- Quest complete ----------
const METRIC_LABELS = [
  ["model_file", "Model"], ["model_mb", "Model size (MB)"], ["mean_decode_tok_per_s", "Speed (tokens/s)"],
  ["peak_rss_mb", "Peak memory (MB)"], ["total_run_s", "Generation time (s)"], ["llm_calls", "Model calls"],
  ["generated_tokens", "Tokens generated"], ["model_load_s", "Model load (s)"], ["passage_words", "Passage words"],
  ["cloze_fallbacks", "Fill-in-the-blank fallbacks"],
];

async function finishQuest() {
  clearInterval(timerHandle);
  const total = Date.now() - sStart;
  const d = await (await fetch(`/api/quest/${job}/finish`)).json();
  $("d-score").textContent = `${d.correct}/${d.total}`;
  $("d-time").textContent = fmt(total);
  $("d-summary").textContent = d.summary || "(No summary was produced.)";
  $("d-metrics").innerHTML = METRIC_LABELS.filter(([k]) => d.metrics[k] !== undefined && d.metrics[k] !== null)
    .map(([k, label]) => `<tr><td>${label}</td><td>${esc(d.metrics[k])}</td></tr>`).join("");
  const bonus = 20;
  const earned = results.reduce((s, r) => s + (r ? 25 : 5), 0) + bonus;
  $("d-xp").textContent = "+" + earned;
  store.set("quests", store.get("quests", 0) + 1);
  store.set("correct", store.get("correct", 0) + d.correct);
  show("done");
  addXP(bonus, $("d-xp"));
}

// ---------- Start ----------
paintArt();
renderXP();
loadSamples();
updateCount();
