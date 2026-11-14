"""Answerable-question rate per mode, from results/labels.csv after teammates fill in yes/no."""
import csv
from collections import defaultdict

counts = defaultdict(lambda: [0, 0])
with open("results/labels.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        label = row["answerable_yes_no"].strip().lower()
        if label in ("yes", "no"):
            counts[row["mode"]][1] += 1
            counts[row["mode"]][0] += label == "yes"

for mode, (yes, total) in counts.items():
    print(f"{mode}: {yes}/{total} answerable ({100 * yes / total:.0f}%)")
if not counts:
    print("No labelled rows yet: fill the answerable_yes_no column with yes or no.")
