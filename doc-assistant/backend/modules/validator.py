from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class FieldStatus:
    field: str
    value: str
    status: str   # "정상" | "누락" | "오류"
    reason: str = ""


PHONE_RE = re.compile(r"^0\d{1,2}-?\d{3,4}-?\d{4}$")
DATE_RE = re.compile(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}$")


def _validate_field(field: str, value: str) -> FieldStatus:
    if not value or not value.strip():
        return FieldStatus(field=field, value=value, status="누락")

    if "전화번호" in field or "연락처" in field:
        clean = value.replace(" ", "")
        if not PHONE_RE.match(clean):
            return FieldStatus(field=field, value=value, status="오류", reason="올바른 전화번호 형식이 아닙니다")

    if "생년월일" in field or "날짜" in field:
        if not DATE_RE.match(value.replace(" ", "")):
            return FieldStatus(field=field, value=value, status="오류", reason="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")

    if "성명" in field and len(value.strip()) < 2:
        return FieldStatus(field=field, value=value, status="오류", reason="이름이 너무 짧습니다")

    return FieldStatus(field=field, value=value, status="정상")


def validate_form(form_data: dict[str, str]) -> list[FieldStatus]:
    """모든 필드의 정상/누락/오류 상태를 반환한다."""
    return [_validate_field(field, value) for field, value in form_data.items()]


def summarize_issues(statuses: list[FieldStatus]) -> dict:
    missing = [s.field for s in statuses if s.status == "누락"]
    errors = [{"field": s.field, "reason": s.reason} for s in statuses if s.status == "오류"]
    return {"missing": missing, "errors": errors}
