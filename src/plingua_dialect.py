from __future__ import annotations

import re

OFFICIAL_MODEL_RE = re.compile(r"^\s*@model\b", re.IGNORECASE | re.MULTILINE)
OFFICIAL_SPIKING_MODEL_RE = re.compile(
    r"^\s*@model\s*<\s*spiking_psystems\s*>", re.IGNORECASE | re.MULTILINE
)


def looks_like_official_plingua(source: str) -> bool:
    return OFFICIAL_MODEL_RE.search(source) is not None


def looks_like_official_spiking(source: str) -> bool:
    return OFFICIAL_SPIKING_MODEL_RE.search(source) is not None
