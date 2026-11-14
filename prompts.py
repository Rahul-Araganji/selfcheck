"""Llama 3.2 chat-format prompts."""

H = "<|start_header_id|>{role}<|end_header_id|>\n\n{text}<|eot_id|>"


def chat(system, turns):
    """turns: list of (role, text); the prompt ends ready for the assistant to reply."""
    out = "<|begin_of_text|>" + H.format(role="system", text=system)
    for role, text in turns:
        out += H.format(role=role, text=text)
    return out + "<|start_header_id|>assistant<|end_header_id|>\n\n"


def question(sentence, answer):
    return chat(
        "You write one quiz question for a school student. The question must be answerable "
        "from the sentence, and its answer must be exactly the given answer. Do not include "
        "the answer in the question. Output only the question on one line.",
        [
            ("user", "Sentence: Stomata are tiny pores on the leaf surface through which gases are exchanged.\nAnswer: Stomata"),
            ("assistant", "What are the tiny pores on a leaf surface through which gases are exchanged called?"),
            ("user", f"Sentence: {sentence}\nAnswer: {answer}"),
        ],
    )


def answer_back(sentence, q):
    """Ask the model to answer its own question from the sentence, for verification."""
    return chat(
        "Answer the question using only the sentence. Reply with the shortest possible answer "
        "phrase, copied from the sentence. No full sentences.",
        [
            ("user", "Sentence: Stomata are tiny pores on the leaf surface through which gases are exchanged.\n"
                     "Question: What are the tiny pores on a leaf surface called?"),
            ("assistant", "Stomata"),
            ("user", f"Sentence: {sentence}\nQuestion: {q}"),
        ],
    )


def summary(passage):
    return chat(
        "Summarise the passage for a Class 9 student in two or three short, simple sentences. "
        "Use only facts from the passage. Output only the summary.",
        [("user", passage)],
    )


def baseline(passage):
    """One-prompt baseline: what most teams will do. Used for comparison only."""
    return chat(
        "You help a Class 9 student revise. Write a short summary of the passage, then three "
        "quiz questions with their answers. Use this format:\nSummary: ...\nQ1: ...\nA1: ...\n"
        "Q2: ...\nA2: ...\nQ3: ...\nA3: ...",
        [("user", passage)],
    )
