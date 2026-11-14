"""Build a blind, shuffled labelling sheet from results/*.json.

Writes:
  results/label_sheet.csv  questions from both versions, shuffled, version hidden
  results/label_key.csv    which version made each question (don't show labellers)
Labellers fill two columns with yes or no:
  good      = the question can be answered from the passage AND the given answer is correct.
  important = the question tests a key idea of the passage, not a minor detail.
"""
import csv
import glob
import json
import random

rows = []
for path in sorted(glob.glob("results/*.json")):
    run = json.load(open(path, encoding="utf-8"))
    passage_file = run["run_id"].split("-", 2)[2]
    for it in run["items"]:
        rows.append({
            "passage": passage_file,
            "question": it["question"],
            "given_answer": it["answer"],
            "mode": run["metrics"]["mode"],
            "kind": it["kind"],
            "run_id": run["run_id"],
        })

random.seed(14)  # fixed so the sheet can be rebuilt identically
random.shuffle(rows)
rows.sort(key=lambda r: r["passage"])  # group by passage so labellers read each passage once

with open("results/label_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "passage", "question", "given_answer", "good (yes/no)", "important (yes/no)", "note"])
    for i, r in enumerate(rows, 1):
        w.writerow([i, r["passage"], r["question"], r["given_answer"], "", "", ""])

with open("results/label_key.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "mode", "kind", "run_id"])
    for i, r in enumerate(rows, 1):
        w.writerow([i, r["mode"], r["kind"], r["run_id"]])

print(f"{len(rows)} questions from {len(set(r['passage'] for r in rows))} passages "
      "-> results/label_sheet.csv (key in results/label_key.csv)")
