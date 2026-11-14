# SelfCheck: full context for an AI assistant

## Situation
- Namma AI Hackathon 2026 (Arm + IIIT Bangalore + NASSCOM). Live build today (14 Nov), ends 6 PM.
- Problem Statement 1: offline learning assistant using ExecuTorch on a Raspberry Pi.
- Mandatory deliverables: process the organisers' 150-300 word passage locally on the Pi with
  ExecuTorch; output a short summary and at least 3 quiz questions (terminal output is fine); no cloud
  AI; report inference time, model, model size/memory; a short impact explanation with one example
  from the passage; code on GitHub (https://github.com/Rahul-Araganji/selfcheck).
- No official judging rubric was published; organisers say "practical implementation, measurable
  results and societal relevance".

## The idea (pitch)
Reading doesn't check retention; answering questions does (retrieval practice; research is mostly
outside India, so it guides the design, it doesn't predict our effect). But small AI models often
write questions the passage can't answer, or give wrong answers, and a student studying alone can't
tell. SelfCheck reverses the usual approach:
1. Plain code picks a key sentence and an answer straight from the passage (cannot be made up).
2. The on-device model writes one question for that answer, seeing only that sentence.
3. Checks: must end in "?", not give the answer away, stay on topic. Then the model must answer its
   own question from the sentence; if that answer doesn't match, the question is thrown out and the
   next fact is tried. If nothing passes, a fill-in-the-blank question is used instead.
4. The student answers first, then sees the answer and the exact source sentence.
5. Questions are spread across the beginning, middle and end of the passage; key ideas
   (definitions, numbers, causes) are prioritised.
6. A short summary is shown after the quiz (recall first, then review).
Learner: Class 9-10 students who can read the passage but have no quick way to check, alone,
whether they understood it. (The missing self-check is an inference; no survey measures it.)
One-liner: "Other AI quizzes make the question first and hope the answer is right. We take the
answer from the book first, then build and check the question around it, and show the proof."

## Hardware and software (working)
- Raspberry Pi 5, 8 GB, Raspberry Pi OS 64-bit (Debian 13 Trixie), glibc 2.41, Python 3.13.5.
- SSH: katz@192.168.102.247 (venue Wi-Fi IOT-STARTUP2). Venv: ~/selfcheck-env. Project: ~/selfcheck
- torch 2.15.0+cpu (installed from the PyTorch CPU index; the default PyPI torch pulls useless CUDA
  packages), executorch 1.6.0, huggingface_hub, flask.
- Model: Llama 3.2 1B Instruct, SpinQuant INT4, ExecuTorch .pte (1,082 MB) from
  software-mansion/Llama-3.2-ExecuTorch; backup Qwen3 0.6B (518 MB, downloaded, not tested).
- API: executorch.extension.llm.runner.TextLLMRunner(pte, tokenizer).generate(prompt,
  GenerationConfig(...), token_cb, stats_cb); runner.reset() between prompts. The model loads on the
  first generate(). The C++ runner prints raw tokens to stdout, so llm.py hides them during generation.

## How to run (on the Pi)
```
cd ~/selfcheck && source ~/selfcheck-env/bin/activate
python selfcheck.py passages/sample1.txt --interactive 2>/dev/null   # CLI, student mode
python selfcheck.py passages/sample1.txt --mode baseline 2>/dev/null # basic prompt (or --mode careful)
python app.py      # web UI on http://localhost:5000 or http://192.168.102.247:5000
```
For the organisers' passage: save it as passages/official.txt and run either way.

## Files
- selfcheck.py: CLI and the pipeline (run_selfcheck, run_baseline with basic/careful prompts).
- picker.py: no-AI sentence and answer selection, coverage across passage sections.
- prompts.py: Llama 3.2 prompts (question, answer-back, summary, basic, careful).
- llm.py: ExecuTorch wrapper with timing, tokens/s and peak memory.
- app.py + templates/ + static/: offline game-style Flask UI (welcome, passage with word meter,
  live progress, quiz with timers and XP, reveal with highlighted source, completion with summary
  and real metrics). Reuses run_selfcheck unchanged; answers are sent only after submission;
  runs at lower CPU priority so the Pi's browser stays responsive.
- evidence.py, score.py, make_sheet.py: automatic checks, blind labelling sheet, scoring.
- setup/: install_cpu.sh, get_models.sh, run_eval.sh. passages/: 8 practice passages written by the
  team (photosynthesis, water cycle, Constitution, heart, Revolt of 1857, sound, money and credit, soils).
- results/: run outputs, label_sheet.csv (blind), label_sheet_evaluated.csv (labelled), label_key.csv.

## Results
On-device (Pi 5): about 11-12.5 tokens/s writing, about 100-110 tokens/s prompt reading, about
2.6 GB peak memory, model load about 3 s, SelfCheck about 20-40 s per passage (3 questions + summary).

Fair three-way test, same model, same Pi, 8 passages, 70 questions shuffled and labelled blind
(the labeller didn't know which version wrote which question):

| Measure | Basic prompt | Careful prompt | SelfCheck |
|---|---|---|---|
| Good questions (answerable, answer correct) | 12/22 (55%) | 20/24 (83%) | 22/24 (92%) |
| Questions or answers with a factual error | 6 | 0 | 0 |
| Real source sentence shown | 0% | 8% | 100% |
| Answer copied word for word from passage | 64% | 38% | 100% |
| Passage sections covered (of 3) | 2.0 | 2.4 | 2.4 |
| Key terms covered | 50% | 60% | 71% |
| Time per passage | about 24 s | about 28 s | about 40 s |

- Basic prompt errors: "red soil" where the passage says laterite; "becomes groundwater"; Ambedkar
  "chaired the Constituent Assembly" (passage: Drafting Committee); ultrasound "above 20 Hz";
  plus cut-off and incomplete answers.
- Careful prompt (told to answer only from the passage, copy answers, quote sources): wrote 3
  statements instead of questions and quoted a source for only 2 of 24. Instructions alone don't make
  a small model reliable.
- SelfCheck's 2 misses were wording, not facts: one question asked for two dates but gave one; one
  was grammatically broken ("What people do with their extra money...?"). The answer-back check
  caught the model inventing "The Bill of Rights" in a test run.
- Fill-in-the-blank fallbacks dropped from 12 to 2 of 24 after improving answer picking.

Honest limits: one labeller (confirm whether a person or an AI did it; if AI, say "AI-assisted blind
review"), about 24 questions per version. The gap to the basic prompt is large; the gap to the
careful prompt is 2 questions, so lean on zero factual errors, 100% sources and coverage rather
than the 9-point difference. One lenient label ("India" issues currency; the passage says the
Reserve Bank of India); strict scoring gives SelfCheck 21/24 (88%). English only; needs a student
who can read the passage; measures question quality and speed, not learning gains.

## Remaining
Must: rehearse with Wi-Fi off on the organisers' passage, record a backup video, build about 5
slides (problem, method, results table, limits), confirm how labelling was done, fill the
submission form with the GitHub link. Nice: block two-part questions and broken grammar, check the
UI in the Pi's own Chromium, printable study sheet. Before returning the Pi: rm ~/.ssh/authorized_keys
and sign out of everything. Credit "Built with Llama" (Llama 3.2 licence).
