"""SelfCheck web UI: a local Flask server around the existing SelfCheck pipeline.

It reuses run_selfcheck() and LLM unchanged, so the CLI (selfcheck.py) keeps working as before.
Everything runs on the Raspberry Pi: no cloud APIs, and answers are only sent to the browser
after the student submits an attempt.

Run on the Pi:   python app.py      then open http://localhost:5000 (or the Pi's IP from a laptop)
"""
import glob
import json
import os
import threading
import time
import uuid

from flask import Flask, abort, jsonify, render_template, request

import selfcheck
from selfcheck import DEFAULT_PTE, DEFAULT_TOK

app = Flask(__name__)

_llm = None
_llm_lock = threading.Lock()  # one model, one generation at a time
_jobs = {}

STAGES = {
    0: "Picking key facts from the passage",
    1: "Writing a question for each fact",
    2: "Checking each question against the passage",
    3: "Writing the summary",
}


def get_llm():
    global _llm
    if _llm is None:
        from llm import LLM
        _llm = LLM(os.environ.get("SELFCHECK_PTE", DEFAULT_PTE), os.environ.get("SELFCHECK_TOK", DEFAULT_TOK))
    return _llm


class CountingLLM:
    """Wraps the shared LLM to report live progress (number of model calls) to the browser."""

    def __init__(self, llm, job):
        self.llm, self.job = llm, job

    def generate(self, prompt, max_new_tokens=40):
        self.job["calls"] += 1
        p = prompt.lower()
        if "summarise the passage" in p:
            self.job["stage"] = 3
        elif "answer the question using only the sentence" in p:
            self.job["stage"] = 2
        else:
            self.job["stage"] = 1
        return self.llm.generate(prompt, max_new_tokens)


def run_job(job_id, passage, n):
    job = _jobs[job_id]
    try:
        with _llm_lock:
            job["status"] = "running"
            t0 = time.perf_counter()
            llm = get_llm()
            first_call = len(llm.calls)
            items, summary, log = selfcheck.run_selfcheck(CountingLLM(llm, job), passage, n)
            total_s = round(time.perf_counter() - t0, 2)
            calls = llm.calls[first_call:]
            totals = llm.totals()
            rates = [c["tok_per_s"] for c in calls if c["tok_per_s"]]
            metrics = {
                "model_file": totals["model_file"],
                "model_mb": totals["model_mb"],
                "model_load_s": totals["model_load_s"],
                "llm_calls": len(calls),
                "generated_tokens": sum(c["gen_tokens"] or 0 for c in calls),
                "generation_wall_s": round(sum(c["wall_s"] for c in calls), 2),
                "mean_decode_tok_per_s": round(sum(rates) / len(rates), 2) if rates else None,
                "peak_rss_mb": totals["peak_rss_mb"],
                "total_run_s": total_s,
                "mode": "selfcheck",
                "passage_words": len(passage.split()),
                "questions": len(items),
                "cloze_fallbacks": sum(i["kind"] == "cloze" for i in items),
            }
        summary_info = next((l.get("summary_check") for l in log if l.get("summary_call")), None) or {}
        job.update(items=items, summary=summary, summary_source=summary_info.get("source", "checked"),
                   metrics=metrics, status="done", stage=4)
        os.makedirs("results_ui", exist_ok=True)  # kept apart from results/ so the evaluation stays clean
        with open(f"results_ui/{job_id}.json", "w", encoding="utf-8") as f:
            json.dump({"run_id": job_id, "passage": passage, "items": items, "summary": summary,
                       "metrics": metrics, "log": log}, f, indent=2, ensure_ascii=False)
    except Exception as e:  # shown to the user instead of hanging the loading screen
        job.update(status="error", error=f"{type(e).__name__}: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/samples")
def samples():
    out = []
    for path in sorted(glob.glob("passages/*.txt")):
        text = open(path, encoding="utf-8").read().strip()
        out.append({"name": os.path.splitext(os.path.basename(path))[0], "text": text})
    return jsonify(out)


@app.post("/api/quest")
def start_quest():
    data = request.get_json(force=True)
    passage = " ".join((data.get("passage") or "").split())
    words = len(passage.split())
    if words < 40:
        return jsonify(error="Please paste a longer passage (at least 40 words; 150-300 is best)."), 400
    if words > 600:
        return jsonify(error="That passage is too long for one quest. Please use up to 600 words."), 400
    n = max(3, min(5, int(data.get("n", 3))))
    job_id = time.strftime("%H%M%S") + "-" + uuid.uuid4().hex[:6]
    _jobs[job_id] = {"status": "queued", "stage": 0, "calls": 0, "started": time.time(), "answers": {}}
    threading.Thread(target=run_job, args=(job_id, passage, n), daemon=True).start()
    return jsonify(job_id=job_id)


@app.get("/api/quest/<job_id>")
def quest_status(job_id):
    job = _jobs.get(job_id) or abort(404)
    out = {"status": job["status"], "stage": job["stage"], "stage_text": STAGES.get(job["stage"], "Ready"),
           "calls": job["calls"], "elapsed_s": round(time.time() - job["started"], 1)}
    if job["status"] == "done":
        # Questions only: answers and sources stay on the Pi until the student submits.
        out["questions"] = [{"question": it["question"], "kind": it["kind"]} for it in job["items"]]
    if job["status"] == "error":
        out["error"] = job["error"]
    return jsonify(out)


@app.post("/api/quest/<job_id>/answer")
def submit_answer(job_id):
    job = _jobs.get(job_id) or abort(404)
    if job["status"] != "done":
        abort(409)
    data = request.get_json(force=True)
    i = int(data.get("index", -1))
    if not 0 <= i < len(job["items"]):
        abort(400)
    attempt = (data.get("attempt") or "").strip()
    item = job["items"][i]
    a, b = attempt.lower(), item["answer"].lower()
    correct = bool(a) and (a in b or b in a)  # same rule as the CLI's interactive mode
    job["answers"][i] = {"attempt": attempt, "correct": correct, "seconds": data.get("seconds")}
    return jsonify(correct=correct, answer=item["answer"], source=item["source"], kind=item["kind"])


@app.get("/api/quest/<job_id>/finish")
def finish(job_id):
    job = _jobs.get(job_id) or abort(404)
    if job["status"] != "done":
        abort(409)
    return jsonify(summary=job["summary"], summary_source=job.get("summary_source", "checked"), metrics=job["metrics"],
                   correct=sum(1 for a in job["answers"].values() if a["correct"]),
                   answered=len(job["answers"]), total=len(job["items"]))


def warm_up():
    """Load the model in the background so the first quest starts faster."""
    with _llm_lock:
        try:
            get_llm().generate("<|begin_of_text|>Hi", max_new_tokens=1)
        except Exception as e:
            print("Warm-up failed:", e)


if __name__ == "__main__":
    # Lower priority, so a browser on the same Pi stays smooth while the model uses the CPU.
    # Generation speed is unchanged when nothing else is running.
    try:
        os.nice(int(os.environ.get("SELFCHECK_NICE", 10)))
    except (AttributeError, OSError):
        pass
    threading.Thread(target=warm_up, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
