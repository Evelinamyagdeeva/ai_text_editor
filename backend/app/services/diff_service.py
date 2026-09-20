import difflib
from dataclasses import dataclass


@dataclass
class DiffChunk:
    kind: str  # equal, insert, delete
    text: str


def word_diff(old: str, new: str) -> list[DiffChunk]:
    old_words = old.split()
    new_words = new.split()
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    chunks: list[DiffChunk] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            text = " ".join(old_words[i1:i2])
            if text:
                chunks.append(DiffChunk("equal", text + " "))
        elif tag == "delete":
            text = " ".join(old_words[i1:i2])
            if text:
                chunks.append(DiffChunk("delete", text + " "))
        elif tag == "insert":
            text = " ".join(new_words[j1:j2])
            if text:
                chunks.append(DiffChunk("insert", text + " "))
        elif tag == "replace":
            old_t = " ".join(old_words[i1:i2])
            new_t = " ".join(new_words[j1:j2])
            if old_t:
                chunks.append(DiffChunk("delete", old_t + " "))
            if new_t:
                chunks.append(DiffChunk("insert", new_t + " "))
    return chunks
