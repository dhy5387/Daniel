from __future__ import annotations
import os
import json
from google import genai
from google.genai import types

def _client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT = """이 신청서 이미지를 분석하여 모든 기입 항목(필드)을 찾아주세요.
각 항목에 실제로 내용이 기입되어 있는지(정상), 칸이 비어 있는지(누락)를 확인하세요.

반드시 아래 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):
[
  {"field": "항목명", "value": "기입된 내용 (없으면 빈 문자열)", "status": "정상 또는 누락"},
  ...
]

규칙:
- 항목명은 서류의 라벨 그대로 사용 (예: 성명, 생년월일, 주소, 연락처 등)
- 칸에 글자/숫자가 실제로 적혀 있으면 status = "정상", 빈칸이면 status = "누락"
- 서명/도장란은 서명이나 도장이 있으면 "정상", 없으면 "누락"
- JSON 외 어떤 텍스트도 출력하지 마세요"""


async def analyze_form_fields(image_bytes: bytes, mime: str = "image/jpeg") -> list[dict]:
    """
    Gemini Vision으로 신청서 이미지를 분석해 항목별 기입 여부를 반환한다.
    반환: [{"field": str, "value": str, "status": "정상"|"누락"}]
    """
    client = _client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            PROMPT,
        ],
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

    return json.loads(raw)
