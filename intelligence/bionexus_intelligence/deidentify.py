from __future__ import annotations

import re

_EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", flags=re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"(?:\+?\d{1,2}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
_MRN_PATTERN = re.compile(r"\b(?:MRN|Patient\s*ID|Subject\s*ID)\s*[:#-]?\s*[A-Z0-9-]{4,}\b", flags=re.IGNORECASE)


def deidentify_text(text: str) -> str:
    """Scrub obvious direct identifiers before loading study metadata into staging."""
    if not text:
        return ""

    cleaned = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    cleaned = _PHONE_PATTERN.sub("[REDACTED_PHONE]", cleaned)
    cleaned = _MRN_PATTERN.sub("[REDACTED_PATIENT_ID]", cleaned)
    return cleaned
