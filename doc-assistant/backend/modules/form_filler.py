from __future__ import annotations
import json
import os
from google import genai
from google.genai import types

def _client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

FORM_FIELDS = [
    "신청자 성명",
    "생년월일",
    "주소",
    "연락처 (전화번호)",
    "신청 내용",
    "신청 사유",
    "신청 날짜",
    "서명",
]


async def fill_form_from_text(transcript: str) -> dict[str, str]:
    """음성 텍스트에서 신청서 항목을 자동 추출·기입한다."""
    fields_str = "\n".join(f"- {f}" for f in FORM_FIELDS)
    prompt = f"""다음은 신청자가 음성으로 말한 내용입니다:

\"{transcript}\"

아래 신청서 항목들을 위 내용에서 추출해 JSON으로 반환하세요.
항목에 해당하는 정보가 없으면 빈 문자열("")로 설정하세요.
반드시 JSON 객체만 반환하고, 다른 텍스트는 포함하지 마세요.

항목 목록:
{fields_str}"""

    client = _client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    return {field: data.get(field, "") for field in FORM_FIELDS}


async def generate_correction_message(missing_fields: list[str], error_fields: list[dict]) -> str:
    """누락/오류 항목에 대한 보완 요청 문자 메시지를 생성한다."""
    issues = []
    if missing_fields:
        issues.append(f"누락 항목: {', '.join(missing_fields)}")
    if error_fields:
        errs = ", ".join(f"{e['field']}({e['reason']})" for e in error_fields)
        issues.append(f"오류 항목: {errs}")

    if not issues:
        return ""

    issues_str = "\n".join(issues)
    prompt = f"""신청서 검토 결과 아래 문제가 발견되었습니다:

{issues_str}

신청자에게 보낼 친절하고 간결한 보완 요청 문자 메시지를 작성하세요.
100자 이내로 작성하고, 어떤 항목을 보완해야 하는지 명확히 안내하세요."""

    client = _client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return response.text.strip()
