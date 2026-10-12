"""Projekt als PDF zeichnen – dieselben Daten wie in der .qet-Datei, 1 px = 0,25 mm."""
from __future__ import annotations

import io
import math
from datetime import date
from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

from . import schrift
from .blatt import KOPF, MM_PRO_PX, QET_RAND
from .model import (ASCENT, TEXT_RAND, ZEILENHOEHE, Blatt, Bauteil, Leitung, Projekt, drehe,
                    schriftpx, textbreite)
from .schriftfeld import logo_png, vorlage_fuer

PT_PRO_MM = 72 / 25.4
K = MM_PRO_PX * PT_PRO_MM          # PDF-Punkte je Szenenpixel
_STRICHE = {"SolidLine": None, "DashLine": (4, 2), "DotLine": (1, 2), "DashDotLine": (4, 2, 1, 2)}


# --------------------------------------------------------------------------
# Grundfunktionen im Szenenkoordinatensystem (y nach unten)
# --------------------------------------------------------------------------
def _stift(c, breite=1.0, farbe="#000000", stil="SolidLine"):
    c.setLineWidth(breite)
    c.setStrokeColor(farbe)
    muster = _STRICHE.get(stil)
    if muster:
        c.setDash([m * max(breite, 1.0) for m in muster], 0)
    else:
        c.setDash([], 0)


def _text_zeilen(c, x, y, rot, zeilen, pt, fett=False, farbe="#000000", rand=TEXT_RAND):
    """Text wie QGraphicsTextItem: Ursprung oben links inkl. Rand, Drehung um den Ursprung."""
    s = schriftpx(pt)
    c.saveState()
    c.translate(x, y)
    if rot:
        c.rotate(rot)
    c.setFillColor(farbe)
    c.setFont(schrift.name(fett), s)
    for i, z in enumerate(zeilen):
        if not z:
            continue
        c.saveState()
        c.translate(rand, rand + ASCENT * s + i * ZEILENHOEHE * s)
        c.scale(1, -1)
        c.drawString(0, 0, z)
        c.restoreState()
    c.restoreState()


def _string(c, x, y_grundlinie, text, pt, fett=False, ausrichtung="links"):
    s = schriftpx(pt)
    c.saveState()
    c.setFont(schrift.name(fett), s)
    c.setFillColor("#000000")
    w = textbreite(text, pt, fett)
    dx = {"links": 0, "mitte": -w / 2, "rechts": -w}[ausrichtung]
    c.translate(x + dx, y_grundlinie)
    c.scale(1, -1)
    c.drawString(0, 0, text)
    c.restoreState()


# --------------------------------------------------------------------------
# Rahmen und Schriftfeld
# --------------------------------------------------------------------------
def _rahmen(c, bl: Blatt):
    fmt = bl.format
    x, y, w, h = fmt.rahmen
    _stift(c, 1.0)
    c.rect(x, y, w, h, stroke=1, fill=0)
    if not bl.raster_anzeigen:
        return
    c.rect(x, y, KOPF, KOPF, stroke=1, fill=0)
    for i in range(fmt.cols):
        cx = x + KOPF + i * fmt.colsize
        c.rect(cx, y, fmt.colsize, KOPF, stroke=1, fill=0)
        _string(c, cx + fmt.colsize / 2, y + KOPF / 2 + 3.5, str(i + 1), 8, ausrichtung="mitte")
    for j in range(fmt.rows):
        cy = y + KOPF + j * fmt.rowsize
        c.rect(x, cy, KOPF, fmt.rowsize, stroke=1, fill=0)
        _string(c, x + KOPF / 2, cy + fmt.rowsize / 2 + 3.5, chr(ord("A") + j), 8,
                ausrichtung="mitte")


def _werte(bl: Blatt, nr: int, gesamt: int) -> dict:
    w = {k: str(v) for k, v in bl.felder.items()}
    w["title"] = bl.titel
    w["folio"] = f"{nr}/{gesamt}"
    return w


def _ersetze(text: str, werte: dict) -> str:
    import re
    for k in sorted(werte, key=len, reverse=True):
        text = text.replace("%{" + k + "}", werte[k]).replace("%" + k, werte[k])
    text = re.sub(r"%\{[a-z0-9_-]+\}|%[a-z0-9_-]+", "", text)
    return text


def _schriftfeld(c, bl: Blatt, nr: int, gesamt: int):
    fmt = bl.format
    v = vorlage_fuer(fmt)
    x0, y0, _, _ = fmt.schriftfeld
    werte = _werte(bl, nr, gesamt)
    _stift(c, 1.0)
    # alle Rasterzellen rahmen (wie QElectroTech), verbundene Zellen als Ganzes
    abgedeckt = {}
    for z in v.zellen:
        for r in range(z.zeile, z.zeile + z.zeilen):
            for s in range(z.spalte, z.spalte + z.spalten):
                abgedeckt[(r, s)] = z
    gezeichnet = set()
    for r in range(len(v.hoehen)):
        for s in range(len(v.breiten)):
            z = abgedeckt.get((r, s))
            if z is not None:
                if id(z) in gezeichnet:
                    continue
                gezeichnet.add(id(z))
                cx, cy, cw, ch = v.rechteck(z)
            else:
                cx, cy = sum(v.breiten[:s]), sum(v.hoehen[:r])
                cw, ch = v.breiten[s], v.hoehen[r]
            c.rect(x0 + cx, y0 + cy, cw, ch, stroke=1, fill=0)
    for z in v.zellen:
        cx, cy, cw, ch = v.rechteck(z)
        cx += x0
        cy += y0
        if z.logo:
            png = logo_png(cw, ch)
            c.saveState()
            c.translate(cx, cy + ch)
            c.scale(1, -1)
            c.drawImage(ImageReader(io.BytesIO(png)), 0, 0, cw, ch, mask="auto")
            c.restoreState()
            continue
        text = " " + _ersetze(z.wert, werte)
        if not text.strip():
            continue
        s = schriftpx(z.pt)
        w = textbreite(text, z.pt)
        faktor = min(1.0, cw / w) if w else 1.0
        c.saveState()
        c.translate(cx, cy)
        if faktor < 1.0:
            c.translate(0, ch * (1 - faktor) / 2)
            c.scale(faktor, faktor)
        bw, bh = cw / faktor, ch
        hoehe = (ASCENT + 0.212) * s
        if z.v == "top":
            gl = ASCENT * s
        elif z.v == "bottom":
            gl = bh - 0.212 * s
        else:
            gl = (bh - hoehe) / 2 + ASCENT * s
        tx = {"left": 0, "center": (bw - w) / 2, "right": bw - w}[z.h]
        c.translate(tx, gl)
        c.scale(1, -1)
        c.setFont(schrift.name(), s)
        c.setFillColor("#000000")
        c.drawString(0, 0, text)
        c.restoreState()


# --------------------------------------------------------------------------
# Bauteile
# --------------------------------------------------------------------------
def _prims(c, b: Bauteil):
    for p in b.symbol.prims:
        a = p.attrs
        if p.tag == "text":
            continue
        stil = dict(kv.split(":") for kv in a.get("style", "").split(";") if ":" in kv)
        lw = {"thin": 0.5, "normal": 1.0, "hight": 2.0, "eleve": 5.0}.get(stil.get("line-weight"), 1.0)
        ls = {"dashed": "DashLine", "dotted": "DotLine"}.get(stil.get("line-style"), "SolidLine")
        fill = stil.get("filling", "none")
        _stift(c, lw, "#000000", ls)
        c.setLineCap(2)
        c.setLineJoin(2)
        f = 0
        if fill not in ("none", ""):
            c.setFillColor({"black": "#000000", "white": "#FFFFFF", "gray": "#A0A0A0"}.get(fill, fill))
            f = 1
        if p.tag == "line":
            c.line(a["x1"], a["y1"], a["x2"], a["y2"])
        elif p.tag == "rect":
            c.rect(a["x"], a["y"], a["width"], a["height"], stroke=1, fill=f)
        elif p.tag == "ellipse":
            c.ellipse(a["x"], a["y"], a["x"] + a["width"], a["y"] + a["height"], stroke=1, fill=f)
        elif p.tag == "arc":
            # Qt: gegen den Uhrzeigersinn auf dem Bildschirm; hier ist y gespiegelt
            c.arc(a["x"], a["y"], a["x"] + a["width"], a["y"] + a["height"],
                  -a["start"], -a["angle"])
        elif p.tag == "polygon":
            pts = []
            i = 1
            while f"x{i}" in a:
                pts.append((a[f"x{i}"], a[f"y{i}"]))
                i += 1
            pfad = c.beginPath()
            pfad.moveTo(*pts[0])
            for q in pts[1:]:
                pfad.lineTo(*q)
            if a.get("closed") != "false":
                pfad.close()
            c.drawPath(pfad, stroke=1, fill=f if a.get("closed") != "false" else 0)
    c.setDash([], 0)


def _bauteil(c, b: Bauteil):
    c.saveState()
    c.translate(b.x, b.y)
    c.rotate(90 * b.ori)
    _prims(c, b)
    c.restoreState()
    # feste Texte: bleiben waagerecht, Drehpunkt = Mitte des Textkastens
    for p in b.symbol.prims:
        if p.tag != "text":
            continue
        a = p.attrs
        s = schriftpx(a["pt"])
        w = textbreite(a["text"], a["pt"])
        mx, my = a["x"] + w / 2, a["y"] - ASCENT * s + (ASCENT + 0.212) * s / 2
        gx, gy = drehe(mx, my, b.ori)
        _string(c, b.x + gx - w / 2, b.y + gy - (ASCENT + 0.212) * s / 2 + ASCENT * s, a["text"], a["pt"])
    # dynamische Texte
    for t in b.dyn_texte():
        wert = str(b.info.get(t.info, "")).strip()
        if not wert:
            continue
        ox, oy = drehe(t.x, t.y, b.ori)
        _text_zeilen(c, b.x + ox, b.y + oy, t.rot + 90 * b.ori, wert.split("\n"), t.pt, t.fett)


# --------------------------------------------------------------------------
# Leitungen
# --------------------------------------------------------------------------
def _richtungen(punkt, leitungen):
    ri = set()
    px, py = punkt
    for l in leitungen:
        for (ax, ay), (bx, by) in zip(l.punkte, l.punkte[1:]):
            if (ax, ay) == punkt:
                ri.add(((bx > ax) - (bx < ax), (by > ay) - (by < ay)))
            elif (bx, by) == punkt:
                ri.add(((ax > bx) - (ax < bx), (ay > by) - (ay < by)))
            elif ax == bx == px and min(ay, by) < py < max(ay, by):
                ri.update({(0, 1), (0, -1)})
            elif ay == by == py and min(ax, bx) < px < max(ax, bx):
                ri.update({(1, 0), (-1, 0)})
    return ri


def knotenpunkte(leitungen: list[Leitung]) -> list[tuple[float, float]]:
    """Abzweigpunkte (T-Verbindungen) an Knicken, wie QElectroTech sie zeichnet."""
    out = set()
    for l in leitungen:
        for p in l.punkte[1:-1]:
            if len(_richtungen(p, leitungen)) >= 3:
                out.add(p)
    return sorted(out)


def _markierungen(c, l: Leitung):
    (ax, ay), (bx, by) = l.mittelsegment()
    waag = ay == by
    mx, my = (ax + bx) / 2, (ay + by) / 2
    rx, ry = mx - 12, my - 12
    anzahl = (1 if l.neutral else 0) + (1 if l.schutz else 0) + l.phasen
    if not anzahl:
        return
    abstand = 24 / (anzahl + 1)
    sw = 2.0
    _stift(c, 1.0, l.farbe)
    c.setLineCap(0)
    c.setFillColor(l.farbe)
    for i in range(1, anzahl + 1):
        if waag:
            p1 = (rx + i * abstand + sw, ry + 18)
            p2 = (rx + i * abstand - sw, ry + 6)
        else:
            p2 = (rx + 18, ry + i * abstand - sw)
            p1 = (rx + 6, ry + i * abstand + sw)
        c.line(*p1, *p2)
        if l.schutz and i == 1:
            h = 2.0
            if waag:
                c.line(p2[0] - h, p2[1], p2[0] + h, p2[1])
            else:
                c.line(p2[0], p2[1] - h, p2[0], p2[1] + h)
        elif l.neutral and ((i == 1 and not l.schutz) or (i == 2 and l.schutz)):
            c.circle(p2[0], p2[1], 1.5, stroke=0, fill=1)
    c.setLineCap(2)


def _leitungen(c, bl: Blatt):
    for l in bl.leitungen:
        _stift(c, l.breite, l.farbe, l.stil)
        c.setLineCap(2)
        c.setLineJoin(0)
        pfad = c.beginPath()
        pfad.moveTo(*l.punkte[0])
        for p in l.punkte[1:]:
            pfad.lineTo(*p)
        c.drawPath(pfad, stroke=1, fill=0)
        c.setDash([], 0)
        if l.markiert:
            _markierungen(c, l)
    c.setFillColor("#000000")
    for x, y in knotenpunkte(bl.leitungen):
        c.circle(x, y, 1.5, stroke=1, fill=1)


# --------------------------------------------------------------------------
def _formen(c, bl: Blatt):
    for f in bl.formen:
        _stift(c, f.breite, f.farbe, f.stil)
        c.setLineCap(2)
        fill = 0
        if f.fuellung:
            c.setFillColor(f.fuellung)
            fill = 1
        if f.art == "Line":
            (x1, y1), (x2, y2) = f.punkte
            c.line(x1, y1, x2, y2)
        elif f.art == "Rectangle":
            (x1, y1), (x2, y2) = f.punkte
            c.rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1), stroke=1 if f.breite > 0 else 0,
                   fill=fill)
        elif f.art == "Ellipse":
            (x1, y1), (x2, y2) = f.punkte
            c.ellipse(x1, y1, x2, y2, stroke=1, fill=fill)
        elif f.art == "Polygon":
            pfad = c.beginPath()
            pfad.moveTo(*f.punkte[0])
            for p in f.punkte[1:]:
                pfad.lineTo(*p)
            if f.geschlossen:
                pfad.close()
            c.drawPath(pfad, stroke=1 if f.breite > 0 else 0, fill=fill if f.geschlossen else 0)
    c.setDash([], 0)


def _bilder(c, bl: Blatt):
    for b in bl.bilder:
        w, h = b.px_b * b.skala, b.px_h * b.skala
        c.saveState()
        c.translate(b.x, b.y + h)
        c.scale(1, -1)
        c.drawImage(ImageReader(io.BytesIO(b.png)), 0, 0, w, h, mask="auto")
        c.restoreState()


def schreibe_pdf(projekt: Projekt, pfad: Path, autor: str | None = None) -> None:
    from . import firma as _firma
    c = rl_canvas.Canvas(str(pfad))
    c.setTitle(projekt.titel)
    c.setAuthor(autor or _firma.wert("name"))
    c.setCreator("Skill elektroplan")
    gesamt = len(projekt.blaetter)
    for nr, bl in enumerate(projekt.blaetter, 1):
        fmt = bl.format
        pw, ph = fmt.papier_mm
        c.setPageSize((pw * PT_PRO_MM, ph * PT_PRO_MM))
        gw, gh = fmt.gesamt
        # Heftrand links 20 mm, sonst 10 mm; Zeichnung im verbleibenden Feld zentriert
        nutz_w, nutz_h = pw - 30, ph - 20
        ox = 20 + (nutz_w - gw * MM_PRO_PX) / 2
        oy = 10 + (nutz_h - gh * MM_PRO_PX) / 2
        c.saveState()
        c.translate(ox * PT_PRO_MM, (ph - oy) * PT_PRO_MM)
        c.scale(K, -K)
        c.translate(-QET_RAND, -QET_RAND)
        _bilder(c, bl)
        _formen(c, bl)
        _leitungen(c, bl)
        for b in bl.bauteile:
            _bauteil(c, b)
        for t in bl.texte:
            _text_zeilen(c, t.x, t.y, t.rot, t.zeilen, t.pt, t.fett, t.farbe)
        _rahmen(c, bl)
        _schriftfeld(c, bl, nr, gesamt)
        c.restoreState()
        c.showPage()
    c.save()


def vorschau_png(pdf: Path, ziel_ordner: Path, dpi: int = 110) -> list[Path]:
    """PDF-Seiten als PNG rendern (zur Sichtkontrolle)."""
    import fitz
    out = []
    with fitz.open(pdf) as doc:
        for i, seite in enumerate(doc, 1):
            pix = seite.get_pixmap(dpi=dpi)
            p = ziel_ordner / f"{pdf.stem}_Seite{i}.png"
            pix.save(p)
            out.append(p)
    return out
