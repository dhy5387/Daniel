from __future__ import annotations
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from modules.stt import transcribe_audio
from modules.form_filler import fill_form_from_text, generate_correction_message
from modules.validator import validate_form, summarize_issues

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI 문서 작업 보조 시스템")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드 정적 파일 서빙
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(frontend_dir / "index.html"))


class TranscriptRequest(BaseModel):
    transcript: str


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """음성 파일을 Whisper로 텍스트 변환"""
    if not audio.content_type.startswith("audio/"):
        # webm, ogg 등도 허용
        allowed = {"audio/webm", "audio/ogg", "audio/wav", "audio/mpeg", "video/webm"}
        if audio.content_type not in allowed:
            raise HTTPException(400, f"지원하지 않는 파일 형식: {audio.content_type}")

    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(400, "빈 오디오 파일입니다")

    filename = f"{uuid.uuid4()}.webm"
    (UPLOAD_DIR / filename).write_bytes(audio_bytes)

    try:
        transcript = await transcribe_audio(audio_bytes, filename=audio.filename or filename)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"음성 인식 실패: {str(e)}")

    return {"transcript": transcript}


@app.post("/api/fill-form")
async def fill_form(req: TranscriptRequest):
    """텍스트에서 신청서 항목 자동 기입 + 유효성 검사"""
    if not req.transcript.strip():
        raise HTTPException(400, "텍스트가 비어 있습니다")

    try:
        form_data = await fill_form_from_text(req.transcript)
    except Exception as e:
        raise HTTPException(500, f"폼 기입 실패: {str(e)}")

    statuses = validate_form(form_data)
    issues = summarize_issues(statuses)

    fields = [
        {
            "field": s.field,
            "value": s.value,
            "status": s.status,
            "reason": s.reason,
        }
        for s in statuses
    ]

    return {
        "form_data": form_data,
        "fields": fields,
        "issues": issues,
        "has_issues": bool(issues["missing"] or issues["errors"]),
    }


@app.post("/api/correction-message")
async def correction_message(payload: dict):
    """누락/오류 항목에 대한 보완 요청 문자 메시지 생성"""
    missing = payload.get("missing", [])
    errors = payload.get("errors", [])

    if not missing and not errors:
        return {"message": ""}

    try:
        msg = await generate_correction_message(missing, errors)
    except Exception as e:
        raise HTTPException(500, f"메시지 생성 실패: {str(e)}")

    return {"message": msg}


@app.post("/api/ocr")
async def ocr_image(image: UploadFile = File(...)):
    """GPT-4o Vision으로 신청서 이미지의 항목별 기입 여부 분석"""
    allowed = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if image.content_type not in allowed:
        raise HTTPException(400, f"지원하지 않는 이미지 형식: {image.content_type}")

    image_bytes = await image.read()
    mime = image.content_type or "image/jpeg"

    try:
        from modules.ocr import analyze_form_fields
        fields = await analyze_form_fields(image_bytes, mime)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"분석 실패: {str(e)}")

    return {"fields": fields}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
