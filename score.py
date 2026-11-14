"""Results summary: question quality from the blind labels, plus speed and memory from all runs."""
import csv
import glob
import json
import statistics
from collections import defaultdict

# Question quality (needs results/label_sheet.csv filled in, and results/label_key.csv)
try:
    key = {r["id"]: r for r in csv.DictReader(open("results/label_key.csv", encoding="utf-8"))}
    counts = defaultdict(lambda: [0, 0])
    imp = defaultdict(lambda: [0, 0])
    sheets = sorted(glob.glob("results/label_sheet*.csv"))  # one file per labeller is fine
    for sheet in sheets:
        for r in csv.DictReader(open(sheet, encoding="utf-8-sig")):
            mode = key[r["id"]]["mode"]
            label = r["good (yes/no)"].strip().lower()
            if label in ("yes", "y", "no", "n"):
                counts[mode][1] += 1
                counts[mode][0] += label.startswith("y")
            label = r.get("important (yes/no)", "").strip().lower()
            if label in ("yes", "y", "no", "n"):
                imp[mode][1] += 1
                imp[mode][0] += label.startswith("y")
    print(f"=== Question quality (blind human labels, {len(sheets)} sheet(s)) ===")
    if counts:
        for mode, (good, total) in sorted(counts.items()):
            i_good, i_total = imp[mode]
            extra = f" | important {i_good}/{i_total} ({100 * i_good / i_total:.0f}%)" if i_total else ""
            print(f"  {mode}: good {good}/{total} ({100 * good / total:.0f}%){extra}")
    else:
        print("  No labels yet: fill the 'good (yes/no)' column in results/label_sheet.csv")
except FileNotFoundError:
    print("Run make_sheet.py first.")

# Automatic evidence checks, identical for every version
import evidence

by_mode = defaultdict(list)
auto = defaultdict(lambda: defaultdict(int))
for path in glob.glob("results/*.json"):
    run = json.load(open(path, encoding="utf-8"))
    m = run["metrics"]
    by_mode[m["mode"]].append(m)
    a = auto[m["mode"]]
    for it in run["items"]:
        a["questions"] += 1
        a["supported"] += evidence.support(it["question"], it["answer"], run["passage"])
        a["verbatim"] += evidence.verbatim(it["answer"], run["passage"])
        a["traceable"] += evidence.traceable(it, run["passage"])
    cov = evidence.coverage(run["items"], run["passage"])
    a["runs"] += 1
    a["sections"] += cov["sections_covered"]
    a["keys_hit"] += cov["key_terms_covered"]
    a["keys_total"] += cov["key_terms_total"]

print("\n=== Automatic checks (same rules for every version) ===")
for mode, a in sorted(auto.items()):
    q = a["questions"] or 1
    print(f"  {mode}: answer copied word-for-word from passage {a['verbatim']}/{a['questions']} "
          f"({100 * a['verbatim'] / q:.0f}%) | real source sentence shown {a['traceable']}/{a['questions']} "
          f"({100 * a['traceable'] / q:.0f}%) | sections covered {a['sections'] / a['runs']:.1f}/3 | "
          f"key terms covered {100 * a['keys_hit'] / max(a['keys_total'], 1):.0f}%")
print("  (rough one-sentence evidence check, biased against long answers, not a headline: "
      + ", ".join(f"{m} {100 * a['supported'] / (a['questions'] or 1):.0f}%" for m, a in sorted(auto.items())) + ")")
print("\n=== Speed and memory (Raspberry Pi 5) ===")
for mode, ms in sorted(by_mode.items()):
    def avg(k):
        vals = [x[k] for x in ms if x.get(k) is not None]
        return round(statistics.mean(vals), 2) if vals else None
    print(f"  {mode}: {len(ms)} runs | total {avg('total_run_s')} s | "
          f"{avg('mean_decode_tok_per_s')} tok/s | peak {max(x['peak_rss_mb'] for x in ms)} MB | "
          f"load {avg('model_load_s')} s | fallbacks {sum(x.get('cloze_fallbacks', 0) for x in ms)}")
