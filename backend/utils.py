import re


def clean_ai_output(text):
    """Clean AI response text by removing prompt artifacts and normalizing whitespace."""
    if not text:
        return ""

    cleaned = text
    # Remove prompt artifacts
    cleaned = re.sub(r"(?i)\b(user question|question|rules|rule|preface|example|examples|constraints|behavior|answer)\s*:\s*", " ", cleaned)
    # Normalize multiple spaces to single space
    cleaned = re.sub(r" {2,}", " ", cleaned)
    return cleaned.strip()
