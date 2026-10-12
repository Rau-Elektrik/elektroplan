"""Schriftart für PDF und Textbreiten: Arial (wie QElectroTech unter Windows), sonst Helvetica."""
from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

NORMAL = "Helvetica"
FETT = "Helvetica-Bold"

_KANDIDATEN = [
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    (Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
     Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")),
    (Path("/Library/Fonts/Arial.ttf"), Path("/Library/Fonts/Arial Bold.ttf")),
]

for _reg, _bold in _KANDIDATEN:
    if _reg.exists() and _bold.exists():
        try:
            pdfmetrics.registerFont(TTFont("EP-Arial", str(_reg)))
            pdfmetrics.registerFont(TTFont("EP-Arial-Bold", str(_bold)))
            NORMAL, FETT = "EP-Arial", "EP-Arial-Bold"
        except Exception:
            pass
        break


def name(fett: bool = False) -> str:
    return FETT if fett else NORMAL
