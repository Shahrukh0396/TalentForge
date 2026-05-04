# app/services/openai_service.py
# encoding: utf-8

import os
import json
from openai import AzureOpenAI


SYSTEM_PROMPT = """
You are a professional resume editor working for a staffing firm.

TASK:
Convert the raw resume text into STRUCTURED JSON.

CRITICAL RULES:
- ALWAYS extract and preserve the candidate's FULL NAME.
- The candidate's name is NOT contact information.
- REMOVE contact information ONLY:
  - email addresses
  - phone numbers
  - physical addresses
  - LinkedIn URLs
  - personal websites
- DO NOT remove the candidate's name.


FORMATTING RULES:
- Fix grammar and spelling.
- Ensure consistent tense:
  - Current role = present tense
  - Past roles = past tense
- Standardize dates to: MM/YYYY – MM/YYYY
- Do NOT invent experience, companies, dates, or metrics.
- Output VALID JSON ONLY.
- Do NOT include markdown or commentary.

SECTION NORMALIZATION RULES:

The resume may use many different section headings.
You must normalize them into the following semantic sections ONLY:

- summary
- core_competencies
- professional_experience
- education
- technical_skills
- certifications

If a section heading matches ANY of the following meanings, map it accordingly:

CORE COMPETENCIES:
Includes sections titled (or similar to):
Core Competencies, Core Skills, Key Skills, Areas of Expertise,
Professional Strengths, Capabilities, Expertise, Competencies

SUMMARY:
Includes Profile, Executive Summary, Professional Summary, Overview

TECHNICAL SKILLS:
Includes Tools & Technologies, Technical Expertise, Systems, Platforms

CERTIFICATIONS:
Includes Licenses, Credentials, Professional Certifications

If the resume includes content that belongs to a category but the heading
uses different wording, still extract it into the correct semantic section.

Do NOT invent sections.
Do NOT drop content.

OUTPUT SCHEMA (MUST MATCH EXACTLY):
{
  "name": "",
  "title": "",
  "summary": "",
  "professional_experience": [
    {
      "company": "",
      "location": "City, ST",
      "role": "",
      "dates": "MM/YYYY – MM/YYYY",
      "bullets": []
    }
  ],
  "education": [],
  "technical_skills": [],
  "certifications": []
}
"""


def format_resume_with_openai(clean_text: str) -> dict:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not all([api_key, endpoint, api_version, deployment]):
        raise RuntimeError("Azure OpenAI environment variables are not fully set")

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": clean_text},
        ],
        temperature=0.2,
        response_format={"type": "json_object"}  # ✅ forces JSON
    )

    content = response.choices[0].message.content

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("OpenAI returned invalid JSON") from exc

    # ✅ Minimal schema guard (important for docxtpl)
    required_keys = [
        "name",
        "title",
        "summary",
        "professional_experience",
        "education",
        "technical_skills",
        "certifications",
    ]

    for key in required_keys:
        if key not in data:
            data[key] = [] if key.endswith("s") else ""

    return data