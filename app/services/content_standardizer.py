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

# Named credentials. Ordinary uses of "certified", such as "certified the record", are not included.
_CERT_STOP_WORDS = {
    "supporting",
    "while",
    "and",
    "with",
    "for",
    "in",
    "the",
    "a",
    "an",
    "during",
    "after",
    "before",
    "by",
    "to",
    "on",
    "from",
    "who",
    "that",
    "across",
}

_CERT_MENTIONS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:AWS|Amazon Web Services|Microsoft|Google|Oracle|Cisco|Salesforce|CompTIA)\s+Certified\b"
        r"(?:\s+[A-Za-z][A-Za-z0-9+/]*){0,6}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bCertified\s+(?:Public Accountant|Management Accountant|Information Systems Auditor|"
        r"Information Systems Security Professional|Internal Auditor|Fraud Examiner|"
        r"E-Discovery Specialist|Scrum Master|Ethical Hacker|Project Management Professional)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:PMP|CAPM|CPA|CFA|CMA|CISA|CISSP|CISM|CEH|PHR|SPHR|SHRM-CP|SHRM-SCP)\b"),
    re.compile(r"\bSix Sigma(?:\s+[A-Za-z]+){0,3}\s+Belt\b", re.IGNORECASE),
)

LIST_FIELDS = (
    "core_competencies",
    "professional_experience",
    "key_accomplishments",
    "career_highlights",
    "education",
    "technical_skills",
    "certifications",
    "awards",
    "additional_information",
    "volunteer_experience",
    "extracurricular_activities",
    "bar_licenses",
)

DETAIL_FIELDS = (
    "key_accomplishments",
    "career_highlights",
    "awards",
    "certifications",
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


def _as_items(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (str, dict)):
        return [value]
    return []


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
    location = normalize_location(apply_language_fixes(_raw_location(job)))
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


def _line_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _raw_location(item: dict) -> str:
    location = _text(item.get("location"))
    if location:
        return location
    return ", ".join(
        part
        for part in (
            _text(item.get("city")),
            _text(item.get("state")),
            _text(item.get("country")),
        )
        if part
    )


def _raw_dates(item: dict) -> str:
    explicit = _text(
        item.get("dates")
        or item.get("date")
        or item.get("graduation_date")
        or item.get("year")
    )
    start = _text(item.get("start_date"))
    end = _text(item.get("end_date"))
    ranged = " – ".join(part for part in (start, end) if part)
    if not explicit:
        return ranged
    if not ranged:
        return explicit
    explicit_key = _line_key(normalize_dates(explicit))
    ranged_key = _line_key(normalize_dates(ranged))
    if not explicit_key or explicit_key == ranged_key or explicit_key in ranged_key or ranged_key in explicit_key:
        return explicit if len(explicit_key) >= len(ranged_key) else ranged
    return f"{explicit} · {ranged}"


def _clean_detail(item, *, as_bullet: bool = False) -> dict | None:
    """Keep a non-job entry, including a date and location that are not part of a role."""
    if isinstance(item, str):
        text = _clean_bullet(item, None) if as_bullet else apply_language_fixes(item)
        return {"name": text} if text else None
    if not isinstance(item, dict):
        return None

    name = apply_language_fixes(
        _text(
            item.get("name")
            or item.get("title")
            or item.get("certification")
            or item.get("credential")
            or item.get("role")
        )
    )
    if as_bullet and name:
        name = _clean_bullet(name, None)
    issuer = apply_language_fixes(_text(item.get("issuer") or item.get("organization")))
    dates = normalize_dates(apply_language_fixes(_raw_dates(item)))
    location = normalize_location(apply_language_fixes(_raw_location(item)))
    normalized_name = normalize_location(name) if name else ""
    if location and name and _line_key(location) in {_line_key(name), _line_key(normalized_name)}:
        location = ""
    bullets = [
        cleaned
        for raw in (item.get("bullets") or [])
        if (cleaned := _clean_bullet(_text(raw), is_current_role(dates)))
    ]
    if not any([name, issuer, dates, location, bullets]):
        return None

    detail = {"name": name}
    if issuer:
        detail["issuer"] = issuer
    if dates:
        detail["dates"] = dates
    if location:
        detail["location"] = location
    if bullets:
        detail["bullets"] = bullets
    return detail


def _detail_full_key(item: dict) -> str:
    return _line_key(
        " ".join(
            part
            for part in (
                item.get("name", ""),
                item.get("issuer", ""),
                item.get("dates", ""),
                item.get("location", ""),
                " ".join(item.get("bullets") or []),
            )
            if part
        )
    )


def _text_blobs(value) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        blobs: list[str] = []
        for item in value:
            blobs.extend(_text_blobs(item))
        return blobs
    if isinstance(value, dict):
        blobs = []
        for key in ("name", "title", "role", "description", "summary"):
            blobs.extend(_text_blobs(value.get(key)))
        blobs.extend(_text_blobs(value.get("bullets")))
        return blobs
    return []


def _display_certification(name: str) -> str:
    tokens = []
    for token in re.sub(r"\s+", " ", name).strip(" -").split(" "):
        word = token.strip(",.;:").lower()
        if tokens and word in _CERT_STOP_WORDS:
            break
        if tokens and token[:1].islower() and word not in {"of"}:
            break
        tokens.append(token.strip(",.;:"))
    compact = " ".join(tokens).strip(" -")
    if re.fullmatch(r"[A-Za-z]{2,6}(?:-[A-Za-z]{2,4})?", compact):
        return compact.upper()
    return compact


def _mentioned_certifications(data: dict) -> list[dict]:
    """Find credentials named outside a certifications heading."""
    sources = [
        data.get("summary"),
        data.get("title"),
        data.get("technical_skills"),
        data.get("core_competencies"),
        data.get("professional_experience"),
        data.get("volunteer_experience"),
        data.get("key_accomplishments"),
        data.get("career_highlights"),
        data.get("awards"),
        data.get("additional_information"),
        data.get("extracurricular_activities"),
    ]
    found: list[dict] = []
    seen: set[str] = set()
    for blob in (text for source in sources for text in _text_blobs(source)):
        for pattern in _CERT_MENTIONS:
            for match in pattern.finditer(blob):
                name = _display_certification(blob[match.start():match.end()])
                key = _line_key(name)
                if not key or key in seen:
                    continue
                seen.add(key)
                found.append({"name": name})
    return found


def _add_mentioned_certifications(data: dict) -> None:
    existing = {
        _line_key(item.get("name", ""))
        for item in data.get("certifications") or []
        if isinstance(item, dict)
    }
    existing.discard("")
    for cert in _mentioned_certifications(data):
        key = _line_key(cert["name"])
        if any(key == prior or key in prior or prior in key for prior in existing):
            continue
        data["certifications"].append(cert)
        existing.add(key)


def _dedupe_details(items: list[dict], claimed: set[str]) -> list[dict]:
    """Drop an entry already printed under a job or an earlier section."""
    kept = []
    for item in items:
        full_key = _detail_full_key(item)
        name_key = _line_key(item.get("name", ""))
        has_context = bool(
            item.get("dates") or item.get("location") or item.get("issuer") or item.get("bullets")
        )
        if not full_key or full_key in claimed:
            continue
        if name_key and name_key in claimed and not has_context:
            continue
        claimed.add(full_key)
        if name_key:
            claimed.add(name_key)
        for bullet in item.get("bullets") or []:
            bullet_key = _line_key(bullet)
            if bullet_key:
                claimed.add(bullet_key)
        kept.append(item)
    return kept


def _clean_education(item) -> dict | str | None:
    if isinstance(item, str):
        text = apply_language_fixes(item)
        return text or None
    if not isinstance(item, dict):
        return None
    institution = apply_language_fixes(
        _text(item.get("institution") or item.get("school") or item.get("name"))
    )
    degree = apply_language_fixes(_text(item.get("credential") or item.get("degree")))
    field = apply_language_fixes(_text(item.get("field")))
    if degree and field and _line_key(field) not in _line_key(degree):
        credential = f"{degree}, {field}"
    else:
        credential = degree or field
    location = normalize_location(apply_language_fixes(_raw_location(item)))
    dates = normalize_dates(apply_language_fixes(_raw_dates(item)))
    if not any([institution, credential, location, dates]):
        return None
    education = {
        "institution": institution,
        "credential": credential,
        "location": location,
    }
    if dates:
        education["dates"] = dates
    return education


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
    information = []
    for item in _as_items(data.get("additional_information")):
        if isinstance(item, dict):
            cleaned = _clean_detail(item, as_bullet=True)
            if cleaned:
                information.append(cleaned)
            continue
        text = _clean_bullet(_text(item), None)
        if text:
            information.append(text)
    data["additional_information"] = information
    for field in DETAIL_FIELDS:
        as_bullet = field in {"key_accomplishments", "career_highlights", "extracurricular_activities"}
        details = []
        for item in _as_items(data.get(field)):
            cleaned = _clean_detail(item, as_bullet=as_bullet)
            if cleaned:
                details.append(cleaned)
        data[field] = details

    experience = []
    for job in _as_items(data.get("professional_experience")):
        cleaned = _clean_job(job, org_keys=("company", "organization", "employer"))
        if cleaned:
            experience.append(cleaned)
    data["professional_experience"] = experience

    volunteer = []
    for job in _as_items(data.get("volunteer_experience")):
        cleaned = _clean_job(job, org_keys=("organization", "company", "employer"))
        if cleaned:
            volunteer.append(cleaned)
    data["volunteer_experience"] = volunteer

    education = []
    for item in _as_items(data.get("education")):
        cleaned = _clean_education(item)
        if cleaned:
            education.append(cleaned)
    data["education"] = education

    claimed: set[str] = set()
    for field in ("professional_experience", "volunteer_experience"):
        for job in data[field]:
            local: set[str] = set()
            bullets = []
            for bullet in job.get("bullets") or []:
                key = _line_key(bullet)
                if not key or key in local:
                    continue
                local.add(key)
                claimed.add(key)
                bullets.append(bullet)
            job["bullets"] = bullets

    for field in DETAIL_FIELDS:
        # A certification named inside a job stays on that job and is also listed
        # under certifications, so job bullets must not remove it.
        seen = set() if field == "certifications" else claimed
        data[field] = _dedupe_details(data[field], seen)

    _add_mentioned_certifications(data)
    for item in data["certifications"]:
        name_key = _line_key(item.get("name", ""))
        full_key = _detail_full_key(item)
        if name_key:
            claimed.add(name_key)
        if full_key:
            claimed.add(full_key)

    information = []
    for item in data["additional_information"]:
        if isinstance(item, dict):
            kept = _dedupe_details([item], claimed)
            information.extend(kept)
            continue
        key = _line_key(item)
        if not key or key in claimed:
            continue
        claimed.add(key)
        information.append(item)
    data["additional_information"] = information

    for key in LIST_FIELDS:
        data.setdefault(key, [])
    return data
