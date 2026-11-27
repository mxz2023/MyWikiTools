from __future__ import annotations


def card_safe_summary(text: str) -> str:
    """Strip control characters so card JSON templates survive json.loads."""
    return " ".join(text.split())


def card_safe_md(text: str) -> str:
    """Keep newlines for lists; strip chars that break card JSON rendering."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(lines)