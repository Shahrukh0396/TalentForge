import re

def normalize_text(text: str) -> str:
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize bullets
    text = text.replace("•", "-").replace("●", "-")

    # Trim whitespace on each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text