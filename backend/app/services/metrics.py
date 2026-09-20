import re
from dataclasses import dataclass


@dataclass
class TextMetrics:
    clarity: int
    readability: int
    formality: int
    avg_sentence_length: float
    word_count: int


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?…]+\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"[\w']+", text, flags=re.UNICODE)


def compute_metrics(text: str) -> TextMetrics:
    words = _words(text)
    sents = _sentences(text)
    wc = len(words)
    sc = max(len(sents), 1)
    avg_len = wc / sc if wc else 0.0

    long_words = sum(1 for w in words if len(w) > 6)
    long_ratio = long_words / wc if wc else 0

    readability = int(max(0, min(100, 100 - avg_len * 2.5 - long_ratio * 40)))

    formal_markers = len(
        re.findall(
            r"\b(therefore|however|furthermore|thus|shall|hereby|данный|следовательно|однако)\b",
            text,
            re.I,
        )
    )
    formality = int(max(0, min(100, 35 + formal_markers * 8 + long_ratio * 30)))

    clarity = int(max(0, min(100, readability * 0.6 + (100 - min(avg_len, 40) * 2) * 0.4)))

    return TextMetrics(
        clarity=clarity,
        readability=readability,
        formality=formality,
        avg_sentence_length=round(avg_len, 1),
        word_count=wc,
    )
