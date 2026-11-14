"""Automatic checks applied identically to every version's questions.

support(q, a, passage): is there ONE sentence in the passage that contains the answer's key words
    and most of the question's key words? Catches invented facts and mix-ups between sentences
    (e.g. answering 'red soil' to a question about heavy rainfall, which describes laterite).
    It is a proxy: it can pass a wrong question and fail a fine paraphrase, so human labels decide.
traceable(item, passage): does the item show a source sentence that really is in the passage?
coverage(items, passage): share of the passage's three sections and key terms the quiz touches.
"""
import re

import picker


def terms(text):
    nums = {n.strip(",.") for n in re.findall(r"\d[\d,.]*", text)}
    return set(picker.content_words(text)) | nums


def stem(w):
    return re.sub(r"(ies|es|s|ing|ed)$", "", w) if len(w) > 4 else w


def support(question, answer, passage):
    a = {stem(w) for w in terms(answer)}
    q = {stem(w) for w in terms(question)} - a
    if not a:
        return False
    for s in picker.sentences(passage):
        st = {stem(w) for w in terms(s)}
        if a <= st and (not q or len(q & st) / len(q) >= 0.5):
            return True
    return False


def norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


def verbatim(answer, passage):
    """Does the answer appear word for word in the passage? (The careful prompt was told to do this.)"""
    a = norm(answer)
    return bool(a) and a in norm(passage)


def traceable(item, passage):
    src = item.get("source", "")
    return bool(src) and norm(src) in norm(passage)


def coverage(items, passage):
    sections = set()
    touched = " ".join(f"{it['question']} {it['answer']} {it.get('source', '')}" for it in items).lower()
    for it in items:
        # Locate each question by its best-matching sentence in the passage.
        best, best_score = None, 0
        qa = terms(f"{it['question']} {it['answer']}")
        for s in picker.sentences(passage):
            score = len(qa & terms(s))
            if score > best_score:
                best, best_score = s, score
        if best:
            sections.add(picker.section_of(best, passage))
    keys = picker.key_terms(passage)
    hit = [k for k in keys if k in touched]
    return {"sections_covered": len(sections), "key_terms_covered": len(hit), "key_terms_total": len(keys)}
