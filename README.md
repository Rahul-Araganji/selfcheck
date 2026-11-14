# SelfCheck - Don't just read it. Check if you understood it.

An offline study aid that helps Class 9-10 students check whether they understood what they read.
It turns a 150-300 word passage into checked quiz questions and a short summary, running fully
on a Raspberry Pi 5 with ExecuTorch. No internet, login or student data.

Namma AI Hackathon 2026, Problem Statement 1: AI for Inclusive Education.

## Why
A student studying alone can't tell whether they understood a passage, and small AI models often
write quiz questions the passage cannot answer. SelfCheck reverses the usual approach:

1. Plain code picks a key sentence and an answer from the passage.
2. The model writes a question for that answer.
3. Code rejects questions that give the answer away, drift off topic or don't end in "?".
4. The model answers its own question from the sentence; the question is kept only if that
   answer matches the chosen one. Otherwise it retries, then falls back to fill-in-the-blank.
5. The student attempts each question first, then sees the answer and its source sentence.
6. A short summary comes after the quiz.

## Hardware and model
- Raspberry Pi 5 (8 GB), Raspberry Pi OS 64-bit (Debian 13), Python 3.13
- ExecuTorch 1.6.0 (XNNPACK backend), PyTorch 2.15.0 CPU
- Llama 3.2 1B Instruct, SpinQuant INT4, `.pte` from
  [software-mansion/Llama-3.2-ExecuTorch](https://huggingface.co/software-mansion/Llama-3.2-ExecuTorch)

## Setup (on the Pi, once, online)
```bash
python3 -m venv ~/selfcheck-env
bash setup/install_cpu.sh
bash setup/get_models.sh
```

## Run (offline)
```bash
source ~/selfcheck-env/bin/activate
python selfcheck.py passages/sample1.txt --interactive 2>/dev/null   # student mode
python selfcheck.py passages/sample1.txt 2>/dev/null                 # print everything
python selfcheck.py passages/sample1.txt --mode baseline 2>/dev/null # one-prompt baseline
python score.py                                                      # after labelling results/labels.csv
```

## Web UI (offline, on the Pi)
```bash
source ~/selfcheck-env/bin/activate && pip install flask
python app.py        # then open http://localhost:5000 on the Pi, or http://<pi-ip>:5000 from a laptop
```
Screens: home, choose a passage, reading (questions are prepared on the Pi while the student
reads), assessment one question at a time with a session timer, evidence reveal with the
highlighted source sentence, and results with the summary and real on-device metrics.
The UI reuses `run_selfcheck()` unchanged; answers stay on the Pi until the student submits.

## Results (Raspberry Pi 5, 8 practice passages, same model for all three versions)
Three ways of making a quiz from the same passage: a basic one-line prompt, a careful prompt with
explicit grounding rules ("answer only from the passage, copy the answer, quote the sentence"), and
SelfCheck. All 70 questions were shuffled and labelled blind, without knowing which version wrote them.

| Measure | Basic prompt | Careful prompt | SelfCheck |
|---|---|---|---|
| Good questions (answerable from the passage, answer correct) | 12/22 (55%) | 20/24 (83%) | **22/24 (92%)** |
| Questions or answers with a factual error | 6 | 0 | **0** |
| Real source sentence shown | 0% | 8% | **100%** |
| Answer copied word for word from the passage | 64% | 38% | **100%** |
| Key terms of the passage covered | 50% | 60% | **71%** |
| Time per passage | about 24 s | about 28 s | about 40 s |

- The careful prompt was told to quote its source but did so for 2 of 24 questions, and wrote 3
  statements instead of questions: instructions alone don't make a small model reliable.
- SelfCheck's 2 misses were wording problems (a question asking for two dates, and a grammatically
  broken question), not wrong facts.
- Limits: one labeller, about 24 questions per version. The gap to the basic prompt is large;
  the gap to the careful prompt is 2 questions and should not be over-read.

On-device: 1,082 MB model, about 11-12 tokens/s, about 2.6 GB peak memory. This PoC measures
question quality and speed, not learning gains.

Run outputs, the blind sheet (`results/label_sheet.csv`), the labelled sheet
(`results/label_sheet_evaluated.csv`) and the key (`results/label_key.csv`) are in `results/`.

## Files
| File | Role |
|---|---|
| `selfcheck.py` | Main program: pipeline, checks, output, metrics |
| `picker.py` | Sentence and answer selection (no AI) |
| `prompts.py` | Llama 3.2 prompts |
| `llm.py` | ExecuTorch runner wrapper with timing and memory stats |
| `score.py` | Answerable-question rate from human labels |
| `smoke_test.py` | Quick model test |
| `passages/` | Practice passages written by the team |

**SelfCheck flips the way AI-generated quizzes work: instead of generating questions and hoping their answers are correct, it selects evidence-backed answers first, generates questions around them, and verifies each question against the original passage — entirely offline on a Raspberry Pi 5.**

## Limits
- English only; needs a student who can already read the passage.
- Checks reduce bad questions but cannot guarantee good ones.

Built with Llama.
