from __future__ import annotations

import re


def split_text_area(value: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"[\\r\\n,]+", value or "") if segment.strip()]
