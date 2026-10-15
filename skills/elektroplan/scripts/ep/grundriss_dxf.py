"""Architektengrundriss (Vektor-PDF) → CADCraft-Befehle, Maßstab 1:1 in mm.

Jede Linie, Fläche und jeder Text der PDF-Seite wird in Wirklichkeitsmaßen
(mm) übernommen: 1 PDF-Punkt = 25,4/72 mm auf dem Papier × Maßstab.
Graue Füllflächen (Wände) kommen auf ARCH_WAND und werden SOLID schraffiert,
rote Linien (Skizzen) auf ARCH_ROT, dicke Linien auf ARCH_DICK, der Rest auf ARCH.

Planpunkte (Meter, Ursprung oben links auf der Seite, y nach unten – wie beim
Meterraster aus grundriss_raster.py ohne Ausschnitt) rechnet `Grundriss.mm()`
in DXF-Koordinaten um.

Als Modul:  g = Grundriss.aus_pdf(pfad, 50); cmds = g.befehle()
Als Skript: python -X utf8 grundriss_dxf.py PLAN.pdf MASSSTAB AUSGABE [SEITE]
            → AUSGABE.scr, AUSGABE.dxf, AUSGABE.png
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PT_MM = 25.4 / 72

ARCH_LAYER = [  # Name, Farbe (ACI), Linienstärke mm
    ("ARCH", 8, 0.13), ("ARCH_DICK", 8, 0.35), ("ARCH_ROT", 1, 0.13),
    ("ARCH_WAND", 9, 0.13), ("ARCH_TEXT", 8, 0.13),
]


def befehl(cid: str, **p) -> str:
    return f"{cid} {json.dumps(p, ensure_ascii=False)}"


def _fix(s: str) -> str:
    """Fehlende Unicode-Zuordnung im PDF reparieren (m², °, Umlaute)."""
    s = re.sub(r"m\ufffd", "m²", s)
    s = re.sub(r"(\d)\ufffd", r"\1°", s)
    for a, b in [("\ufffdber", "über"), ("n\ufffdtig", "nötig"), ("\ufffd", "?")]:
        s = s.replace(a, b)
    return s


@dataclass
class Grundriss:
    massstab: float
    breite_mm: float                       # ganze Seite in Wirklichkeitsmaßen
    hoehe_mm: float
    linien: list = field(default_factory=list)     # (layer, [[x,y],…], geschlossen)
    texte: list = field(default_factory=list)      # (x, y, text, höhe, drehung)
    waende: list = field(default_factory=list)     # geschlossene Wandflächen [[x,y],…] (mm)
    quelle: str = ""

    # ---------------------------------------------------------------- Einlesen
    @classmethod
    def aus_pdf(cls, pdf, massstab: float, seite: int = 1) -> "Grundriss":
        import fitz
        doc = fitz.open(str(pdf))
        page = doc[int(seite) - 1]
        M = page.rotation_matrix
        H = page.rect.height                      # Höhe der angezeigten (gedrehten) Seite
        F = PT_MM * float(massstab)
        g = cls(float(massstab), page.rect.width * F, H * F, quelle=str(pdf))

        def P(pt):
            q = fitz.Point(pt) * M
            return [round(q.x * F, 1), round((H - q.y) * F, 1)]

        for d in page.get_drawings():
            lay = _layer_fuer(d)
            ketten, kette = [], []
            for it in d["items"]:
                k = it[0]
                if k == "re":
                    if kette:
                        ketten.append(kette)
                        kette = []
                    r = it[1]
                    ketten.append([P(r.tl), P(r.tr), P(r.br), P(r.bl), "zu"])
                elif k == "qu":
                    if kette:
                        ketten.append(kette)
                        kette = []
                    q = it[1]
                    ketten.append([P(q.ul), P(q.ur), P(q.lr), P(q.ll), "zu"])
                elif k in ("l", "c"):
                    if k == "l":
                        pts = [P(it[1]), P(it[2])]
                    else:                          # Bézierkurve abtasten
                        p0, p1, p2, p3 = it[1:5]
                        pts = []
                        for i in range(9):
                            t = i / 8
                            x = ((1 - t) ** 3 * p0.x + 3 * (1 - t) ** 2 * t * p1.x
                                 + 3 * (1 - t) * t * t * p2.x + t ** 3 * p3.x)
                            y = ((1 - t) ** 3 * p0.y + 3 * (1 - t) ** 2 * t * p1.y
                                 + 3 * (1 - t) * t * t * p2.y + t ** 3 * p3.y)
                            pts.append(P((x, y)))
                    if kette and kette[-1] == pts[0]:
                        kette += pts[1:]
                    else:
                        if kette:
                            ketten.append(kette)
                        kette = pts
            if kette:
                ketten.append(kette)
            for ch in ketten:
                zu = ch[-1] == "zu"
                v = [p for p in ch if p != "zu"]
                if len(v) > 2 and v[0] == v[-1]:
                    v, zu = v[:-1], True
                if len(v) < 2 or (len(v) == 2 and v[0] == v[1]):
                    continue
                g.linien.append((lay, v, zu))
                if lay == "ARCH_WAND" and zu and len(v) >= 3:
                    g.waende.append(v)

        for b in page.get_text("dict")["blocks"]:
            for zeile in b.get("lines", []):
                dx, dy = zeile["dir"]
                dv = fitz.Point(dx, dy) * fitz.Matrix(M.a, M.b, M.c, M.d, 0, 0)
                rot = round(math.degrees(math.atan2(-dv.y, dv.x)), 1)
                for s in zeile["spans"]:
                    t = _fix(s["text"]).strip()
                    if t:
                        x, y = P(s["origin"])
                        g.texte.append((x, y, t, round(s["size"] * F * 0.72, 1), rot))
        return g

    # ---------------------------------------------------------------- Umrechnung
    def mm(self, x_m: float, y_m: float) -> tuple[float, float]:
        """Planmeter (Ursprung oben links, y nach unten) → DXF-mm (y nach oben)."""
        return round(x_m * 1000, 1), round(self.hoehe_mm - y_m * 1000, 1)

    def wand_grenzen(self):
        """Umgebendes Rechteck aller Wandflächen in mm (x0, y0, x1, y1) oder None."""
        pts = [p for w in self.waende for p in w]
        if not pts:
            return None
        return (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))

    def wandkanten(self, min_laenge: float = 150.0):
        """Kanten der Wandflächen mit Normalen aus der Wand heraus (in den Raum).
        → [(a, b, (nx, ny))]"""
        out = []
        for poly in self.waende:
            flaeche = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1)
                          in zip(poly, poly[1:] + poly[:1])) / 2
            if abs(flaeche) < 1e3:
                continue
            for a, b in zip(poly, poly[1:] + poly[:1]):
                lx, ly = b[0] - a[0], b[1] - a[1]
                n = math.hypot(lx, ly)
                if n < min_laenge:
                    continue
                # gegen den Uhrzeigersinn (Fläche > 0): außen liegt rechts der Kante
                nx, ny = (ly / n, -lx / n) if flaeche > 0 else (-ly / n, lx / n)
                out.append((tuple(a), tuple(b), (nx, ny)))
        return out

    def in_wand(self, x: float, y: float) -> bool:
        for poly in self.waende:
            drin = False
            for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
                if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                    drin = not drin
            if drin:
                return True
        return False

    # ---------------------------------------------------------------- Ausgabe
    def befehle(self, ausschnitt=None) -> list[str]:
        """CADCraft-Befehle für Layer, Linien, Wandschraffur und Texte.
        ausschnitt (mm, x0 y0 x1 y1): nur Elemente übernehmen, die ihn berühren."""
        def im(pts):
            if not ausschnitt:
                return True
            x0, y0, x1, y1 = ausschnitt
            return not (max(p[0] for p in pts) < x0 or min(p[0] for p in pts) > x1
                        or max(p[1] for p in pts) < y0 or min(p[1] for p in pts) > y1)

        c = [befehl("layer.new", name=n, color=col, lineweight=lw) for n, col, lw in ARCH_LAYER]
        akt = None
        for lay, v, zu in self.linien:
            if not im(v):
                continue
            if lay != akt:
                c.append(befehl("layer.current", name=lay))
                akt = lay
            if len(v) == 2 and not zu:
                c.append(befehl("line", points=v))
            else:
                c.append(befehl("pline", vertices=v, closed=zu))
        # Wände: alle geschlossenen Polylinien auf ARCH_WAND in einem Zug füllen
        c += [befehl("layer.current", name="ARCH_WAND"),
              befehl("qselect", layer="ARCH_WAND", type="Polyline"),
              befehl("hatch", pattern="SOLID"),
              befehl("ai_deselect"),
              befehl("qselect", layer="ARCH_WAND", type="Hatch"),
              befehl("draworder.back"),
              befehl("ai_deselect"),
              befehl("layer.current", name="ARCH_TEXT")]
        for x, y, t, h, rot in self.texte:
            if im([[x, y]]):
                c.append(befehl("text", at=[x, y], text=t, height=h, rotation=rot))
        return c


def _layer_fuer(d) -> str:
    col = d.get("color") or d.get("fill") or (0, 0, 0)
    r, g, b = col
    if r > 0.6 and g < 0.4 and b < 0.4:
        return "ARCH_ROT"
    if (d.get("fill") is not None and d["type"] in ("f", "fs")
            and max(col) - min(col) < 0.05 and 0.2 < r < 0.95):
        return "ARCH_WAND"
    return "ARCH_DICK" if (d.get("width") or 0) >= 0.7 else "ARCH"


def _cli():
    try:
        from .programme import cadcraft_cli
    except ImportError:                         # als Skript aufgerufen
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from ep.programme import cadcraft_cli
    cli = cadcraft_cli()
    if not cli:
        raise RuntimeError("CADCraft nicht gefunden – installieren mit: python einrichtung.py installieren cadcraft")
    return cli


def cadcraft(*args, pruefen=True) -> str:
    """cadcraft-cli aufrufen; Ausgabe zurückgeben (die Befehlsantworten kommen über stderr)."""
    cli = _cli()
    r = subprocess.run([str(cli), *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    aus = (r.stdout or "") + (r.stderr or "")
    if pruefen and (r.returncode != 0 or "invalid parameters" in aus or "unknown command" in aus):
        raise RuntimeError(f"cadcraft-cli {args[0]} fehlgeschlagen ({r.returncode}):\n{aus[-2500:]}")
    return aus


def main(argv=None):
    a = argv or sys.argv[1:]
    if len(a) < 3:
        print(__doc__)
        return 1
    pdf, massstab, out = Path(a[0]), float(a[1]), Path(a[2])
    seite = int(a[3]) if len(a) > 3 else 1
    g = Grundriss.aus_pdf(pdf, massstab, seite)
    cmds = [befehl("new", metric=True), befehl("linetype", load="*"),
            befehl("style", name="PLAN", font="arial.ttf", current=True)]
    cmds += g.befehle() + [befehl("zoom", mode="extents")]
    scr = out.with_suffix(".scr")
    scr.write_text("\n".join(cmds) + "\n", encoding="utf-8")
    cadcraft("run", "--script-file", scr, "--save", out.with_suffix(".dxf"),
             "--export", out.with_suffix(".png"), "--view", "extents")
    print(f"{len(cmds)} Befehle, {len(g.waende)} Wandflächen, Seite {g.breite_mm:.0f} × "
          f"{g.hoehe_mm:.0f} mm → {out.with_suffix('.dxf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
