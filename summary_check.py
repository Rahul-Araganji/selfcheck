"""Checked summary: every sentence shown must be backed by the passage.

1. The model writes a short summary (one fact per sentence, in the passage's words).
2. Each summary sentence is kept only if:
   - ALL of its key words appear in ONE passage sentence, apart from a few harmless general words
     ("different", "main", ...). One wrong word is enough to drop it, e.g. "red soil ... heavy
     rainfall" when the passage says red soil forms with LOW rainfall,
   - every number in it appears in the passage,
   - it doesn't add or drop a "not / no / never" compared with that passage sentence.
3. If fewer than 2 sentences survive, the summary is built from the passage's own most important
   sentences instead (extractive), so nothing unsupported is ever shown.

   - it doesn't skip any key word from the middle of that passage sentence (skipping can change
     who did what).

Limits: word overlap can't understand meaning perfectly. A correct but reworded sentence is often
dropped (the safe side), and an unusual rewording could in principle still pass.
"""
import re

import picker

NEGATIONS = {"not", "no", "never", "cannot", "can't", "isn't", "doesn't", "don't", "none", "neither", "nor"}
# Words a summary may add without changing any fact.
GENERIC = {"different", "various", "many", "several", "important", "main", "key", "type", "kind",
           "part", "way", "help", "include", "called", "known", "process", "also", "overall", "major"}


def _stem(w):
    return re.sub(r"(ies|es|s|ing|ed)$", "", w) if len(w) > 4 else w


def _terms(text):
    return {_stem(w) for w in picker.content_words(text)}


def _numbers(text):
    return {n.strip(",.") for n in re.findall(r"\d[\d,.]*", text)}


def _negations(text):
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w in NEGATIONS}


def split_sentences(text):
    return picker.sentences(text, min_words=4)


def _skipped_in_middle(sentence_terms, src):
    """How many of the passage sentence's key words the summary skips between its first and last match.

    Skipping words in the middle can change who did what ("drafted by a Constituent Assembly and
    [the Drafting Committee was] chaired by Ambedkar"), so more than one skip is rejected.
    """
    src_terms = [_stem(w) for w in picker.content_words(src)]
    hits = [i for i, w in enumerate(src_terms) if w in sentence_terms]
    if not hits:
        return 0
    middle = src_terms[min(hits):max(hits) + 1]
    return len([w for w in middle if w not in sentence_terms])


def check_sentence(sentence, passage):
    """Return (ok, reason, best_coverage)."""
    words = _terms(sentence)
    if not words:
        return False, "no content", 0.0
    if not _numbers(sentence) <= _numbers(passage):
        return False, "number not in passage", 0.0
    generic = {_stem(w) for w in GENERIC}
    best, best_src, best_missing = 0.0, None, words
    for src in picker.sentences(passage):
        missing = words - _terms(src) - generic
        cov = 1 - len(missing) / len(words)
        if cov > best:
            best, best_src, best_missing = cov, src, missing
    if best_missing:
        return False, f"not in any one passage sentence: {', '.join(sorted(best_missing))}", best
    if _skipped_in_middle(words, best_src) > 0:
        return False, "leaves out words from the middle of the passage sentence (meaning may change)", best
    if bool(_negations(sentence)) != bool(_negations(best_src)):
        return False, "negation differs from the passage", best
    return True, "backed by the passage", best


DANGLING = re.compile(r"^(it|its|this|these|those|they|their|such|he|she|however|also|then)\b", re.I)


def extractive(passage, k=3):
    """The passage's own key sentences, in reading order, chosen to read well on their own.

    Always starts with the passage's opening sentence (it states the topic), skips sentences that
    begin with words like "These" or "It" (they don't make sense alone), and takes the remaining
    sentences from different parts of the passage.
    """
    from collections import Counter
    sents = picker.sentences(passage)
    if not sents:
        return passage.strip()
    freq = Counter(picker.content_words(passage))
    chosen = [0]
    n = len(sents)
    for part in ((n // 3, 2 * n // 3), (2 * n // 3, n)):  # middle, then end
        if len(chosen) == k:
            break
        cands = [i for i in range(max(1, part[0]), part[1]) if not DANGLING.match(sents[i])]
        if cands:
            chosen.append(max(cands, key=lambda i: picker.importance(sents[i], freq)))
    return " ".join(sents[i] for i in sorted(set(chosen)))


def checked_summary(model_summary, passage):
    """Return (summary_text, info) where info explains what was kept or dropped."""
    kept, dropped = [], []
    for s in split_sentences(model_summary):
        ok, reason, cov = check_sentence(s, passage)
        (kept if ok else dropped).append({"sentence": s, "reason": reason, "coverage": round(cov, 2)})
    if len(kept) >= 2:
        return " ".join(k["sentence"] for k in kept), {"source": "checked", "kept": kept, "dropped": dropped}
    return extractive(passage), {"source": "passage", "kept": [], "dropped": dropped}
