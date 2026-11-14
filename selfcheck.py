"""SelfCheck: offline study aid. Passage in, checked quiz questions and a summary out.

Usage:
  python selfcheck.py passages/sample1.txt                 # SelfCheck, prints everything
  python selfcheck.py passages/sample1.txt --interactive   # student attempts before reveal
  python selfcheck.py passages/sample1.txt --mode baseline # one-prompt baseline, for comparison
"""
import argparse
import csv
import json
import os
import re
import time

import picker
import prompts

DEFAULT_PTE = "models/llama/1b/xnnpack/llama_3_2_1b_xnnpack_spinquant.pte"
DEFAULT_TOK = "models/llama/tokenizer.json"


def first_line(text):
    for line in text.splitlines():
        line = re.sub(r"^\s*(question|q\d*)\s*[:.)-]\s*", "", line.strip(), flags=re.I).strip(" \"'")
        if line:
            return line
    return ""


def check_question(q, answer, sentence):
    """Return None if the question passes, else the reason it was rejected."""
    if not q.endswith("?"):
        return "no question mark"
    if len(q.split()) < 4:
        return "too short"
    if re.search(r"\b" + re.escape(answer.lower()) + r"\b", q.lower()):
        return "gives away the answer"
    answer_words = set(picker.content_words(answer))
    shared = (set(picker.content_words(q)) & set(picker.content_words(sentence))) - answer_words
    if not shared:
        return "off topic"
    return None


def key_terms(text):
    """Content words plus numbers, for comparing answers."""
    nums = set(re.findall(r"\d[\d,.]*", text))
    return set(picker.content_words(text)) | {n.strip(",.") for n in nums}


def answers_match(chosen, back, question):
    """The model's own answer must contain the chosen answer and add nothing beyond the question's words."""
    want, got = key_terms(chosen), key_terms(back)
    if not want or not want <= got:
        return False
    extra = got - want - key_terms(question)
    return not extra


def strip_preamble(text):
    """Drop a leading line like 'Here is a summary of the passage:'."""
    lines = [l for l in text.strip().splitlines()]
    while lines and (not lines[0].strip() or (lines[0].strip().endswith(":") and len(lines) > 1)):
        lines.pop(0)
    return "\n".join(lines).strip()


def cloze(sentence, answer):
    blank = re.sub(re.escape(answer), "_____", sentence, count=1, flags=re.I)
    return "Fill in the blank: " + blank


def run_selfcheck(llm, passage, n_questions):
    items, log = [], []
    for sentence, answers in picker.pick(passage, k=max(5, n_questions + 2)):
        if len(items) == n_questions:
            break
        made = None
        for answer in answers[:2]:  # at most two model attempts per sentence
            raw, call = llm.generate(prompts.question(sentence, answer), max_new_tokens=40)
            q = first_line(raw)
            reason = check_question(q, answer, sentence)
            back = None
            if reason is None:
                back_raw, back_call = llm.generate(prompts.answer_back(sentence, q), max_new_tokens=16)
                back = first_line(back_raw).rstrip(".")
                if not answers_match(answer, back, q):
                    reason = f"answer-back mismatch (model answered: {back})"
            log.append({"sentence": sentence, "answer": answer, "raw": raw, "answer_back": back,
                        "rejected": reason, **call})
            if reason is None:
                made = {"question": q, "answer": answer, "source": sentence, "kind": "model"}
                break
        if made is None:
            answer = answers[0]
            made = {"question": cloze(sentence, answer), "answer": answer, "source": sentence, "kind": "cloze"}
        items.append(made)
    summary, call = llm.generate(prompts.summary(passage), max_new_tokens=90)
    summary = strip_preamble(summary)
    log.append({"summary_call": True, **call})
    return items, summary, log


def run_baseline(llm, passage):
    raw, call = llm.generate(prompts.baseline(passage), max_new_tokens=220)
    summary = ""
    m = re.search(r"Summary:\s*(.+?)(?=\n\s*Q1|\Z)", raw, flags=re.S | re.I)
    if m:
        summary = m.group(1).strip()
    items = []
    for i in range(1, 6):
        q = re.search(rf"Q{i}\s*[:.)]\s*(.+)", raw)
        a = re.search(rf"A{i}\s*[:.)]\s*(.+)", raw)
        if q:
            items.append({"question": q.group(1).strip(" *"), "answer": a.group(1).strip(" *") if a else "",
                          "source": "", "kind": "baseline"})
    return items, summary, [{"raw": raw, **call}]


def show(items, summary, interactive):
    print("\n=== Quiz ===")
    for i, it in enumerate(items, 1):
        print(f"\nQ{i}. {it['question']}")
        if interactive:
            attempt = input("Your answer: ").strip()
            a, b = attempt.lower(), it["answer"].lower()
            ok = bool(a) and (a in b or b in a)
            print("  Matches!" if ok else "  Compare with the answer below.")
        print(f"  Answer: {it['answer']}")
        if it["source"]:
            print(f"  Source: \"{it['source']}\"")
        if it["kind"] == "cloze":
            print("  (fill-in-the-blank: the model's question did not pass the checks)")
    print("\n=== Summary ===")
    print(summary or "(no summary produced)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("passage")
    ap.add_argument("--mode", choices=["selfcheck", "baseline"], default="selfcheck")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--n", type=int, default=3, help="number of questions (at least 3 for the brief)")
    ap.add_argument("--pte", default=DEFAULT_PTE)
    ap.add_argument("--tokenizer", default=DEFAULT_TOK)
    args = ap.parse_args()

    passage = open(args.passage, encoding="utf-8").read().strip()
    from llm import LLM  # imported here so --help works without ExecuTorch

    t0 = time.perf_counter()
    llm = LLM(args.pte, args.tokenizer)
    if args.mode == "selfcheck":
        items, summary, log = run_selfcheck(llm, passage, args.n)
    else:
        items, summary, log = run_baseline(llm, passage)
    total_s = round(time.perf_counter() - t0, 2)

    show(items, summary, args.interactive)

    metrics = {**llm.totals(), "total_run_s": total_s, "mode": args.mode,
               "passage_words": len(passage.split()),
               "questions": len(items), "cloze_fallbacks": sum(i["kind"] == "cloze" for i in items)}
    print("\n=== Metrics (offline, on-device) ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    os.makedirs("results", exist_ok=True)
    run_id = time.strftime("%H%M%S") + "-" + args.mode + "-" + os.path.splitext(os.path.basename(args.passage))[0]
    with open(f"results/{run_id}.json", "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, "passage": passage, "items": items, "summary": summary,
                   "metrics": metrics, "log": log}, f, indent=2, ensure_ascii=False)
    new = not os.path.exists("results/labels.csv")
    with open("results/labels.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_id", "mode", "q_no", "question", "answer", "source", "kind", "answerable_yes_no"])
        for i, it in enumerate(items, 1):
            w.writerow([run_id, args.mode, i, it["question"], it["answer"], it["source"], it["kind"], ""])
    print(f"\nSaved results/{run_id}.json and appended to results/labels.csv")


if __name__ == "__main__":
    main()
