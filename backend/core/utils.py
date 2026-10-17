import re


def clean_ai_output(text):
    """Clean AI response text by removing prompt artifacts and normalizing whitespace."""
    if not text:
        return ""

    cleaned = text

    # Remove markdown headers ### Header
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)

    # Remove **bold** and any trailing punctuation/colons
    cleaned = re.sub(r"\*\*([^*:]+)\*\*[:.]?", r"\1", cleaned)

    # Remove [auto] and similar model-generated suffixes
    cleaned = re.sub(r"\s*\[auto\]\s*$", "", cleaned, flags=re.IGNORECASE)

    # Remove "AI:" prefix
    cleaned = re.sub(r"(?i)^AI:\s*", "", cleaned)

    # Remove ParagraphN: artifacts
    cleaned = re.sub(r"(?i)^Paragraph\s*\d+:\s*", "", cleaned, flags=re.MULTILINE)

    # Remove "Recent conversation:" and "Conversation history:" labels
    cleaned = re.sub(r"(?i)^Recent conversation:\s*", "", cleaned)
    cleaned = re.sub(r"(?i)^Conversation history:\s*", "", cleaned)

    # Remove echoed instruction/system tags
    cleaned = re.sub(r"(?i)</?system[_ ]instructions>\s*", "", cleaned)

    # Remove CamelCase instruction fragments
    cleaned = re.sub(r"(?i)^[A-Z][a-z]+(?:[A-Z][a-z]+)+\s*", "", cleaned, flags=re.MULTILINE)

    # Remove echoed "You:" or "AI:" labels
    cleaned = re.sub(r"(?i)^(You|AI)\s*:\s*", "", cleaned, flags=re.MULTILINE)

    # Remove prompt artifacts
    cleaned = re.sub(r"(?i)\b(user question|question|rules|rule|preface|example|examples|constraints|behavior|answer)\s*:\s*", " ", cleaned)

    # Normalize multiple spaces between words to single space (preserves indentation)
    cleaned = re.sub(r"(\S) {2,}(\S)", r"\1 \2", cleaned)

    return cleaned.strip()
