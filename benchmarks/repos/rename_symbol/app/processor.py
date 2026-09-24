"""Text processing helpers."""


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split()).lower()
