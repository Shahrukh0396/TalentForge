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

Glossary:
    - Name: person name can constitues a distinctive designation


FORMATTING RULES:
- Fix grammar, spelling, and punctuation.
- Capitalize the first word of each bullet. Do not capitalize ordinary words in the middle of a sentence.
- Bullet points must NOT end with a period. Keep them consistent.
- Ensure consistent tense:
  - Current role (end date is Present) = present tense
  - Previous roles = past tense
- Standardize every date range to: MM/YYYY – MM/YYYY
  Use an en dash. Use "Present" only when the candidate holds that role now.
  Example: 02/2015 – 05/2020
- Keep every source date, including a future or expected graduation date.
  Do not replace a future date with "Present" and do not drop it.
- Standardize every location to: City, ST
  Use the two-letter state abbreviation. Example: Baltimore, MD
- Standardize software names exactly:
  QuickBooks, PeopleSoft, PowerPoint, Salesforce, MicroStrategy
- Do NOT invent experience, companies, dates, degrees, or metrics.
- Output VALID JSON ONLY.
- Do NOT include markdown or commentary.

SECTION NORMALIZATION RULES:

Map source headings into these fields. Do not drop a section because the heading wording differs.

- summary: Profile, Executive Summary, Professional Summary, Overview, Summary of Qualifications
- core_competencies: Core Competencies, Core Skills, Key Skills, Areas of Expertise, Strengths
- technical_skills: Skills, Technical Skills, Tools & Technologies, Systems, Platforms
- professional_experience: Experience, Work Experience, Employment, Professional Experience
- education: Education, Academic Background. Keep the graduation date or attendance dates on each entry.
- key_accomplishments: Key Accomplishments, Selected Accomplishments, Achievements. Only a separate source section. Leave a bullet under a job in that job.
- career_highlights: Career Highlights, Professional Highlights
- awards: Awards, Honors, Honors and Awards, Recognitions
- certifications: Certifications, Credentials, Professional Certifications, and Licenses other than bar admissions. Keep the issue date and location when the source states them.
  Also list every named certification or credential mentioned anywhere else, including the summary, skills, and experience bullets. Leave that original sentence where it is, and add the certification itself here. Do not invent a certification that the source does not name. Do not put bar admissions here.
- additional_information: Additional Information, Interests, Publications, Professional Affiliations, Other
- volunteer_experience: Volunteer Experience, Community Service, Community Involvement, Pro Bono
- extracurricular_activities: Extracurricular Activities, Activities, Campus Involvement, Leadership Activities
- bar_licenses: Bar Licenses, Bar Admissions, Jurisdictions Admitted. Keep the admission date and jurisdiction when present.

Put each source section in exactly one field. Do not copy an item into a second field, except a named certification: it stays in its original section and is also listed under certifications. Do not leave these sections out.

OUTPUT SCHEMA (MUST MATCH EXACTLY):
{
  "name": "",
  "title": "",
  "summary": "",
  "core_competencies": [],
  "technical_skills": [],
  "professional_experience": [
    {
      "company": "",
      "location": "City, ST",
      "role": "",
      "dates": "MM/YYYY – MM/YYYY",
      "bullets": []
    }
  ],
  "key_accomplishments": [],
  "career_highlights": [],
  "education": [
    {
      "institution": "",
      "location": "City, ST",
      "credential": "",
      "dates": "MM/YYYY"
    }
  ],
  "bar_licenses": [
    {
      "name": "",
      "dates": "MM/YYYY",
      "location": "City, ST"
    }
  ],
  "awards": [
    {
      "name": "",
      "issuer": "",
      "dates": "MM/YYYY",
      "location": "City, ST"
    }
  ],
  "certifications": [
    {
      "name": "",
      "issuer": "",
      "dates": "MM/YYYY",
      "location": "City, ST"
    }
  ],
  "additional_information": [],
  "volunteer_experience": [
    {
      "organization": "",
      "location": "City, ST",
      "role": "",
      "dates": "MM/YYYY – MM/YYYY",
      "bullets": []
    }
  ],
  "extracurricular_activities": []
}

DO not remove professional experience locations.
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
        "core_competencies",
        "professional_experience",
        "education",
        "technical_skills",
        "certifications",
        "additional_information",
        "volunteer_experience",
        "extracurricular_activities",
        "bar_licenses",
        "key_accomplishments",
        "career_highlights",
        "awards",
    ]

    for key in required_keys:
        if key not in data:
            data[key] = [] if key not in {"name", "title", "summary"} else ""

    return data