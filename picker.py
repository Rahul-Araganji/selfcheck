"""Plain-Python selection of key sentences and answer spans. No model involved."""
import re
from collections import Counter

STOP = set(
    """a an the of in on at to and or but nor so is are was were be been being am by for with
    as that this these those it its from has have had having not no which who whom whose what
    when where why how their his her they them he she we you your our us i me my do does did
    can could will would shall should may might must also than then there here into onto over
    under about after before during between through while because if each other such some any
    all most more many much very only same both own few""".split()
)

WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


def sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text)
    return [p.strip() for p in parts if len(p.split()) >= 6]


def content_words(s):
    return [w.lower() for w in WORD.findall(s) if w.lower() not in STOP and len(w) > 2]


MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DEFINED = re.compile(
    r"\b(?:called|known as|is named|termed)\s+(?:a |an |the )?([A-Za-z][A-Za-z-]*(?:\s[A-Z][A-Za-z-]*)?)"
)


MARKER = re.compile(r"\b(?:called|known as|termed|is named)\s+(?:the |a |an )?")
UNITS = (r"metres per second|times per minute|per cent|percent|%|hertz|km|kilometres|kg|metres|"
         r"million|billion|crore|lakh|years?|degrees")


def defined_terms(sentence):
    """Full term after 'called' / 'known as', e.g. 'double coincidence of wants'.

    Multi-word terms are kept only when they run up to punctuation; otherwise just the first word,
    so 'capillaries connect arteries' becomes 'capillaries'.
    """
    terms = []
    for m in MARKER.finditer(sentence):
        rest = sentence[m.end():]
        words = []
        ended_by_punct = False
        for tok in re.finditer(r"[A-Za-z][A-Za-z'-]*|[,.;:!?]", rest):
            w = tok.group()
            if w in ",.;:!?":
                ended_by_punct = True
                break
            if w.lower() in STOP and w.lower() != "of":
                break
            if len(words) == 4:  # a 5th word: too long to be a term
                break
            words.append(w)
        if words and words[-1].lower() == "of":
            words.pop()
        if words:
            terms.append(" ".join(words) if ended_by_punct else words[0])
    return terms


def candidate_answers(sentence, freq):
    """Return (answers, strong). Strong answers: defined terms, dates, numbers, names.

    Weak answers (rare single words) are used only when a passage has too few strong ones.
    Words that appear 3+ times in the passage are its topic, so they make poor answers.
    """
    def topical(a):
        ws = content_words(a)
        return bool(ws) and all(freq[w] >= 3 for w in ws)

    defined = defined_terms(sentence)
    found = list(defined)
    found += [m.group() for m in re.finditer(rf"\b\d{{1,2}}\s(?:{MONTHS})\s\d{{4}}\b", sentence)]
    for m in re.finditer(rf"\b\d[\d,.]*\s?(?:{UNITS})?", sentence):
        num = m.group().strip(" ,.")
        if not any(num in f for f in found):  # skip "26" when "26 November 1949" is already there
            found.append(num)
    tokens = list(WORD.finditer(sentence))
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.start() > 0 and tok.group()[0].isupper() and tok.group().lower() not in STOP:
            j = i
            while j + 1 < len(tokens) and tokens[j + 1].group()[0].isupper() \
                    and sentence[tokens[j].end():tokens[j + 1].start()] == " ":
                j += 1
            name = re.sub(r"'s$", "", sentence[tok.start():tokens[j].end()])
            if not any(name in f for f in found):
                found.append(name)
            i = j + 1
        else:
            i += 1
    def dedupe(items):
        seen, out = set(), []
        for a in items:
            key = a.lower()
            # A term the sentence explicitly defines ("called X") is a good answer even if it is the topic.
            if a and key not in seen and (a in defined or not topical(a)):
                seen.add(key)
                out.append(a)
        return out

    strong = dedupe(found)
    if strong:
        return strong, True
    # Weak fallback: rare nouns-ish words, skipping adverbs, verb forms and vague quantity words.
    vague = {"important", "several", "thousands", "different", "various", "major", "large", "small",
             "great", "important", "common", "certain", "whole", "often"}
    rare = sorted(
        {w for w in WORD.findall(sentence)
         if w.lower() not in STOP and w.lower() not in vague and len(w) >= 5
         and not re.search(r"(ly|ing|ed|es|s)$", w.lower())},
        key=lambda w: (freq[w.lower()], -len(w)),
    )
    return dedupe(rare[:2]), False


CAUSAL = re.compile(r"\b(because|due to|causes?|caused|leads? to|results? in|as a result|therefore|"
                    r"so that|depends on|important|used (?:to|in|for))\b", re.I)


def importance(s, freq):
    """How central a sentence is: shared key words, definitions, numbers, causes and effects."""
    ws = content_words(s)
    if not ws:
        return 0
    centrality = sum(freq[w] for w in ws) / len(ws)
    return (centrality + (2.0 if MARKER.search(s) else 0) + (1.5 if re.search(r"\d", s) else 0)
            + (1.0 if CAUSAL.search(s) else 0))


def pick(text, k=8):
    """Return up to k (sentence, [answers], strong) triples, ordered to cover the whole passage.

    Sentences are grouped into the beginning, middle and end of the passage. Picks rotate between
    the three parts, taking the most important sentence with a strong answer from each part first,
    so a 3-question quiz covers the whole passage instead of clustering in one place.
    """
    sents = sentences(text)
    freq = Counter(content_words(text))
    n = len(sents)
    buckets = [[], [], []]
    used = set()
    ranked = sorted(range(n), key=lambda i: importance(sents[i], freq), reverse=True)
    for i in ranked:
        answers, strong = candidate_answers(sents[i], freq)
        answers = [a for a in answers if a.lower() not in used]
        if answers:
            used.add(answers[0].lower())
            buckets[min(2, i * 3 // max(n, 1))].append((sents[i], answers, strong))
    for b in buckets:
        b.sort(key=lambda p: not p[2])  # strong answers first within each part, keeping importance order
    out = []
    while any(buckets) and len(out) < k:
        for b in buckets:
            if b:
                out.append(b.pop(0))
    # Weak answers go last overall, whatever their part.
    out.sort(key=lambda p: not p[2])
    return out[:k]


def section_of(sentence, text):
    """0, 1 or 2: beginning, middle or end of the passage."""
    sents = sentences(text)
    if sentence in sents:
        return min(2, sents.index(sentence) * 3 // max(len(sents), 1))
    return None


def key_terms(text, top=8):
    """The passage's key ideas: every defined term plus the most frequent content words."""
    freq = Counter(content_words(text))
    terms = []
    for s in sentences(text):
        terms += [t.lower() for t in defined_terms(s)]
    for w, _ in freq.most_common(top):
        if w not in terms:
            terms.append(w)
    return terms
