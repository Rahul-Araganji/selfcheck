"""Generate a summary for each practice passage and show what the summary check keeps or drops."""
import glob
import json

import prompts
import summary_check
from llm import LLM
from selfcheck import DEFAULT_PTE, DEFAULT_TOK, strip_preamble

llm = LLM(DEFAULT_PTE, DEFAULT_TOK)
report = []
for path in sorted(glob.glob("passages/sample*.txt")):
    passage = open(path, encoding="utf-8").read().strip()
    raw, call = llm.generate(prompts.summary(passage), max_new_tokens=90)
    text, info = summary_check.checked_summary(strip_preamble(raw), passage)
    report.append({"passage": path, "raw": raw, "shown": text, "info": info, "seconds": call["wall_s"]})
    print(f"\n===== {path}  ({info['source']}, {call['wall_s']} s)")
    for k in info["kept"]:
        print("  KEEP:", k["sentence"])
    for d in info["dropped"]:
        print("  DROP:", d["sentence"], "|", d["reason"])
    print("  SHOWN:", text)
json.dump(report, open("results/summary_check.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
checked = sum(r["info"]["source"] == "checked" for r in report)
print(f"\n{checked}/{len(report)} summaries used checked AI sentences; the rest used the passage's own sentences.")
