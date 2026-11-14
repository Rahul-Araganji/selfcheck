"""Thin wrapper around the ExecuTorch LLM runner, with timing and memory stats."""
import contextlib
import ctypes
import os
import resource
import sys
import time

_libc = ctypes.CDLL(None)


@contextlib.contextmanager
def native_stdout_silenced():
    """The C++ runner prints raw tokens and stats to stdout; hide them during generation."""
    sys.stdout.flush()
    saved = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    try:
        yield
    finally:
        _libc.fflush(None)
        os.dup2(saved, 1)
        os.close(devnull)
        os.close(saved)

# These imports register the custom and quantized kernels the .pte needs.
from executorch.extension.llm.custom_ops import custom_ops  # noqa: F401
from executorch.kernels import quantized  # noqa: F401
from executorch.extension.llm.runner import GenerationConfig, TextLLMRunner


def peak_rss_mb():
    # ru_maxrss is in KB on Linux.
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)


class LLM:
    def __init__(self, pte_path, tokenizer_path):
        self.pte_path = pte_path
        t0 = time.perf_counter()
        self.runner = TextLLMRunner(pte_path, tokenizer_path)
        self.load_s = round(time.perf_counter() - t0, 2)
        self.calls = []

    @property
    def model_mb(self):
        return round(os.path.getsize(self.pte_path) / 1e6)

    def generate(self, prompt, max_new_tokens=40):
        pieces, stats = [], {}

        def on_stats(s):
            stats["prompt_tokens"] = getattr(s, "num_prompt_tokens", None)
            stats["gen_tokens"] = getattr(s, "num_generated_tokens", None)
            start = getattr(s, "prompt_eval_end_ms", None)
            end = getattr(s, "inference_end_ms", None)
            if start is not None and end is not None:
                stats["decode_ms"] = end - start
            ls, le = getattr(s, "model_load_start_ms", None), getattr(s, "model_load_end_ms", None)
            if ls and le and le > ls:
                stats["load_ms"] = le - ls

        cfg = GenerationConfig(echo=False, max_new_tokens=max_new_tokens, temperature=0.0)
        self.runner.reset()  # independent prompts: clear the KV cache
        t0 = time.perf_counter()
        with native_stdout_silenced():
            self.runner.generate(prompt, cfg, pieces.append, on_stats)
        wall = time.perf_counter() - t0

        text = "".join(pieces)
        if stats.get("load_ms") and not self.calls:
            # The runner loads the model lazily, during the first generate() call.
            self.load_s = round(stats["load_ms"] / 1000, 2)
            wall -= self.load_s
        gen = stats.get("gen_tokens") or len(pieces)
        decode_s = (stats.get("decode_ms") or wall * 1000) / 1000
        call = {
            "wall_s": round(wall, 2),
            "prompt_tokens": stats.get("prompt_tokens"),
            "gen_tokens": gen,
            "tok_per_s": round(gen / decode_s, 2) if decode_s > 0 else None,
        }
        self.calls.append(call)
        return clean(text), call

    def totals(self):
        gen = sum(c["gen_tokens"] or 0 for c in self.calls)
        wall = sum(c["wall_s"] for c in self.calls)
        rates = [c["tok_per_s"] for c in self.calls if c["tok_per_s"]]
        return {
            "model_file": os.path.basename(self.pte_path),
            "model_mb": self.model_mb,
            "model_load_s": self.load_s,
            "llm_calls": len(self.calls),
            "generated_tokens": gen,
            "generation_wall_s": round(wall, 2),
            "mean_decode_tok_per_s": round(sum(rates) / len(rates), 2) if rates else None,
            "peak_rss_mb": peak_rss_mb(),
        }


def clean(text):
    """Drop special tokens and anything after the first end-of-turn marker."""
    cut = text.find("<|")
    if cut != -1:
        text = text[:cut]
    return text.strip()
