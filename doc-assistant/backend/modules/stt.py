from __future__ import annotations
import io
import os
import tempfile
import traceback
from pathlib import Path

from faster_whisper import WhisperModel

FFMPEG_NIX = "/nix/store/di4ja16k8a4ivwgn91hpm1fzf57ywrng-ffmpeg-6.0-bin/bin/ffmpeg"

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        # tiny 모델: ~75MB, CPU로도 빠름
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """로컬 faster-whisper로 음성을 한국어 텍스트로 변환"""
    # ffmpeg PATH 추가
    ffmpeg_dir = str(Path(FFMPEG_NIX).parent)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    suffix = Path(filename).suffix or ".webm"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        model = _get_model()
        segments, _ = model.transcribe(tmp_path, language="ko", beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text
    except Exception:
        traceback.print_exc()
        raise
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
