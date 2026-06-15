from __future__ import annotations

import re

OFFICIAL_MODEL_RE = re.compile(r"^\s*@model\b", re.IGNORECASE | re.MULTILINE)


def looks_like_official_plingua(source: str) -> bool:
    return OFFICIAL_MODEL_RE.search(source) is not None
