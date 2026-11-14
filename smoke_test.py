"""Quick check: model loads, writes two questions, and reports speed and memory."""
import sys

import prompts
from llm import LLM

pte = sys.argv[1] if len(sys.argv) > 1 else "models/llama/1b/xnnpack/llama_3_2_1b_xnnpack_spinquant.pte"
tok = sys.argv[2] if len(sys.argv) > 2 else "models/llama/tokenizer.json"

m = LLM(pte, tok)
print("LOAD_S", m.load_s)
tests = [
    ("Chloroplasts contain a green pigment called chlorophyll, which absorbs energy from sunlight.", "chlorophyll"),
    ("Water is absorbed by the roots and carried up to the leaves through vessels called xylem.", "xylem"),
]
for sentence, answer in tests:
    q, call = m.generate(prompts.question(sentence, answer), 40)
    print("Q:", repr(q))
    print("CALL", call)
print("TOTALS", m.totals())
