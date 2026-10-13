import re
from app.parsing.extractor import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt
)
from app.parsing.normalizer import normalize_text

EMAIL_REGEX = r"\b[\w\.-]+@[\w\.-]+\.\w+\b"
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}\b"
)
URL_REGEX = r"(https?://\S+|www\.\S+)"
LINKEDIN_REGEX = r"(?:https?://)?(?:www\.)?linkedin\.com/\S+|\blinkedin\s*:\s*\S+"
ADDRESS_REGEX = r"\b\d{1,5}\s+\w+(?:\s+\w+){0,4}\s+(Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Drive|Dr\.?|Lane|Ln\.?|Boulevard|Blvd\.?)\b\.?"
CONTACT_LINE_REGEX = re.compile(
    r"^\s*(e-?mail|phone|mobile|cell|tel(?:ephone)?|address|linkedin|website|portfolio)\s*[:|].*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def _strip_phones(text: str) -> str:
    def replacer(match: re.Match) -> str:
        raw = match.group(0)
        # Dates use slashes or a four-digit year. Leave those in place.
        if "/" in raw or re.search(r"\b(?:19|20)\d{2}\b", raw):
            return raw
        return ""

    return PHONE_REGEX.sub(replacer, text)


def remove_contact_info(text: str) -> str:
    if not text:
        return ""
    text = CONTACT_LINE_REGEX.sub("", text)
    text = re.sub(EMAIL_REGEX, "", text)
    text = re.sub(URL_REGEX, "", text)
    text = re.sub(LINKEDIN_REGEX, "", text, flags=re.IGNORECASE)
    text = _strip_phones(text)
    text = re.sub(ADDRESS_REGEX, "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:e-?mail|phone|mobile|cell|linkedin|website)\s*[:.]?\s*(?=\.|$|,)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+([,.;!?])", r"\1", text)
    text = re.sub(r"([.!?])(?:\s*[.])+", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def parse_resume(file_name: str, data: bytes) -> str:
    extension = file_name.lower().split(".")[-1]

    if extension == "pdf":
        text = extract_text_from_pdf(data)
    elif extension == "docx":
        text = extract_text_from_docx(data)
    elif extension == "txt":
        text = extract_text_from_txt(data)
    else:
        raise ValueError("Unsupported file type")

    text = normalize_text(text)
    text = remove_contact_info(text)

    return text.strip()
