from __future__ import annotations

from farkad_ai.prompts import prompt

PHOTO = prompt("photo")


def photo_briefing(language: str) -> str:
    """How to read a photo as a log, answered in `language`, a language's name in English."""
    return PHOTO.format(language=language)
