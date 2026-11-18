from __future__ import annotations

import unicodedata


def words(said: str) -> list[str]:
    kept = (
        " " if unicodedata.category(c)[0] in "PSZ" else c
        for c in unicodedata.normalize("NFKC", said).casefold()
        if unicodedata.category(c) != "Mn"
    )
    return "".join(kept).split()


def word_errors(reference: str, heard: str) -> int:
    wanted_words, heard_words = words(reference), words(heard)
    previous = list(range(len(heard_words) + 1))
    for row, wanted in enumerate(wanted_words, start=1):
        current = [row]
        for column, found in enumerate(heard_words, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (wanted != found),
                )
            )
        previous = current
    return previous[-1]
