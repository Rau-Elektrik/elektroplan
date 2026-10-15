"""Installationsplan / Deckenspiegel als CADCraft-Zeichnung (DXF + DWG + PDF).

Gleiche Plan-JSON wie für QElectroTech (Koordinaten in Metern, Ursprung oben links,
y nach unten). Unterschied: Der Grundriss ist hier keine Rasterkopie, sondern
maßgenaue Vektorgeometrie in mm:
  - "grundriss": {"pdf": "Plan.pdf", "massstab": 50, "seite": 1}
    Architektenplan als Vektor-PDF; Koordinaten = Meter ab der linken oberen
    Seitenecke (Raster aus grundriss_raster.py ohne Ausschnitt).
  - "grundriss": {"bild": "Plan.pdf", "massstab": …, "dpi": …, "ausschnitt": …, "versatz": …}
    bestehende JSON mit Rasterhintergrund: dieselbe PDF wird als Vektor gelesen,
    Ausschnitt und Versatz rechnet der Generator um.
  - "grundriss": {"raeume": […], "tueren": […], "fenster": […]} aus dem Aufmaß.

Ablauf: Skript 1 (Modellbereich: Grundriss, Blöcke, Geräte wandbündig, Linien,
`count`) → Attributtexte waagrecht neben die Symbole legen (DXF) → Skript 2
(Layout A3 mit Ansichtsfenster im Maßstab, Legende mit Stückzahlen aus `count`,
Schriftfeld mit den eigenen Firmendaten) → DXF, DWG, PDF (Logo im PDF als Originalgrafik).
"""
from __future__ import annotations

import copy
import json
import math
import re
from collections import OrderedDict
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth

from .blatt import FORMATE
from .cad_symbole import (H_INFO, H_SK, blockdefinition, cad_symbol, geometrie, grundbefehle)
from .grundriss_dxf import Grundriss, befehl, cadcraft
from .installationsplan import (LINIENARTEN, LINIEN_STUECK, LINIENNAMEN, Raum, _an_wand,
                                _oeffnung, _symbol_fuer, _wandrechteck, _zahl, _n, _de)
from . import firma as _firma
from .schriftfeld import vorlage_fuer

MASSSTAEBE = [20, 25, 50, 75, 100, 125, 150, 200, 250]
PAPIER = {"A3": (420.0, 297.0)}
RAHMEN = (20.0, 10.0, 410.0, 287.0)          # Zeichnungsrahmen auf dem Blatt (mm)
SF_H = 20.0                                   # Schriftfeldhöhe
LEG_B = 72.0                                  # Legendenbreite
VP = (25.0, 35.0, 328.0, 282.0)               # Ansichtsfenster (mm)
LAYOUT = "A3 Plan"
RICHTUNG = {"n": (0.0, -1.0), "s": (0.0, 1.0), "w": (1.0, 0.0), "o": (-1.0, 0.0)}
LTYP = {"SolidLine": "Continuous", "DashLine": "DASHED", "DashDotLine": "DASHDOT"}
LW_STUFEN = [0.13, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0]
REIHENFOLGE = ["verteiler", "steckdose", "geraet", "fernmelde", "schalter", "leuchte", "dose",
               "melder", "klingel"]


# --------------------------------------------------------------------------
def _textbreite(text: str, h: float, fett=False) -> float:
    """Breite eines Texts der Versalhöhe h (mm) in Arial ≈ Helvetica."""
    return stringWidth(text, "Helvetica-Bold" if fett else "Helvetica", h / 0.716)


def _lw(px_breite: float) -> float:
    mm = px_breite * 0.25
    return min(LW_STUFEN, key=lambda s: abs(s - mm))


def _farbe(hexwert: str) -> str:
    h = hexwert.lstrip("#")
    if h.upper() == "000000":
        return "ByLayer"
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def _ueberlapp(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _drehe(x, y, grad):
    w = math.radians(grad)
    return x * math.cos(w) - y * math.sin(w), x * math.sin(w) + y * math.cos(w)


# --------------------------------------------------------------------------
class Grundlage:
    """Grundriss + Umrechnung Planmeter → mm."""

    def __init__(self, daten: dict, basis: Path):
        gr = daten.get("grundriss", {}) or {}
        self.vektor: Grundriss | None = None
        self.raeume = [Raum(r, _zahl(gr.get("wanddicke"), 0.115)) for r in gr.get("raeume", [])]
        self.gr = gr
        quelle = gr.get("pdf") or (gr.get("bild") if str(gr.get("bild", "")).lower().endswith(".pdf")
                                   else None)
        if gr.get("bild") and not quelle:
            raise ValueError("CADCraft kann keine Rasterbilder einbinden – Grundriss als Vektor-PDF "
                             "('pdf') oder als Räume aus dem Aufmaß angeben")
        self.ax = self.ay = 0.0
        if quelle:
            pfad = Path(quelle)
            if not pfad.is_absolute():
                pfad = basis / pfad
            if not pfad.exists():
                raise FileNotFoundError(f"Grundriss-PDF nicht gefunden: {pfad}")
            massstab = _zahl(gr.get("massstab"))
            if not massstab:
                raise ValueError("Grundriss-PDF: 'massstab' angeben (z. B. 50 für 1:50)")
            self.vektor = Grundriss.aus_pdf(pfad, massstab, int(gr.get("seite", 1)))
            if gr.get("bild") and gr.get("ausschnitt"):     # alte Rasterkoordinaten
                m_px = 25.4 / int(gr.get("dpi", 150)) * massstab / 1000
                self.ax, self.ay = (float(v) * m_px for v in gr["ausschnitt"][:2])
        vx, vy = (_zahl(v) for v in gr.get("versatz", [0, 0])) if gr.get("bild") or gr.get("pdf") \
            else (0.0, 0.0)
        self.vx, self.vy = vx, vy
        if not self.vektor and not self.raeume:
            raise ValueError("Grundriss fehlt: 'pdf' (Architektenplan) oder 'raeume' angeben")
        self.rname = {r.name.lower(): r for r in self.raeume if r.name}

    def mm(self, x, y) -> tuple[float, float]:
        if self.vektor:
            return self.vektor.mm(x - self.vx + self.ax, y - self.vy + self.ay)
        return round(x * 1000, 1), round(-y * 1000, 1)

    def in_wand(self, x, y) -> bool:
        return bool(self.vektor) and self.vektor.in_wand(x, y)


# --------------------------------------------------------------------------
class Geraet:
    def __init__(self, d, cs, x, y, rot, an_wand, eingerastet):
        self.d, self.cs, self.x, self.y, self.rot = d, cs, x, y, rot
        self.an_wand, self.eingerastet = an_wand, eingerastet
        self.label = None          # Liste (tag, text, x, y)

    def bbox(self, m):
        x0, y0, x1, y1 = self.cs.grenzen
        pts = [_drehe(px * m, py * m, self.rot) for px, py in
               ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        return (self.x + min(p[0] for p in pts), self.y + min(p[1] for p in pts),
                self.x + max(p[0] for p in pts), self.y + max(p[1] for p in pts))

    def attribute(self) -> dict:
        d = self.d
        hoehe = f"h={_de(_zahl(d['hoehe']))}" if d.get("hoehe") not in (None, "") else ""
        return {"SK": _n(d.get("stromkreis") or d.get("bmk")), "HOEHE": hoehe,
                "BEM": _n(d.get("text2") or d.get("bemerkung"))}


def _einrasten(g: Grundlage, p, hinweis, fang: float):
    """Wandpunkt auf der nächsten Wandoberfläche → (punkt, richtung in den Raum) oder None."""
    best = None
    for a, b, n in g.vektor.wandkanten():
        lx, ly = b[0] - a[0], b[1] - a[1]
        laenge = math.hypot(lx, ly)
        t = ((p[0] - a[0]) * lx + (p[1] - a[1]) * ly) / laenge ** 2
        if t < -100 / laenge or t > 1 + 100 / laenge:
            continue
        s = (p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1]
        if not (-fang <= s <= fang):
            continue
        if hinweis and n[0] * hinweis[0] + n[1] * hinweis[1] < 0.7:
            continue
        t = min(max(t, 0.0), 1.0)
        if best is None or abs(s) < best[0]:
            best = (abs(s), (round(a[0] + t * lx, 1), round(a[1] + t * ly, 1)), n)
    return (best[1], best[2]) if best else None


def _geraete(daten, g: Grundlage, m: float, hinweise: list) -> list[Geraet]:
    out = []
    fang = _zahl((daten.get("grundriss") or {}).get("fangradius"), 0.4) * 1000
    nicht = []
    for d in daten.get("geraete", []):
        sym, an_wand = _symbol_fuer(d)
        cs = cad_symbol(sym, an_wand, _n(d.get("legende")))
        x, y = _zahl(d.get("x")), _zahl(d.get("y"))
        wand = _n(d.get("wand")).lower()
        richtung = None
        eingerastet = False
        raum = None
        if _n(d.get("raum")):
            raum = g.rname.get(_n(d.get("raum")).lower())
            if raum is None:
                raise ValueError(f"Gerät {d}: Raum {d.get('raum')!r} gibt es nicht")
            x, y = raum.x + x, raum.y + y
        elif g.raeume:
            raum = next((r for r in g.raeume if r.enthaelt(x, y)), None)
        hint = RICHTUNG.get({"e": "o"}.get(wand[:1], wand[:1])) if wand and wand != "frei" else None
        px, py = g.mm(x, y)
        if an_wand and wand != "frei":
            if raum is not None:
                x, y, ori = _an_wand(raum, x, y, wand or None)
                px, py = g.mm(x, y)
                richtung = RICHTUNG["nosw"[ori]]
                eingerastet = True
            elif g.vektor:
                treffer = _einrasten(g, (px, py), hint, fang)
                if treffer:
                    (px, py), richtung = treffer
                    eingerastet = True
                else:
                    nicht.append(f"{d.get('symbol')} {_n(d.get('stromkreis'))} bei "
                                 f"x={_de(x)} y={_de(y)}")
            richtung = richtung or hint or (0.0, -1.0)
            rot = math.degrees(math.atan2(richtung[1], richtung[0])) + 90
        else:
            rot = -90 * "nosw".index({"e": "o"}.get(wand[:1], wand[:1])) if wand[:1] in "nosew" \
                and wand else 0.0
        if d.get("drehung") not in (None, ""):
            rot = -_zahl(d["drehung"])      # Grad im Uhrzeigersinn wie im Grundriss
        out.append(Geraet(d, cs, px, py, round(rot % 360, 3), an_wand, eingerastet))
    if nicht:
        hinweise.append(f"(Lage) {len(nicht)} Wandgeräte ohne Massivwand im Fangradius "
                        f"({_de(fang / 1000)} m) – Leichtbau-/Glaswand oder frei, Lage aus der "
                        f"JSON übernommen: " + "; ".join(nicht))
    return out


# --------------------------------------------------------------------------
def _beschriftungen(geraete: list[Geraet], m: float, g: Grundlage, hindernisse: list):
    """Attributtexte waagrecht neben das Symbol legen, ohne Überdeckung."""
    gap = 0.8 * m
    hs, hi = H_SK * m, H_INFO * m
    belegt = [ge.bbox(m) for ge in geraete] + list(hindernisse)
    for i, ge in enumerate(geraete):
        at = ge.attribute()
        z1 = at["SK"]
        z2 = " ".join(v for v in (at["HOEHE"], at["BEM"]) if v)
        zeilen = [(z, h, f) for z, h, f in ((z1, hs, True), (z2, hi, False)) if z]
        if not zeilen:
            ge.label = [(t, ge.x, ge.y) for t in ("SK", "HOEHE", "BEM")]
            continue
        w = max(_textbreite(z, h, f) for z, h, f in zeilen)
        h = sum(z[1] for z in zeilen) + 0.9 * m * (len(zeilen) - 1)
        x0, y0, x1, y1 = ge.bbox(m)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        k = {"R": (x1 + gap, cy - h / 2), "L": (x0 - gap - w, cy - h / 2),
             "O": (cx - w / 2, y1 + gap), "U": (cx - w / 2, y0 - gap - h),
             "RO": (x1 + gap, y1 - h * 0.3), "RU": (x1 + gap, y0 - h * 0.7),
             "LO": (x0 - gap - w, y1 - h * 0.3), "LU": (x0 - gap - w, y0 - h * 0.7)}
        rot = ge.rot % 360
        if not ge.an_wand:
            folge = ["R", "L", "O", "U", "RO", "RU", "LO", "LU"]
        elif abs(rot - 0) < 45 or abs(rot - 360) < 45:       # hängt nach unten (Nordwand)
            folge = ["R", "L", "U", "RU", "LU", "RO", "LO"]
        elif abs(rot - 180) < 45:                            # zeigt nach oben (Südwand)
            folge = ["R", "L", "O", "RO", "LO", "RU", "LU"]
        elif abs(rot - 90) < 45:                             # zeigt nach rechts (Westwand)
            folge = ["R", "O", "U", "RO", "RU", "L"]
        else:                                                # zeigt nach links (Ostwand)
            folge = ["L", "O", "U", "LO", "LU", "R"]
        eigen = belegt[i]
        best = None
        for key in folge:
            bx, by = k[key]
            box = (bx, by, bx + w, by + h)
            score = sum(_ueberlapp(box, b) for j, b in enumerate(belegt) if b is not eigen)
            pts = [(bx + w * fx, by + h * fy) for fx in (0.05, 0.5, 0.95) for fy in (0.1, 0.9)]
            score += sum(w * h / 6 for p in pts if g.in_wand(*p))
            if best is None or score < best[0] - 1e-6:
                best = (score, box)
            if score == 0:
                break
        bx, by, bx1, by1 = best[1]
        belegt.append(best[1])
        top = by1
        lab = []
        if z1:
            top -= hs
            lab.append(("SK", round(bx, 1), round(top, 1)))
            top -= 0.9 * m
        else:
            lab.append(("SK", round(bx, 1), round(top, 1)))
        y2 = round(top - hi, 1)
        lab.append(("HOEHE", round(bx, 1), y2))
        versatz = _textbreite(at["HOEHE"] + " ", hi) if at["HOEHE"] else 0.0
        lab.append(("BEM", round(bx + versatz, 1), y2))
        ge.label = lab


def patche_attribute(dxf: Path, geraete: list[Geraet]) -> int:
    """ATTRIB-Positionen in der DXF setzen (Text waagrecht, linksbündig auf der Grundlinie)."""
    roh = dxf.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in roh else "\n"
    z = roh.split(nl)
    ziel = {}
    for ge in geraete:
        ziel.setdefault(ge.cs.block, []).append(((ge.x, ge.y), {t: (x, y) for t, x, y in ge.label}))
    n = 0
    i = 0
    insert = None          # aktuelle Zielwerte für die folgenden ATTRIBs
    while i < len(z) - 1:
        code, val = z[i].strip(), z[i + 1].strip()
        if code == "0":
            if val == "INSERT":
                name = x = y = None
                j = i + 2
                while j < len(z) - 1 and z[j].strip() != "0":
                    c, v = z[j].strip(), z[j + 1].strip()
                    if c == "2":
                        name = v
                    elif c == "10":
                        x = float(v)
                    elif c == "20":
                        y = float(v)
                    j += 2
                insert = None
                for k, ((gx, gy), lab) in enumerate(ziel.get(name, [])):
                    if abs(gx - x) < 2 and abs(gy - y) < 2:
                        insert = lab
                        ziel[name].pop(k)
                        break
            elif val == "ATTRIB":
                if insert:
                    idx = {}
                    j = i + 2
                    while j < len(z) - 1 and z[j].strip() != "0":
                        idx.setdefault(z[j].strip(), j + 1)
                        j += 2
                    tag = z[idx["2"]].strip() if "2" in idx else ""
                    if tag in insert:
                        tx, ty = insert[tag]
                        z[idx["10"]] = f"{tx:.1f}"
                        z[idx["20"]] = f"{ty:.1f}"
                        if "11" in idx:
                            z[idx["11"]] = f"{tx:.1f}"
                            z[idx["21"]] = f"{ty:.1f}"
                        if "50" in idx:
                            z[idx["50"]] = "0.0"
                        n += 1
            else:
                insert = None
        i += 2
    dxf.write_bytes(nl.join(z).encode("utf-8"))
    return n


# --------------------------------------------------------------------------
def _raeume_befehle(g: Grundlage, daten) -> list[str]:
    """Wände, Türen, Fenster, Raumnamen aus dem Aufmaß (Rechteckräume)."""
    gr = daten.get("grundriss", {})
    tueren = [(g.rname[_n(d.get("raum")).lower()], {**d, "_art": "tuer"}) for d in gr.get("tueren", [])]
    fenster = [(g.rname[_n(d.get("raum")).lower()], {**d, "_art": "fenster"})
               for d in gr.get("fenster", [])]
    oeffnungen = []
    for r, d in tueren + fenster:
        seite, a0, a1, dicke = _oeffnung(r, d)
        x, y, w, h = _wandrechteck(r, seite, a0, a1, dicke)
        oeffnungen.append((x, y, x + w, y + h))
    baender = []
    for r in g.raeume:
        x0, y0, x1, y1 = r.aussen()
        seiten = {"n": (x0, y0, x1, r.y, "h"), "s": (x0, r.y + r.t, x1, y1, "h"),
                  "w": (x0, r.y, r.x, r.y + r.t, "v"), "o": (r.x + r.b, r.y, x1, r.y + r.t, "v")}
        for s, (a, b, c, d, lage) in seiten.items():
            if s in r.offen or c - a < 1e-6 or d - b < 1e-6:
                continue
            stuecke = [(a, c)] if lage == "h" else [(b, d)]
            for ox0, oy0, ox1, oy1 in oeffnungen:
                quer = (min(d, oy1) - max(b, oy0)) if lage == "h" else (min(c, ox1) - max(a, ox0))
                if quer <= 0.001:
                    continue
                u0, u1 = (ox0, ox1) if lage == "h" else (oy0, oy1)
                neu = []
                for p0, p1 in stuecke:
                    if u1 <= p0 or u0 >= p1:
                        neu.append((p0, p1))
                        continue
                    if u0 > p0:
                        neu.append((p0, u0))
                    if u1 < p1:
                        neu.append((u1, p1))
                stuecke = neu
            for p0, p1 in stuecke:
                if p1 - p0 > 0.005:
                    baender.append((p0, b, p1, d) if lage == "h" else (a, p0, c, p1))
    c = [befehl("layer.new", name="ARCH", color=8, lineweight=0.13),
         befehl("layer.new", name="ARCH_WAND", color=9, lineweight=0.13),
         befehl("layer.current", name="ARCH_WAND")]
    for x0, y0, x1, y1 in baender:
        c.append(befehl("pline", vertices=[list(g.mm(x0, y0)), list(g.mm(x1, y0)),
                                           list(g.mm(x1, y1)), list(g.mm(x0, y1))], closed=True))
    c += [befehl("qselect", layer="ARCH_WAND", type="Polyline"), befehl("hatch", pattern="SOLID"),
          befehl("ai_deselect"), befehl("layer.current", name="ARCH")]
    for r, d in fenster:
        seite, a0, a1, dicke = _oeffnung(r, d)
        x, y, w, h = _wandrechteck(r, seite, a0, a1, dicke)
        c.append(befehl("pline", vertices=[list(g.mm(x, y)), list(g.mm(x + w, y)),
                                           list(g.mm(x + w, y + h)), list(g.mm(x, y + h))],
                        closed=True))
        if seite in "ns":
            c.append(befehl("line", points=[list(g.mm(x, y + h / 2)), list(g.mm(x + w, y + h / 2))]))
        else:
            c.append(befehl("line", points=[list(g.mm(x + w / 2, y)), list(g.mm(x + w / 2, y + h))]))
    for r, d in tueren:
        seite, a0, a1, dicke = _oeffnung(r, d)
        breite = a1 - a0
        ende = _n(d.get("anschlag")).lower() in ("ende", "rechts", "unten")
        aussen = _n(d.get("aufgehend")).lower() in ("aussen", "außen", "nach_aussen")
        if seite in "ns":
            hy = (r.y - (dicke if aussen else 0)) if seite == "n" else (r.y + r.t + (dicke if aussen else 0))
            hx = r.x + (a1 if ende else a0)
            richt = (0, -1 if aussen else 1) if seite == "n" else (0, 1 if aussen else -1)
            entlang = (-1, 0) if ende else (1, 0)
        else:
            hx = (r.x - (dicke if aussen else 0)) if seite == "w" else (r.x + r.b + (dicke if aussen else 0))
            hy = r.y + (a1 if ende else a0)
            richt = (-1 if aussen else 1, 0) if seite == "w" else (1 if aussen else -1, 0)
            entlang = (0, -1) if ende else (0, 1)
        c.append(befehl("line", points=[list(g.mm(hx, hy)), list(g.mm(hx + richt[0] * breite,
                                                                     hy + richt[1] * breite))]))
        pts = []
        for i in range(13):
            phi = math.pi / 2 * i / 12
            vx = richt[0] * math.cos(phi) + entlang[0] * math.sin(phi)
            vy = richt[1] * math.cos(phi) + entlang[1] * math.sin(phi)
            pts.append(list(g.mm(hx + vx * breite, hy + vy * breite)))
        c.append(befehl("pline", vertices=pts, closed=False))
    return c


def _raumtexte(g: Grundlage, daten, m, belegt) -> tuple[list[str], list]:
    """Raumnamen (Räume aus dem Aufmaß bzw. 'texte') → Befehle, belegte Flächen.
    Räume aus dem Aufmaß: Name und Fläche an eine freie Stelle (Mitte bevorzugt)."""
    c, boxen = [befehl("layer.current", name="ELT_RAUM"), befehl("style.current", name="PLAN_FETT")], []
    h = 2.2 * m
    for r in g.raeume:
        if not r.name:
            continue
        zeilen = [(r.name, h, True)]
        if r.zeige_flaeche is not False:
            fl = r.zeige_flaeche if isinstance(r.zeige_flaeche, (int, float)) and not isinstance(r.zeige_flaeche, bool) else r.b * r.t
            zeilen.append((f"{_de(fl, 1)} m²", h * 0.8, False))
        if r.zusatz:
            zeilen += [(z, h * 0.7, False) for z in r.zusatz.split(chr(10))]
        bw = max(_textbreite(t, hh, f) for t, hh, f in zeilen)
        bh = sum(hh * 1.6 for _, hh, _ in zeilen)
        if r.textpos:
            kandidaten = [(r.x + _zahl(r.textpos[0]), r.y + _zahl(r.textpos[1]))]
        else:
            cx, cy = r.x + r.b / 2, r.y + r.t / 2
            kandidaten = [(cx + a, cy + b) for b in (0, 0.55, -0.55, 0.9, -0.9, 1.3, -1.3)
                          for a in (0, 0.8, -0.8, 1.4, -1.4)
                          if r.x + 0.3 < cx + a < r.x + r.b - 0.3
                          and r.y + 0.3 < cy + b < r.y + r.t - 0.3] or [(cx, cy)]
        wahl = None
        for kx, ky in kandidaten:
            px, py = g.mm(kx, ky)
            box = (px - bw / 2 - 0.5 * m, py - bh / 2, px + bw / 2 + 0.5 * m, py + bh / 2)
            score = sum(_ueberlapp(box, b) for b in belegt)
            if wahl is None or score < wahl[0]:
                wahl = (score, px, py, box)
            if score == 0:
                break
        _, px, py, box = wahl
        boxen.append(box)
        y = py + bh / 2 - zeilen[0][1] * 1.1
        for t, hh, fett in zeilen:
            c += [befehl("style.current", name="PLAN_FETT" if fett else "PLAN"),
                  befehl("text", at=[round(px, 1), round(y - hh / 2, 1)], text=t,
                         height=round(hh, 1), justify="BC")]
            y -= hh * 1.6
    for d in daten.get("texte", []):
        px, py = g.mm(_zahl(d.get("x")), _zahl(d.get("y")))
        hh = _zahl(d.get("groesse"), 8) / 8 * h
        fett = d.get("fett", True)
        t = _n(d.get("text"))
        c += [befehl("style.current", name="PLAN_FETT" if fett else "PLAN"),
              befehl("text", at=[px, py], text=t, height=round(hh, 1), justify="MC")]
        w = _textbreite(t, hh, fett)
        boxen.append((px - w / 2, py - hh / 2, px + w / 2, py + hh / 2))
    for s in (daten.get("grundriss") or {}).get("sanitaer", []) or []:
        r = g.rname.get(_n(s.get("raum")).lower())
        if r is None:
            continue
        sx, sy = r.x + _zahl(s.get("x")), r.y + _zahl(s.get("y"))
        sb, st = _zahl(s.get("b"), 0.9), _zahl(s.get("t"), 0.9)
        c += [befehl("style.current", name="PLAN"), befehl("linetype", current="DASHED"),
              befehl("pline", vertices=[list(g.mm(sx, sy)), list(g.mm(sx + sb, sy)),
                                        list(g.mm(sx + sb, sy + st)), list(g.mm(sx, sy + st))],
                     closed=True),
              befehl("linetype", current="ByLayer"),
              befehl("text", at=list(g.mm(sx + sb / 2, sy + st / 2)),
                     text=_n(s.get("art")).capitalize() or "Dusche", height=round(1.6 * m, 1),
                     justify="MC")]
    c.append(befehl("style.current", name="PLAN"))
    return c, boxen


def _linien(g: Grundlage, daten, m) -> tuple[list[str], "OrderedDict", list]:
    c = [befehl("layer.current", name="ELT_LINIEN")]
    leg: "OrderedDict[tuple, list]" = OrderedDict()
    alle = []
    for d in daten.get("linien", []):
        art = _n(d.get("art")).lower() or "lichtschiene"
        stil = dict(LINIENARTEN.get(art, LINIENARTEN["lichtschiene"]))
        if d.get("farbe"):
            stil["farbe"] = d["farbe"]
        if d.get("mitte"):
            mx, my = (_zahl(v) for v in d["mitte"])
            w = math.radians(_zahl(d.get("winkel")))
            hl = _zahl(d.get("laenge"), 1.0) / 2
            pts = [(mx - hl * math.cos(w), my - hl * math.sin(w)),
                   (mx + hl * math.cos(w), my + hl * math.sin(w))]
        else:
            pts = [(_zahl(p[0]), _zahl(p[1])) for p in d.get("punkte", [])]
        if len(pts) < 2:
            continue
        mm_pts = [list(g.mm(*p)) for p in pts]
        alle.append(mm_pts)
        lt, lw, col = LTYP.get(stil["stil"], "Continuous"), _lw(stil["breite"]), _farbe(stil["farbe"])
        c += [befehl("linetype", current=lt), befehl("lweight", lineweight=lw),
              befehl("color", color=col), befehl("pline", vertices=mm_pts, closed=False)]
        stueck = art in LINIEN_STUECK
        if stueck:
            for a, b in ((mm_pts[0], mm_pts[1]), (mm_pts[-1], mm_pts[-2])):
                lx, ly = b[0] - a[0], b[1] - a[1]
                n = math.hypot(lx, ly) or 1
                q = 120.0
                c.append(befehl("line", points=[[a[0] - ly / n * q, a[1] + lx / n * q],
                                                [a[0] + ly / n * q, a[1] - lx / n * q]]))
        c += [befehl("linetype", current="ByLayer"), befehl("lweight", lineweight="ByLayer")]
        txt = _n(d.get("text") or d.get("stromkreis"))
        if txt:
            if d.get("textpos"):
                tx, ty = g.mm(*(_zahl(v) for v in d["textpos"]))
            else:
                (ax, ay), (bx, by) = mm_pts[0], mm_pts[1]
                lx, ly = bx - ax, by - ay
                n = math.hypot(lx, ly) or 1
                tx, ty = (ax + bx) / 2 + ly / n * 2.0 * m, (ay + by) / 2 - lx / n * 2.0 * m
            c.append(befehl("text", at=[round(tx, 1), round(ty, 1)], text=txt,
                            height=round(1.5 * m, 1), justify="ML"))
        c.append(befehl("color", color="ByLayer"))
        laenge = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        if d.get("legende") is False:
            continue
        name = _n(d.get("name")) or LINIENNAMEN.get(art, art)
        e = leg.setdefault((name, lt, lw, col), [(lt, lw, col), name, 0.0, 0 if stueck else None])
        e[2] += laenge
        if stueck:
            e[3] += 1
    return c, leg, alle


# --------------------------------------------------------------------------
def _schriftfeld(felder: dict) -> list[str]:
    v = vorlage_fuer(FORMATE["A3Q"])
    x0, y0, x1, _ = RAHMEN
    sx = (x1 - x0) / sum(v.breiten)
    sy = SF_H / sum(v.hoehen)
    top = y0 + SF_H
    c = [befehl("layer.current", name="ELT_SCHRIFTFELD")]
    logo_zelle = None
    for z in v.zellen:
        x, y, w, h = v.rechteck(z)
        ax, ay, bx, by = x0 + x * sx, top - (y + h) * sy, x0 + (x + w) * sx, top - y * sy
        c.append(befehl("rectang", p1=[round(ax, 3), round(ay, 3)], p2=[round(bx, 3), round(by, 3)]))
        if z.logo:
            logo_zelle = (ax, ay, bx, by)
            continue
        t = z.wert
        for k, val in felder.items():
            t = t.replace(f"%{k}", val)
        if not t.strip():
            continue
        hh = z.pt * 25.4 / 72 * 0.716
        fett = z.wert in ("%title",) or t == (_firma.wert("name") or _firma.PLATZHALTER_NAME)
        just, tx = ("MC", (ax + bx) / 2) if z.h == "center" else ("ML", ax + 1.2)
        while _textbreite(t, hh, fett) > (bx - ax) - 2 and hh > 1.0:
            hh *= 0.92
        c += [befehl("style.current", name="PLAN_FETT" if fett else "PLAN"),
              befehl("text", at=[round(tx, 3), round((ay + by) / 2, 3)], text=t,
                     height=round(hh, 3), justify=just)]
    c.append(befehl("style.current", name="PLAN"))
    return c, logo_zelle


def _logo_vektor(zelle) -> list[str]:
    """Logo-Zelle in DXF/DWG: Firmenname als Text (CADCraft kann keine Bilder einbetten;
    im PDF liegt das eingerichtete Logo als Originalgrafik darüber)."""
    if not zelle:
        return []
    ax, ay, bx, by = zelle
    name = _firma.wert("name") or _firma.PLATZHALTER_NAME
    hh = min((by - ay) * 0.28, 5.0)
    while _textbreite(name, hh, True) > (bx - ax) * 0.9 and hh > 1.0:
        hh *= 0.92
    return [befehl("layer.current", name="ELT_LOGO"), befehl("style.current", name="PLAN_FETT"),
            befehl("text", at=[round((ax + bx) / 2, 3), round((ay + by) / 2, 3)], text=name,
                   height=round(hh, 3), justify="MC"),
            befehl("style.current", name="PLAN")]


def _legende(eintraege, linien_leg, m, felder, hinweis_text) -> list[str]:
    x0 = VP[2] + 5
    x1 = RAHMEN[2] - 5
    y = VP[3]
    c = [befehl("layer.current", name="ELT_LEGENDE"), befehl("style.current", name="PLAN_FETT"),
         befehl("text", at=[x0, y - 3], text="Legende", height=3.0, justify="ML"),
         befehl("style.current", name="PLAN")]
    y -= 6.5
    c.append(befehl("line", points=[[x0, y], [x1, y]]))
    for cs, anzahl in eintraege:
        gx0, gy0, gx1, gy1 = cs.grenzen
        zeile = max(6.5, gy1 - gy0 + 2.5)
        cy = y - zeile / 2
        ix, iy = x0 + 6 - (gx0 + gx1) / 2, cy - (gy0 + gy1) / 2
        c.append(befehl("insert", name=cs.block, at=[round(ix, 3), round(iy, 3)], scale=1))
        name = cs.name
        h = 1.8
        while _textbreite(name, h) > (x1 - x0) - 22 and h > 1.3:
            h *= 0.94
        c += [befehl("text", at=[x0 + 15, round(cy, 3)], text=name, height=round(h, 3), justify="ML"),
              befehl("text", at=[x1, round(cy, 3)], text=f"{anzahl}×", height=1.8, justify="MR")]
        y -= zeile
    for (lt, lw, col), name, laenge, stueck in linien_leg:
        cy = y - 3.25
        c += [befehl("linetype", current=lt), befehl("lweight", lineweight=lw),
              befehl("color", color=col),
              befehl("line", points=[[x0 + 1, round(cy, 3)], [x0 + 12, round(cy, 3)]]),
              befehl("linetype", current="ByLayer"), befehl("lweight", lineweight="ByLayer"),
              befehl("color", color="ByLayer")]
        wert = f"{stueck}×" if stueck is not None else f"ca. {_de(laenge, 1)} m"
        c += [befehl("text", at=[x0 + 15, round(cy, 3)], text=name, height=1.8, justify="ML"),
              befehl("text", at=[x1, round(cy, 3)], text=wert, height=1.8, justify="MR")]
        y -= 6.5
    c.append(befehl("line", points=[[x0, round(y, 3)], [x1, round(y, 3)]]))
    y -= 3.5
    for t in hinweis_text:
        c.append(befehl("text", at=[x0, round(y, 3)], text=t, height=1.4, justify="ML"))
        y -= 2.6
    # Maßstabsleiste
    meter = 0.5
    for mm_ in (0.5, 1, 2, 5, 10, 20):
        if 5 * mm_ * 1000 / m <= (x1 - x0) - 8:
            meter = mm_
    seg = meter * 1000 / m
    yb = RAHMEN[1] + SF_H + 9
    c.append(befehl("text", at=[x0, yb + 5], text=f"Maßstab 1:{m:g} (bei Druck in Originalgröße A3)",
                    height=1.6, justify="ML"))
    for i in range(5):
        xa = x0 + i * seg
        c.append(befehl("rectang", p1=[round(xa, 3), yb], p2=[round(xa + seg, 3), yb + 1.2]))
        if i % 2 == 0:
            c.append(befehl("pline", vertices=[[round(xa, 3), yb + 0.6], [round(xa + seg, 3), yb + 0.6]],
                            width=1.2))
        c.append(befehl("text", at=[round(xa, 3), yb - 1.2], text=f"{i * meter:g}".replace(".", ","),
                        height=1.3, justify="TC"))
    c.append(befehl("text", at=[round(x0 + 5 * seg, 3), yb - 1.2],
                    text=f"{5 * meter:g} m".replace(".", ","), height=1.3, justify="TC"))
    return c


# --------------------------------------------------------------------------
def _als_installationsplan(daten: dict) -> tuple[dict, list]:
    """Deckenspiegel → Installationsplan-Daten (Leuchten berechnet und gesetzt)."""
    art = _n(daten.get("plan")).lower()
    if art not in ("deckenspiegel", "lichtplanung", "lichtplan"):
        return daten, []
    from .deckenspiegel import berechne, hinweise, leuchten_geraete
    berechne(daten)
    geraete, linien, texte, zusatz = leuchten_geraete(daten)
    plan = copy.deepcopy({k: v for k, v in daten.items() if not k.startswith("_")})
    plan["titel"] = _n(daten.get("titel")) or "Deckenspiegel"
    plan["plantyp"] = _n(daten.get("plantyp")) or "Deckenspiegel · Lichtberechnung DIN EN 12464-1 (Überschlag)"
    plan["geraete"] = (daten.get("geraete") or []) + geraete
    plan["linien"] = (daten.get("linien") or []) + linien
    plan["texte"] = (daten.get("texte") or []) + texte
    for r in (plan.get("grundriss") or {}).get("raeume", []):
        if _n(r.get("name")) in zusatz:
            r["zusatztext"] = zusatz[_n(r["name"])]
    return plan, list(hinweise(daten))


def _grenzen_viewport(g: Grundlage, geraete, m, extra_pts, daten):
    if daten.get("ausschnitt_m"):
        x0, y0, x1, y1 = (_zahl(v) for v in daten["ausschnitt_m"])
        a, b = g.mm(x0, y0), g.mm(x1, y1)
        return min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])
    boxen = []
    if g.vektor and g.vektor.wand_grenzen():
        boxen.append(g.vektor.wand_grenzen())
    for r in g.raeume:
        a0, b0, a1, b1 = r.aussen()
        p, q = g.mm(a0, b0), g.mm(a1, b1)
        boxen.append((min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1])))
    for ge in geraete:
        boxen.append(ge.bbox(m))
    for linie in extra_pts:
        for p in linie:
            boxen.append((p[0], p[1], p[0], p[1]))
    rand = 120.0
    return (min(b[0] for b in boxen) - rand, min(b[1] for b in boxen) - rand,
            max(b[2] for b in boxen) + rand, max(b[3] for b in boxen) + rand)


def _arch_textboxen(g: Grundlage) -> list:
    """Umrisse der Architektentexte (waagrecht/senkrecht), damit Beschriftungen ausweichen."""
    out = []
    if not g.vektor:
        return out
    for x, y, t, h, rot in g.vektor.texte:
        w = _textbreite(t, h)
        r = rot % 360
        if r < 5 or r > 355:
            out.append((x, y - h * 0.25, x + w, y + h))
        elif abs(r - 90) < 5:
            out.append((x - h, y, x + h * 0.25, y + w))
        elif abs(r - 270) < 5:
            out.append((x - h * 0.25, y - w, x + h, y))
    return out


def bemassungsstile(m: float) -> list[str]:
    """Bemaßungsstile EP_M (Meter, 2 Stellen, z. B. 3,19) und EP_MM (mm).
    Zeichnung in mm 1:1, Text 2 mm hoch auf dem Papier, Schrägstriche statt Pfeile."""
    basis = dict(DIMSCALE=m, DIMTXT=2.0, DIMASZ=0, DIMTSZ=1.2, DIMDSEP=",", DIMTXSTY="PLAN",
                 DIMEXO=1.0, DIMEXE=1.5, DIMGAP=0.8, DIMTAD=1)
    return [befehl("dimstyle", name="EP_MM", DIMDEC=0, DIMZIN=8, **basis),
            befehl("dimstyle", name="EP_M", DIMLFAC=0.001, DIMDEC=2, DIMZIN=0, current=True, **basis)]


def _zaehlung(ausgabe: str) -> dict:
    for zeile in reversed(ausgabe.splitlines()):
        if zeile.startswith("{") and '"blocks"' in zeile:
            return json.loads(zeile).get("blocks", {})
    return {}


def erzeuge(daten: dict, ziel: Path, name: str, basis: Path | None = None,
            vorschau: Path | None = None) -> dict:
    """Plan-JSON → <name>.scr/.dxf/.dwg/.pdf (+ Vorschau-PNG). Rückgabe: Pfade und Hinweise."""
    basis = Path(basis or daten.get("_basis", "."))
    hinweise: list[str] = []
    plan, licht = _als_installationsplan(daten)
    hinweise += [f"(Licht) {h}" for h in licht]
    g = Grundlage(plan, basis)
    proj = plan.get("projekt", {})

    # Maßstab: vorgegeben oder kleinster, bei dem alles ins Ansichtsfenster passt
    vp_w, vp_h = VP[2] - VP[0], VP[3] - VP[1]
    m = _zahl(plan.get("massstab")) or _zahl((plan.get("grundriss") or {}).get("massstab")) or 50
    geraete = _geraete(plan, g, m, hinweise)
    lin_cmds, linien_leg, lin_pts = _linien(g, plan, m)
    gx0, gy0, gx1, gy1 = _grenzen_viewport(g, geraete, m, lin_pts, plan)
    if not plan.get("massstab"):
        m = next((s for s in MASSSTAEBE if (gx1 - gx0) / s <= vp_w and (gy1 - gy0) / s <= vp_h),
                 MASSSTAEBE[-1])
        if m != _zahl((plan.get("grundriss") or {}).get("massstab"), m):
            geraete = _geraete(plan, g, m, [])
            lin_cmds, linien_leg, lin_pts = _linien(g, plan, m)
    elif (gx1 - gx0) / m > vp_w or (gy1 - gy0) / m > vp_h:
        hinweise.append(f"(Layout) Grundriss {(gx1 - gx0) / 1000:.1f} × {(gy1 - gy0) / 1000:.1f} m "
                        f"passt bei 1:{m:g} nicht ganz ins Ansichtsfenster – 'massstab' weglassen "
                        f"oder 'ausschnitt_m' angeben")

    # ---------------- Skript 1: Modellbereich
    c = [befehl("new", metric=True), befehl("units", insunits=4)] + grundbefehle()
    c.append(befehl("ltscale", scale=round(m * 0.25, 3)))
    c += bemassungsstile(m)
    if g.vektor:
        c += g.vektor.befehle()
    if g.raeume:
        c += _raeume_befehle(g, plan)
    lin_boxen = [(min(a[0], b[0]) - 20, min(a[1], b[1]) - 20, max(a[0], b[0]) + 20,
                  max(a[1], b[1]) + 20) for linie in lin_pts for a, b in zip(linie, linie[1:])]
    raum_cmds, raum_boxen = _raumtexte(g, plan, m, [ge.bbox(m) for ge in geraete] + lin_boxen)
    c += raum_cmds
    bloecke = OrderedDict()
    for ge in geraete:
        bloecke.setdefault(ge.cs.block, ge.cs)
    for i, cs in enumerate(bloecke.values()):
        c += blockdefinition(cs, i)
    _beschriftungen(geraete, m, g, raum_boxen + _arch_textboxen(g))
    akt = None
    for ge in geraete:
        if ge.cs.layer != akt:
            c.append(befehl("layer.current", name=ge.cs.layer))
            akt = ge.cs.layer
        c.append(befehl("insert", name=ge.cs.block, at=[ge.x, ge.y], scale=m, rotation=ge.rot,
                        attribs=ge.attribute()))
    c += lin_cmds
    c += [befehl("layer.current", name="0"), befehl("count")]
    ziel.mkdir(parents=True, exist_ok=True)
    scr1 = ziel / f"{name} (1 Modell).scr"
    scr1.write_text("\n".join(c) + "\n", encoding="utf-8")
    dxf = ziel / f"{name}.dxf"
    aus = cadcraft("run", "--script-file", scr1, "--save", dxf)
    anzahl = _zaehlung(aus)
    gepatcht = patche_attribute(dxf, geraete)

    # Legende: Stückzahlen aus CADCraft (count), Kontrolle gegen die eigene Zählung
    eigen = OrderedDict()
    for ge in geraete:
        eigen[ge.cs.block] = eigen.get(ge.cs.block, 0) + 1
    for b, n in eigen.items():
        if anzahl.get(b) != n:
            hinweise.append(f"(Zählung) {b}: CADCraft zählt {anzahl.get(b)}, JSON hat {n}")
    eintraege = sorted(((bloecke[b], anzahl.get(b, n)) for b, n in eigen.items()),
                       key=lambda e: (REIHENFOLGE.index(e[0].familie), e[0].name != e[0].sym.name,
                                      e[0].name if e[0].name != e[0].sym.name else e[0].block))

    # ---------------- Skript 2: Layout A3, Schriftfeld, Legende, Ausgabe
    felder = dict(title=_n(plan.get("titel")) or "Installationsplan", kunde=_n(proj.get("kunde")),
                  objekt=_n(proj.get("objekt")), auftrag=_n(proj.get("auftrag")),
                  datum=_n(proj.get("datum")), bearbeiter=_n(proj.get("bearbeiter")) or _firma.bearbeiter(),
                  indexrev=_n(proj.get("revision")) or "A", folio="1/1",
                  anlage=_n(plan.get("anlage")) or f"Maßstab 1:{m:g}",
                  plantyp=_n(plan.get("plantyp")) or "Installationsplan · Symbole nach DIN EN 60617-11")
    pdf, dwg = ziel / f"{name}.pdf", ziel / f"{name}.dwg"
    c2 = [befehl("layout.new", name=LAYOUT, viewport=False),
          befehl("layout.delete", name="Layout1"), befehl("layout.delete", name="Layout2"),
          befehl("pagesetup", layout=LAYOUT, paper="A3", landscape=True, margins=[0, 0, 0, 0]),
          befehl("layout.set", name=LAYOUT),
          befehl("layer.new", name="ELT_ANSICHTSFENSTER", color=8, lineweight=0.13),
          befehl("layer.set", name="ELT_ANSICHTSFENSTER", plot=False),
          befehl("layer.current", name="ELT_RAHMEN"),
          befehl("rectang", p1=list(RAHMEN[:2]), p2=list(RAHMEN[2:]))]
          # Rahmen
    sf, logo_zelle = _schriftfeld(felder)
    c2 += sf + _logo_vektor(logo_zelle)
    c2 += _legende(eintraege, linien_leg.values(), m, felder,
                   ["Am Symbol: Stromkreis, h = Montagehöhe über OKFF in m",
                    "Grundriss maßgenau 1:1 in mm (DXF/DWG)"])
    c2 += [befehl("layer.current", name="ELT_ANSICHTSFENSTER"),
           befehl("mview", p1=list(VP[:2]), p2=list(VP[2:])),
           befehl("select", window=[[VP[0] - 0.5, VP[1] - 0.5], [VP[2] + 0.5, VP[3] + 0.5]]),
           befehl("viewport.set", scale=f"1:{m:g}", center=[round((gx0 + gx1) / 2, 1),
                                                            round((gy0 + gy1) / 2, 1)], locked=True),
           befehl("ai_deselect"),
           befehl("exportpdf", path=str(pdf), layout=LAYOUT, paper="A3", landscape=True),
           # Zum Weiterarbeiten: Modellbereich, Layer ELT_MASSE, Bemaßung in Metern
           befehl("layout.set", name="Model"),
           befehl("layer.current", name="ELT_MASSE"),
           befehl("dimstyle.current", name="EP_M"),
           befehl("zoom", mode="window", p1=[round(gx0, 1), round(gy0, 1)], p2=[round(gx1, 1), round(gy1, 1)]),
           befehl("saveas", path=str(dwg), format="dwg"),
           befehl("saveas", path=str(dxf), format="dxf")]
    scr2 = ziel / f"{name} (2 Layout).scr"
    scr2.write_text("\n".join(c2) + "\n", encoding="utf-8")
    cadcraft("run", dxf, "--script-file", scr2)
    _logo_ins_pdf(pdf, logo_zelle)
    erg = {"dxf": dxf, "dwg": dwg, "pdf": pdf, "skripte": [scr1, scr2], "massstab": m,
           "geraete": len(geraete), "eingerastet": sum(ge.eingerastet for ge in geraete),
           "attribute": gepatcht, "hinweise": hinweise, "anzahl": anzahl}
    if vorschau:
        import fitz
        vorschau.mkdir(parents=True, exist_ok=True)
        png = vorschau / f"{name} Vorschau.png"
        fitz.open(str(pdf))[0].get_pixmap(dpi=110).save(str(png))
        erg["vorschau"] = png
    return erg


def _logo_ins_pdf(pdf: Path, zelle):
    """Eingerichtetes Firmenlogo über die Logo-Zelle legen (nur PDF)."""
    import fitz
    logo = _firma.logo_pfad()
    if not zelle or not logo:
        return
    doc = fitz.open(str(pdf))
    seite = doc[0]
    hoehe = PAPIER["A3"][1]
    k = 72 / 25.4
    ax, ay, bx, by = zelle
    r = fitz.Rect(ax * k + 0.6, (hoehe - by) * k + 0.6, bx * k - 0.6, (hoehe - ay) * k - 0.6)
    seite.draw_rect(r, color=None, fill=(1, 1, 1), overlay=True)
    innen = fitz.Rect(r.x0 + r.width * 0.1, r.y0 + r.height * 0.12,
                      r.x1 - r.width * 0.1, r.y1 - r.height * 0.12)
    seite.insert_image(innen, filename=str(logo), keep_proportion=True, overlay=True)
    tmp = pdf.with_suffix(".tmp.pdf")
    doc.save(str(tmp), garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf)
