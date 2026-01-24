"""Text normalization utilities for consistent cache keying."""

import re


def normalize_text(text: str) -> str:
    """
    Normalize Japanese text for consistent cache keying.

    Rules:
    - Trim leading and trailing whitespace
    - Collapse runs of whitespace (spaces, tabs, newlines) to single spaces
    - Join multi-line text with single spaces
    - Preserve Japanese characters, punctuation, and emoji as-is
    - Case-sensitive (Japanese has no case)

    Args:
        text: Original text to normalize.

    Returns:
        Normalized text string.
    """
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text
