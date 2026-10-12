"""Einfache Layoutprüfung: überlappende Texte, Inhalt außerhalb der Zeichenfläche."""
from __future__ import annotations

import math

from .model import ASCENT, TEXT_RAND, ZEILENHOEHE, Projekt, drehe, schriftpx, textbreite


def _kasten(x, y, rot, zeilen, pt, fett):
    s = schriftpx(pt)
    w = max((textbreite(z, pt, fett) for z in zeilen), default=0)
    h = (len(zeilen) - 1) * ZEILENHOEHE * s + (ASCENT + 0.1) * s
    ecken = [(TEXT_RAND, TEXT_RAND + 0.1 * s), (TEXT_RAND + w, TEXT_RAND + 0.1 * s),
             (TEXT_RAND, TEXT_RAND + h), (TEXT_RAND + w, TEXT_RAND + h)]
    r = math.radians(rot)
    pts = [(x + px * math.cos(r) - py * math.sin(r), y + px * math.sin(r) + py * math.cos(r))
           for px, py in ecken]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _ueberlappt(a, b, toleranz=0.5):
    return (a[0] < b[2] - toleranz and b[0] < a[2] - toleranz and
            a[1] < b[3] - toleranz and b[1] < a[3] - toleranz)


def textkaesten(bl):
    out = []
    for t in bl.texte:
        if t.text.strip():
            out.append((f"Text {t.text.splitlines()[0]!r}", _kasten(t.x, t.y, t.rot, t.zeilen, t.pt, t.fett)))
    for b in bl.bauteile:
        for t in b.dyn_texte():
            wert = str(b.info.get(t.info, "")).strip()
            if not wert:
                continue
            ox, oy = drehe(t.x, t.y, b.ori)
            out.append((f"{b.info.get('label') or b.symbol.name}: {wert.splitlines()[0]!r}",
                        _kasten(b.x + ox, b.y + oy, t.rot + 90 * b.ori, wert.split("\n"), t.pt, t.fett)))
    return out


def symbolkaesten(bl):
    """Umriss der Zeichnung jedes Bauteils (ohne Anschlussleitungen an den Enden)."""
    out = []
    for b in bl.bauteile:
        x0, y0, x1, y1 = b.symbol.grenzen()
        # Zuleitungen an den Anschlüssen nicht mitzählen: 8 px Abstand innen
        if b.symbol.anschluesse:
            ys = [a.y for a in b.symbol.anschluesse]
            if min(ys) == y0:
                y0 += 8
            if max(ys) == y1:
                y1 -= 8
        pts = [drehe(px, py, b.ori) for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        out.append((b, (b.x + min(p[0] for p in pts), b.y + min(p[1] for p in pts),
                        b.x + max(p[0] for p in pts), b.y + max(p[1] for p in pts))))
    return out


def pruefe(projekt: Projekt) -> list[str]:
    meldungen = []
    for nr, bl in enumerate(projekt.blaetter, 1):
        x, y, w, h = bl.format.zeichenflaeche(bl.raster_anzeigen)
        kaesten = textkaesten(bl)
        # Texte eines Bauteils gegen die Zeichnung anderer Bauteile
        symbole = symbolkaesten(bl)
        for b in bl.bauteile:
            for t in b.dyn_texte():
                wert = str(b.info.get(t.info, "")).strip()
                if not wert:
                    continue
                ox, oy = drehe(t.x, t.y, b.ori)
                k = _kasten(b.x + ox, b.y + oy, t.rot + 90 * b.ori, wert.split("\n"), t.pt, t.fett)
                for anderes, sk in symbole:
                    if anderes is not b and _ueberlappt(k, sk, toleranz=1.0):
                        meldungen.append(f"Blatt {nr}: Text {wert.splitlines()[0]!r} von "
                                         f"{b.info.get('label') or b.symbol.name} überdeckt "
                                         f"{anderes.info.get('label') or anderes.symbol.name}")
        for name, k in kaesten:
            if k[0] < x - 1 or k[1] < y - 1 or k[2] > x + w + 1 or k[3] > y + h + 1:
                meldungen.append(f"Blatt {nr}: {name} ragt über die Zeichenfläche")
        for i in range(len(kaesten)):
            for j in range(i + 1, len(kaesten)):
                if _ueberlappt(kaesten[i][1], kaesten[j][1]):
                    meldungen.append(f"Blatt {nr}: Texte überlappen – {kaesten[i][0]} / {kaesten[j][0]}")
        for b in bl.bauteile:
            if not (x <= b.x <= x + w and y <= b.y <= y + h):
                meldungen.append(f"Blatt {nr}: Bauteil {b.info.get('label') or b.symbol.name} "
                                 f"liegt außerhalb der Zeichenfläche")
    return meldungen
