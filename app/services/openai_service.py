# app/services/openai_service.py
# encoding: utf-8

import os
import json
from openai import AzureOpenAI


def format_resume_with_openai(clean_text: str) -> dict:
    """
    Sends parsed resume text to Azure OpenAI and returns structured JSON.
    """

    # ✅ Read env vars INSIDE the function
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not all([api_key, endpoint, api_version, deployment]):
        raise RuntimeError(
            "Azure OpenAI environment variables are not fully set"
        )

    # ✅ Create client lazily
    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )

    system_prompt = """
You are a professional resume editor working for a staffing firm.
Return VALID JSON ONLY. No markdown. No commentary.
"""

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean_text},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    return json.loads(content)
