import re
from app.parsing.extractor import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt
)
from app.parsing.normalizer import normalize_text

EMAIL_REGEX = r"\b[\w\.-]+@[\w\.-]+\.\w+\b"
PHONE_REGEX = r"(\+?\d{1,3})?[\s.-]?\(?\d{2,3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
URL_REGEX = r"(https?://\S+|www\.\S+)"
LINKEDIN_REGEX = r"\b(?:linkedin\.com/in/|linkedin:?)\S*\b"
ADDRESS_REGEX = r"\b\d{1,5}\s+\w+(?:\s+\w+){0,4}\s+(Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b\.?"

def remove_contact_info(text: str) -> str:
    text = re.sub(EMAIL_REGEX, "", text)
    text = re.sub(URL_REGEX, "", text)
    text = re.sub(LINKEDIN_REGEX, "", text, flags=re.IGNORECASE)
    return text

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
