# SelfCheck: context for an AI assistant

## Situation
- Namma AI Hackathon (Arm + IIIT Bangalore + NASSCOM), live build today, ends 6 PM.
- Problem Statement 1: offline learning assistant using ExecuTorch on Raspberry Pi.
- Mandatory: process the organisers' 150-300 word passage locally on the Pi with ExecuTorch;
  output a short summary and at least 3 quiz questions (terminal output is fine); no cloud AI;
  report inference time, model, model size/memory; short impact explanation with one example
  from the passage; code on GitHub.

## Our idea
Learner: Class 9-10 students who can read a textbook passage but have no quick way to check,
alone, whether they understood it. Small models often write questions the passage cannot
answer, and a student studying alone cannot spot that. So SelfCheck picks the ANSWER first with
plain code, then has the model write the question, then verifies it. The student attempts each
question before seeing the answer and its source sentence (retrieval practice with feedback).
The summary comes after the quiz.

## Hardware and software (working)
- Raspberry Pi 5, 8 GB, Raspberry Pi OS 64-bit (Debian 13 Trixie), glibc 2.41, Python 3.13.5.
- SSH: katz@192.168.102.247 (venue Wi-Fi IOT-STARTUP2).
- Venv: ~/selfcheck-env. torch 2.15.0+cpu (CPU-only index; the default PyPI torch pulls CUDA
  packages, avoid), executorch 1.6.0, huggingface_hub.
- Project folder on Pi: ~/selfcheck
- Models (downloaded, from Hugging Face, ungated):
  - models/llama/1b/xnnpack/llama_3_2_1b_xnnpack_spinquant.pte (1,082 MB) + models/llama/tokenizer.json  [default]
  - models/qwen/0_6b/xnnpack/qwen_3_0_6b_xnnpack_8da4w.pte (518 MB) + models/qwen/tokenizer.json  [backup, not yet tested; needs ChatML prompts]
- Python API used: executorch.extension.llm.runner.TextLLMRunner(pte, tokenizer);
  runner.generate(prompt, GenerationConfig(echo=False, max_new_tokens=N, temperature=0.0),
  token_callback, stats_callback); runner.reset() between prompts. Must first import
  executorch.extension.llm.custom_ops.custom_ops and executorch.kernels.quantized.
  The model loads lazily on the first generate(). The C++ runner prints raw tokens to stdout,
  so llm.py silences file descriptor 1 during generation.

## Files
- llm.py: wrapper around TextLLMRunner; returns cleaned text plus per-call stats
  (wall time, prompt/generated tokens, decode tok/s); totals() gives model size, load time,
  peak RSS.
- picker.py: plain Python. Splits sentences, ranks them by keyword frequency (bonus for
  numbers and "called/known as" definitions), and picks answer spans in priority order:
  defined terms, dates, numbers, names, rare words. Skips topic words used 3+ times
  unless explicitly defined.
- prompts.py: Llama 3.2 chat-format prompts: question (one-shot example, sentence + answer),
  answer_back (model answers its own question from the sentence), summary, baseline
  (one prompt for summary + 3 Q&A, used only for comparison).
- selfcheck.py: main program. For each picked sentence: generate question -> checks
  (ends with "?", 4+ words, does not contain answer, shares a word with the sentence) ->
  answer-back check (model's answer must contain the chosen answer and add no words beyond
  the question). Up to 2 tries per sentence, else a fill-in-the-blank fallback. Then summary.
  Prints quiz, summary, metrics. Saves results/<run>.json and appends results/labels.csv.
  Flags: --mode selfcheck|baseline, --interactive, --n, --pte, --tokenizer.
- score.py: answerable rate per mode from labels.csv once humans fill answerable_yes_no.
- smoke_test.py: two test questions plus speed numbers.
- passages/sample1.txt (photosynthesis), sample2.txt (water cycle), sample3.txt (Indian
  Constitution): practice passages written by the team; the real one is given by organisers.
- setup/install_cpu.sh, setup/get_models.sh: install and model download scripts.

## Results so far (3 practice passages, Pi 5)
- About 11 tokens/s decode, about 100-110 tokens/s prompt reading, about 2.6 GB peak RAM,
  model load 3-6 s, about 24-33 s per passage for 3 questions + summary (7-10 model calls).
- Baseline (one prompt): 2 of 9 answers wrong or unsupported ("becomes groundwater";
  Ambedkar "chaired the Constituent Assembly" while the passage says Drafting Committee).
- SelfCheck: no answer mismatches seen; answer-back caught the model inventing
  "The Bill of Rights". 3 of 9 questions fell back to fill-in-the-blank. Known limit: one
  question asked two things ("adopted and came into effect").
- Not yet done: human labelling, more passages, GitHub push, README, Qwen backup test.

## Rules for helping
- Keep it working; test on the Pi after every change. Don't overclaim learning gains.
- Credit "Built with Llama" (Llama 3.2 licence).
