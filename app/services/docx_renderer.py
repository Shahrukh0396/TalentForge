from io import BytesIO
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


BASE_DIR = Path(__file__).resolve().parents[2]
LETTERHEAD_PATH = BASE_DIR / "app" / "templates" / "syntax_talent_letterhead.docx"


def ensure_list(v):
    if isinstance(v, list):
        return v
    if v:
        return [v]
    return []


def ensure_dict(v):
    return v if isinstance(v, dict) else {}


def add_section_header(doc, title: str):
    p = doc.add_paragraph()
    run = p.add_run(title.upper())
    run.bold = True
    run.font.name = "Cambria"
    run.font.size = Pt(10.5)

    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)

    # Bottom border
    p_pr = p._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "auto")
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def render_resume_docx(structured_resume: dict) -> bytes:
    doc = Document(str(LETTERHEAD_PATH))

    # -------------------------
    # Candidate Name (CENTERED)
    # -------------------------
    name_para = doc.add_paragraph()
    name_run = name_para.add_run(structured_resume.get("name", ""))
    name_run.bold = True
    name_run.font.name = "Cambria"
    name_run.font.size = Pt(14)
    name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_para.paragraph_format.space_after = Pt(10)

    # -------------------------
    # SUMMARY OF QUALIFICATIONS
    # -------------------------
    add_section_header(doc, "Summary of Qualifications")
    summary = structured_resume.get("summary", "")
    if summary:
        p = doc.add_paragraph(summary)
        p.paragraph_format.space_after = Pt(6)

    core = ensure_list(structured_resume.get("core_competencies"))
    if core:
        add_section_header(doc, "Core Competencies")

    # Render as multi‑column friendly list (ATS‑safe)
    for c in core:
        p = doc.add_paragraph(f"- {c}")
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.space_after = Pt(2)

    # -------------------------
    # PROFESSIONAL EXPERIENCE
    # -------------------------
    add_section_header(doc, "Professional Experience")

    experience = ensure_list(structured_resume.get("professional_experience"))

    for job in experience:
        job = ensure_dict(job)

        # Company | Location (left) — Dates (right)
        header = doc.add_paragraph()
        header.paragraph_format.tab_stops.add_tab_stop(
            Pt(450), WD_ALIGN_PARAGRAPH.RIGHT
        )

        left = header.add_run(
            f"{job.get('company', '')}, {job.get('location', '')}"
        )
        left.bold = True
        left.font.name = "Cambria"
        left.font.size = Pt(10.5)

        header.add_run("\t")

        right = header.add_run(job.get("dates", ""))
        right.font.name = "Cambria"
        right.font.size = Pt(10.5)

        # Role line (italic)
        role = doc.add_paragraph(job.get("role", ""))
        for r in role.runs:
            r.italic = True
            r.font.name = "Cambria"
            r.font.size = Pt(10.5)
        role.paragraph_format.space_after = Pt(2)

        # Bullets
        bullets = ensure_list(job.get("bullets"))
        for b in bullets:
            bp = doc.add_paragraph(f"- {b}")
            bp.paragraph_format.left_indent = Pt(18)
            bp.paragraph_format.space_after = Pt(2)

    # -------------------------
    # EDUCATION
    # -------------------------
    education = ensure_list(structured_resume.get("education"))
    if education:
        add_section_header(doc, "Education")

    for edu in education:
        # Case 1: Plain string education (most common)
        if isinstance(edu, str):
            p = doc.add_paragraph(edu)
            p.paragraph_format.space_after = Pt(2)
            continue

        # Case 2: Structured education object
        edu = ensure_dict(edu)
        inst = edu.get("institution", "")
        deg = edu.get("degree", "")

        if inst:
            ip = doc.add_paragraph(inst)
            ip.runs[0].bold = True
        if deg:
            doc.add_paragraph(deg)

    # -------------------------
    # CERTIFICATIONS
    # -------------------------
    certs = ensure_list(structured_resume.get("certifications"))
    if certs:
        add_section_header(doc, "Certifications")

    for cert in certs:
        p = doc.add_paragraph(str(cert))
        p.paragraph_format.space_after = Pt(2)


    # -------------------------
    # TECHNICAL SKILLS
    # -------------------------
    skills = ensure_list(structured_resume.get("technical_skills"))
    if skills:
        add_section_header(doc, "Technical Skills")
        doc.add_paragraph(", ".join(map(str, skills)))

    # -------------------------
    # SAVE
    # -------------------------
    out = BytesIO()
    doc.save(out)
    return out.getvalue()