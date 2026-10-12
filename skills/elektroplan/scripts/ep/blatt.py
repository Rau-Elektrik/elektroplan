"""Blattformate. Im PDF gilt immer 1 px = 0,25 mm, damit Maßstäbe stimmen."""
from __future__ import annotations

from dataclasses import dataclass

MM_PRO_PX = 0.25
QET_RAND = 5.0          # Diagram::margin in QElectroTech
KOPF = 20.0             # Höhe der Spaltenköpfe / Breite der Zeilenköpfe
SCHRIFTFELD_H = 80.0    # Höhe des Schriftfelds (4 Zeilen à 20 px)


@dataclass(frozen=True)
class Format:
    key: str
    name: str
    papier_mm: tuple[float, float]   # Breite, Höhe
    cols: int
    colsize: int
    rows: int
    rowsize: int

    # Rahmen inkl. Spalten-/Zeilenköpfen (QElectroTech: diagram_rect_)
    @property
    def rahmen(self) -> tuple[float, float, float, float]:
        return (QET_RAND, QET_RAND, self.cols * self.colsize + KOPF, self.rows * self.rowsize + KOPF)

    def zeichenflaeche(self, raster: bool = True) -> tuple[float, float, float, float]:
        """Nutzbare Fläche (x, y, b, h) innerhalb des Rahmens."""
        x, y, w, h = self.rahmen
        if raster:
            return (x + KOPF, y + KOPF, w - KOPF, h - KOPF)
        return (x, y, w, h)

    @property
    def schriftfeld(self) -> tuple[float, float, float, float]:
        x, y, w, h = self.rahmen
        return (x, y + h, w, SCHRIFTFELD_H)

    @property
    def gesamt(self) -> tuple[float, float]:
        x, y, w, h = self.rahmen
        return (w, h + SCHRIFTFELD_H)

    @property
    def vorlage(self) -> str:
        return f"elektroplan_{self.key.lower()}"


FORMATE = {
    # Heftrand links 20 mm, sonst 10 mm → nutzbar 390 × 277 mm = 1560 × 1108 px
    "A3Q": Format("A3Q", "A3 quer", (420.0, 297.0), cols=30, colsize=50, rows=14, rowsize=70),
    # nutzbar 180 × 277 mm = 720 × 1108 px
    "A4H": Format("A4H", "A4 hoch", (210.0, 297.0), cols=14, colsize=50, rows=14, rowsize=70),
    # nutzbar 267 × 190 mm = 1068 × 760 px
    "A4Q": Format("A4Q", "A4 quer", (297.0, 210.0), cols=20, colsize=50, rows=9, rowsize=70),
}


def format_von(name: str) -> Format:
    k = name.upper().replace(" ", "").replace("-", "")
    k = {"A3": "A3Q", "A3QUER": "A3Q", "A4": "A4Q", "A4QUER": "A4Q", "A4HOCH": "A4H"}.get(k, k)
    if k not in FORMATE:
        raise ValueError(f"Unbekanntes Blattformat {name!r} – möglich: A3 quer, A4 quer, A4 hoch")
    return FORMATE[k]
