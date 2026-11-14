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

## Results so far (Raspberry Pi 5, 3 practice passages)
| Measure | Result |
|---|---|
| Model size | 1,082 MB |
| Decode speed | about 11 tokens/s |
| Prompt processing | about 100-110 tokens/s |
| Peak memory | about 2.6 GB |
| Time per passage (3 questions + summary) | about 24-33 s |

- One-prompt baseline: 2 of 9 answers were wrong or not supported by the passage.
- SelfCheck: no answer mismatches observed; the answer-back check caught the model inventing
  "The Bill of Rights". 3 of 9 questions fell back to fill-in-the-blank.
- Small sample, not yet human-labelled. This PoC measures question quality and speed, not
  learning gains.

Run outputs, the blind labelling sheet (`results/label_sheet.csv`) and its key are in `results/`.

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
