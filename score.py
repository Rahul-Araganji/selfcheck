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
    for r in csv.DictReader(open("results/label_sheet.csv", encoding="utf-8-sig")):
        label = r["good (yes/no)"].strip().lower()
        if label in ("yes", "y", "no", "n"):
            mode = key[r["id"]]["mode"]
            counts[mode][1] += 1
            counts[mode][0] += label.startswith("y")
    print("=== Question quality (blind human labels) ===")
    if counts:
        for mode, (good, total) in sorted(counts.items()):
            print(f"  {mode}: {good}/{total} good ({100 * good / total:.0f}%)")
    else:
        print("  No labels yet: fill the 'good (yes/no)' column in results/label_sheet.csv")
except FileNotFoundError:
    print("Run make_sheet.py first.")

# Speed and memory
by_mode = defaultdict(list)
for path in glob.glob("results/*.json"):
    m = json.load(open(path, encoding="utf-8"))["metrics"]
    by_mode[m["mode"]].append(m)
print("\n=== Speed and memory (Raspberry Pi 5) ===")
for mode, ms in sorted(by_mode.items()):
    def avg(k):
        vals = [x[k] for x in ms if x.get(k) is not None]
        return round(statistics.mean(vals), 2) if vals else None
    print(f"  {mode}: {len(ms)} runs | total {avg('total_run_s')} s | "
          f"{avg('mean_decode_tok_per_s')} tok/s | peak {max(x['peak_rss_mb'] for x in ms)} MB | "
          f"load {avg('model_load_s')} s | fallbacks {sum(x.get('cloze_fallbacks', 0) for x in ms)}")
