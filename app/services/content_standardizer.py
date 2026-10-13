"""Deterministic Syntax Talent cleanup applied after the model returns JSON.

The model is asked to fix grammar, tense, and spelling. This module enforces the
rules that can be checked without guessing: contact removal, date and location
shape, software names, common misspellings, bullet punctuation, and tense on
the first verb of each bullet.
"""

from __future__ import annotations

import re

from app.parsing.parser import remove_contact_info

SOFTWARE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bquick\s*books\b", "QuickBooks"),
    (r"\bpeople\s*soft\b", "PeopleSoft"),
    (r"\bpower\s*point\b", "PowerPoint"),
    (r"\bsales\s*force\b", "Salesforce"),
    (r"\bmicro\s*strategy\b", "MicroStrategy"),
)

# Common resume misspellings. Proper nouns are handled by SOFTWARE_PATTERNS.
SPELLING: dict[str, str] = {
    "recieve": "receive",
    "recieved": "received",
    "seperate": "separate",
    "seperately": "separately",
    "managment": "management",
    "enviroment": "environment",
    "experiance": "experience",
    "responsiblities": "responsibilities",
    "responsibilites": "responsibilities",
    "acheived": "achieved",
    "acheive": "achieve",
    "occured": "occurred",
    "occuring": "occurring",
    "sucessful": "successful",
    "sucessfully": "successfully",
    "liason": "liaison",
    "goverment": "government",
    "accomodate": "accommodate",
    "definately": "definitely",
    "untill": "until",
    "commited": "committed",
    "refered": "referred",
    "independant": "independent",
    "maintainance": "maintenance",
    "teh": "the",
    "adn": "and",
    "wich": "which",
}

# base, third-person present, simple past
VERBS: tuple[tuple[str, str, str], ...] = (
    ("lead", "leads", "led"),
    ("manage", "manages", "managed"),
    ("develop", "develops", "developed"),
    ("create", "creates", "created"),
    ("design", "designs", "designed"),
    ("implement", "implements", "implemented"),
    ("support", "supports", "supported"),
    ("coordinate", "coordinates", "coordinated"),
    ("analyze", "analyzes", "analyzed"),
    ("maintain", "maintains", "maintained"),
    ("oversee", "oversees", "oversaw"),
    ("direct", "directs", "directed"),
    ("build", "builds", "built"),
    ("provide", "provides", "provided"),
    ("assist", "assists", "assisted"),
    ("conduct", "conducts", "conducted"),
    ("prepare", "prepares", "prepared"),
    ("review", "reviews", "reviewed"),
    ("train", "trains", "trained"),
    ("mentor", "mentors", "mentored"),
    ("supervise", "supervises", "supervised"),
    ("execute", "executes", "executed"),
    ("deliver", "delivers", "delivered"),
    ("improve", "improves", "improved"),
    ("establish", "establishes", "established"),
    ("collaborate", "collaborates", "collaborated"),
    ("negotiate", "negotiates", "negotiated"),
    ("research", "researches", "researched"),
    ("monitor", "monitors", "monitored"),
    ("report", "reports", "reported"),
    ("present", "presents", "presented"),
    ("facilitate", "facilitates", "facilitated"),
    ("drive", "drives", "drove"),
    ("spearhead", "spearheads", "spearheaded"),
    ("achieve", "achieves", "achieved"),
    ("reduce", "reduces", "reduced"),
    ("increase", "increases", "increased"),
    ("launch", "launches", "launched"),
    ("migrate", "migrates", "migrated"),
    ("automate", "automates", "automated"),
    ("configure", "configures", "configured"),
    ("administer", "administers", "administered"),
    ("resolve", "resolves", "resolved"),
    ("document", "documents", "documented"),
    ("evaluate", "evaluates", "evaluated"),
    ("identify", "identifies", "identified"),
    ("ensure", "ensures", "ensured"),
    ("handle", "handles", "handled"),
    ("perform", "performs", "performed"),
    ("process", "processes", "processed"),
    ("generate", "generates", "generated"),
    ("produce", "produces", "produced"),
    ("serve", "serves", "served"),
    ("advise", "advises", "advised"),
    ("counsel", "counsels", "counseled"),
    ("represent", "represents", "represented"),
    ("litigate", "litigates", "litigated"),
    ("draft", "drafts", "drafted"),
    ("file", "files", "filed"),
    ("argue", "argues", "argued"),
)

MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}

PRESENT_WORDS = {"present", "current", "now", "ongoing", "today"}

STATE_NAMES = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

STATE_ABBRS = set(STATE_NAMES.values())

LIST_FIELDS = (
    "core_competencies",
    "professional_experience",
    "education",
    "technical_skills",
    "certifications",
    "additional_information",
    "volunteer_experience",
    "extracurricular_activities",
    "bar_licenses",
)


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _match_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def apply_language_fixes(text: str) -> str:
    cleaned = remove_contact_info(text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()

    def software_sub(canonical: str):
        def replacer(match: re.Match) -> str:
            return _match_case(match.group(0), canonical)

        return replacer

    for pattern, canonical in SOFTWARE_PATTERNS:
        cleaned = re.sub(pattern, software_sub(canonical), cleaned, flags=re.IGNORECASE)

    for wrong, right in SPELLING.items():
        cleaned = re.sub(
            rf"\b{re.escape(wrong)}\b",
            lambda match, replacement=right: _match_case(match.group(0), replacement),
            cleaned,
            flags=re.IGNORECASE,
        )
    return cleaned.strip()


def _normalize_date_part(token: str) -> str:
    token = token.strip().strip(".")
    if not token:
        return ""
    if token.lower() in PRESENT_WORDS:
        return "Present"
    month_year = re.fullmatch(r"(\d{1,2})[\/\-.](\d{4})", token)
    if month_year:
        month = int(month_year.group(1))
        if 1 <= month <= 12:
            return f"{month:02d}/{month_year.group(2)}"
    named = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{4})", token)
    if named and named.group(1).lower() in MONTHS:
        return f"{MONTHS[named.group(1).lower()]}/{named.group(2)}"
    year_only = re.fullmatch(r"(\d{4})", token)
    if year_only:
        return year_only.group(1)
    return token


def normalize_dates(value: str) -> str:
    text = re.sub(r"\s+", " ", _text(value))
    if not text:
        return ""
    parts = re.split(r"\s*(?:–|—|-|to)\s*", text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 1:
        return _normalize_date_part(parts[0])
    left = _normalize_date_part(parts[0])
    right = _normalize_date_part(parts[1])
    if left and right:
        return f"{left} – {right}"
    return left or right


def is_current_role(dates: str) -> bool | None:
    if not _text(dates):
        return None
    return "present" in dates.lower()


def _city_case(city: str) -> str:
    city = city.strip(" ,")
    if city.isupper() or city.islower():
        return city.title()
    return city


def normalize_location(value: str) -> str:
    text = re.sub(r"\s+", " ", _text(value)).strip(" ,")
    if not text:
        return ""
    if text.lower() in {"remote", "hybrid", "nationwide", "multiple locations", "various"}:
        return text.title()

    text = re.sub(r"\bD\.?\s*C\.?\b", "DC", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{5}(?:-\d{4})?\b", "", text).strip(" ,")

    lowered = text.lower()
    for name, abbr in sorted(STATE_NAMES.items(), key=lambda item: len(item[0]), reverse=True):
        if lowered == name:
            if name == "new york":
                return "New York, NY"
            if name == "district of columbia":
                return "Washington, DC"
            return abbr
        if lowered.endswith(name) and (len(lowered) == len(name) or not lowered[-len(name) - 1].isalpha()):
            city = text[: len(text) - len(name)].strip(" ,")
            if city:
                return f"{_city_case(city)}, {abbr}"

    match = re.fullmatch(r"(.+?)[,\s]+([A-Za-z]{2})\.?", text)
    if match and match.group(2).upper() in STATE_ABBRS:
        return f"{_city_case(match.group(1).strip(' ,'))}, {match.group(2).upper()}"
    return _city_case(text) if text.isupper() or text.islower() else text


def _retens_first_verb(bullet: str, current: bool | None) -> str:
    if current is None:
        return bullet
    match = re.match(r"^(\W*)([A-Za-z']+)(.*)$", bullet)
    if not match:
        return bullet
    prefix, word, rest = match.groups()
    key = word.lower()
    for _base, present, past in VERBS:
        if current and key == past:
            return f"{prefix}{_match_case(word, present)}{rest}"
        if not current and key == present:
            return f"{prefix}{_match_case(word, past)}{rest}"
    return bullet


def _strip_trailing_period(bullet: str) -> str:
    """Guidelines: bullet points are consistent, and they do not end with a period."""
    return re.sub(r"\.+$", "", bullet).rstrip()


def _clean_bullet(bullet: str, current: bool | None) -> str:
    text = apply_language_fixes(bullet)
    text = re.sub(r"^[\u2022\-\*\u25cf]+\s*", "", text).strip()
    if not text:
        return ""
    text = _retens_first_verb(text, current)
    if text[0].isalpha() and text[0].islower():
        text = text[0].upper() + text[1:]
    return _strip_trailing_period(text)


def _string_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        if isinstance(item, dict):
            text = apply_language_fixes(
                _text(
                    item.get("name")
                    or item.get("title")
                    or item.get("certification")
                    or item.get("credential")
                )
            )
        else:
            text = apply_language_fixes(_text(item))
        if text:
            cleaned.append(text)
    return cleaned


def _clean_job(job, *, org_keys: tuple[str, ...]) -> dict | None:
    if isinstance(job, str):
        text = _clean_bullet(job, None)
        return {"bullets": [text]} if text else None
    if not isinstance(job, dict):
        return None

    dates = normalize_dates(apply_language_fixes(_text(job.get("dates"))))
    current = is_current_role(dates)
    organization = ""
    for key in org_keys:
        organization = apply_language_fixes(_text(job.get(key)))
        if organization:
            break
    role = apply_language_fixes(_text(job.get("role") or job.get("title")))
    location = normalize_location(apply_language_fixes(_text(job.get("location"))))
    bullets = [
        cleaned
        for item in (job.get("bullets") or [])
        if (cleaned := _clean_bullet(_text(item), current))
    ]
    if not any([organization, role, dates, location, bullets]):
        return None
    return {
        "company": organization,
        "location": location,
        "role": role,
        "dates": dates,
        "bullets": bullets,
    }


def _clean_education(item) -> dict | str | None:
    if isinstance(item, str):
        text = apply_language_fixes(item)
        return text or None
    if not isinstance(item, dict):
        return None
    institution = apply_language_fixes(
        _text(item.get("institution") or item.get("school") or item.get("name"))
    )
    credential = apply_language_fixes(
        _text(item.get("credential") or item.get("degree") or item.get("field"))
    )
    location = normalize_location(apply_language_fixes(_text(item.get("location"))))
    if not any([institution, credential, location]):
        return None
    return {
        "institution": institution,
        "credential": credential,
        "location": location,
    }


def standardize_resume(structured_resume: dict) -> dict:
    data = dict(structured_resume or {})
    data["name"] = apply_language_fixes(_text(data.get("name")))
    data["title"] = apply_language_fixes(_text(data.get("title")))
    data["summary"] = apply_language_fixes(_text(data.get("summary")))

    data["core_competencies"] = [
        _strip_trailing_period(item)
        for item in _string_list(data.get("core_competencies"))
    ]
    data["technical_skills"] = _string_list(data.get("technical_skills"))
    data["certifications"] = _string_list(data.get("certifications"))
    data["additional_information"] = [
        _clean_bullet(item, None) for item in _string_list(data.get("additional_information"))
    ]
    data["additional_information"] = [item for item in data["additional_information"] if item]
    data["extracurricular_activities"] = [
        _clean_bullet(item, None) for item in _string_list(data.get("extracurricular_activities"))
    ]
    data["extracurricular_activities"] = [item for item in data["extracurricular_activities"] if item]
    data["bar_licenses"] = _string_list(data.get("bar_licenses"))

    experience = []
    for job in data.get("professional_experience") or []:
        cleaned = _clean_job(job, org_keys=("company", "organization", "employer"))
        if cleaned:
            experience.append(cleaned)
    data["professional_experience"] = experience

    volunteer = []
    for job in data.get("volunteer_experience") or []:
        cleaned = _clean_job(job, org_keys=("organization", "company", "employer"))
        if cleaned:
            volunteer.append(cleaned)
    data["volunteer_experience"] = volunteer

    education = []
    for item in data.get("education") or []:
        cleaned = _clean_education(item)
        if cleaned:
            education.append(cleaned)
    data["education"] = education

    for key in LIST_FIELDS:
        data.setdefault(key, [])
    return data
