import re

def extract_name_from_filename(filename: str) -> str | None:
    """
    Extracts name from filenames like:
    'Bascombe Arnold Resume 2025_STD0925.docx'
    """
    base = filename.rsplit(".", 1)[0]

    # Remove common suffixes
    base = re.sub(r"(resume|cv|profile).*", "", base, flags=re.I)

    words = [w for w in base.split() if w.isalpha()]

    if 2 <= len(words) <= 4:
        return " ".join(words).title()

    return None

def safe_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)

def extract_name_from_text(text: str) -> str | None:
    """
    Looks at the first 3 non-empty lines and finds a name-like line.
    """
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Heuristic: short, no digits, mostly letters
        if (
            2 <= len(line.split()) <= 4
            and not re.search(r"\d", line)
            and line.replace(" ", "").isalpha()
        ):
            return line.title()

    return None

def resolve_candidate_name(
    structured_resume: dict,
    clean_text: str,
    filename: str,
) -> str:
    # 1. OpenAI output
    name = safe_text(structured_resume.get("name"))
    if name:
        return name

    # 2. Filename
    name = extract_name_from_filename(filename)
    if name:
        return name

    # 3. First lines of resume text
    name = extract_name_from_text(clean_text)
    if name:
        return name

    # 4. Final fallback
    return "Candidate Name"

# Source: https://stackoverflow.com/a/51830413
# Modified for bullet usage (num=False)

def list_number(doc, par, prev=None, level=None, num=False):
    xpath_options = {
        True: {'single': 'count(w:lvl)=1 and ', 'level': 0},
        False: {'single': '', 'level': level},
    }

    def style_xpath(prefer_single=True):
        style = par.style.style_id
        return (
            'w:abstractNum['
                '{single}w:lvl[@w:ilvl="{level}"]/w:pStyle[@w:val="{style}"]'
            ']/@w:abstractNumId'
        ).format(style=style, **xpath_options[prefer_single])

    def type_xpath(prefer_single=True):
        type_ = 'decimal' if num else 'bullet'
        return (
            'w:abstractNum['
                '{single}w:lvl[@w:ilvl="{level}"]/w:numFmt[@w:val="{type}"]'
            ']/@w:abstractNumId'
        ).format(type=type_, **xpath_options[prefer_single])

    def get_abstract_id():
        for fn in (style_xpath, type_xpath):
            for prefer_single in (True, False):
                xpath = fn(prefer_single)
                ids = numbering.xpath(xpath)
                if ids:
                    return min(int(x) for x in ids)
        return 0

    numbering = doc.part.numbering_part.numbering_definitions._numbering

    if prev is None or prev._p.pPr is None or prev._p.pPr.numPr is None:
        if level is None:
            level = 0
        anum = get_abstract_id()
        num_obj = numbering.add_num(anum)
        num_obj.add_lvlOverride(ilvl=level).add_startOverride(1)
        num_id = num_obj.numId
    else:
        if level is None:
            level = prev._p.pPr.numPr.ilvl.val
        num_id = prev._p.pPr.numPr.numId.val

    num_pr = par._p.get_or_add_pPr().get_or_add_numPr()
    num_pr.get_or_add_numId().val = num_id
    num_pr.get_or_add_ilvl().val = level