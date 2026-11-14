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


def candidate_answers(sentence, freq):
    """Answer spans in priority order: defined terms, dates, numbers, names, then rare words.

    Words that appear 3+ times in the passage are its topic, so they make poor answers.
    """
    def topical(a):
        ws = content_words(a)
        return bool(ws) and all(freq[w] >= 3 for w in ws)

    defined = [m.group(1) for m in DEFINED.finditer(sentence)]
    found = list(defined)
    found += [m.group() for m in re.finditer(rf"\b\d{{1,2}}\s(?:{MONTHS})\s\d{{4}}\b", sentence)]
    for m in re.finditer(
        r"\b\d[\d,.]*\s?(?:%|percent|per cent|km|kilometres|kg|metres|million|billion|crore|lakh|years?|degrees)?",
        sentence,
    ):
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
    # Last resort: rare content words, skipping adverbs and verb forms that make poor answers.
    rare = sorted(
        {w for w in WORD.findall(sentence)
         if w.lower() not in STOP and len(w) >= 5 and not re.search(r"(ly|ing|ed|es)$", w.lower())},
        key=lambda w: (freq[w.lower()], -len(w)),
    )
    found.extend(rare[:3])
    seen, out = set(), []
    for a in found:
        key = a.lower()
        # A term the sentence explicitly defines ("called X") is a good answer even if it is the topic.
        if a and key not in seen and (a in defined or not topical(a)):
            seen.add(key)
            out.append(a)
    return out


def pick(text, k=5):
    """Return up to k (sentence, [answer candidates]) pairs, best sentences first."""
    sents = sentences(text)
    freq = Counter(content_words(text))

    def score(s):
        ws = content_words(s)
        if not ws:
            return 0
        has_number = 1.5 if re.search(r"\d", s) else 0
        defines = 2.0 if DEFINED.search(s) else 0
        return sum(freq[w] for w in ws) / len(ws) + has_number + defines

    ranked = sorted(sents, key=score, reverse=True)
    out, used = [], set()
    for s in ranked:
        answers = [a for a in candidate_answers(s, freq) if a.lower() not in used]
        if answers:
            out.append((s, answers))
            used.add(answers[0].lower())
        if len(out) == k:
            break
    # Keep passage order so the quiz follows the text.
    order = {s: i for i, s in enumerate(sents)}
    return sorted(out, key=lambda p: order[p[0]])
