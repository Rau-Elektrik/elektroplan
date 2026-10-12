"""Installationsplan: Grundriss mit Installationssymbolen nach DIN EN 60617-11.

Grundriss entweder aus Räumen (Innenmaße aus dem Aufmaß) – Wände, Türen und
Fenster werden gezeichnet – oder als Hintergrundbild (PDF/PNG/JPG vom Architekten).
Koordinaten in Metern, Ursprung oben links, x nach rechts, y nach unten.
Geräte an Wänden werden automatisch an die nächste Wand des Raums gesetzt und
zeigen in den Raum. Die Legende zählt alle Geräte.
"""
from __future__ import annotations

import io
import math
from collections import Counter, OrderedDict
from pathlib import Path

from . import firma as _firma
from .blatt import MM_PRO_PX, Format
from .model import (ASCENT, TEXT_RAND, ZEILENHOEHE, Bild, Blatt, DynText, Projekt, drehe,
                    schriftpx, textbreite)
from .symbole import symbol

MASSSTAEBE = [20, 25, 50, 75, 100, 125, 150, 200, 250]
WAND_INNEN = 0.115
WAND_AUSSEN = 0.30
FARBE_WAND = "#B5B5B5"
FARBE_WAND_RAND = "#7A7A7A"
FARBE_RAUMTEXT = "#6E6E6E"
LEGENDE_B = 330
ORI = {"n": 0, "o": 1, "e": 1, "s": 2, "w": 3}
LINIENARTEN = {
    "lichtschiene": {"breite": 3.0, "farbe": "#000000", "stil": "SolidLine"},
    "ledprofil": {"breite": 2.0, "farbe": "#000000", "stil": "DashDotLine"},
    "kanal": {"breite": 2.5, "farbe": "#8B0000", "stil": "DashLine"},
    "leitung": {"breite": 1.0, "farbe": "#000000", "stil": "DashLine"},
    "lichtlinie": {"breite": 3.5, "farbe": "#000000", "stil": "SolidLine"},
    "voute": {"breite": 2.5, "farbe": "#C87800", "stil": "DashLine"},
    "stromschiene": {"breite": 2.0, "farbe": "#000000", "stil": "DashDotLine"},
    "kontur": {"breite": 1.0, "farbe": "#6E6E6E", "stil": "DashLine"},
    "langfeld": {"breite": 2.5, "farbe": "#000000", "stil": "SolidLine"},
    "umriss": {"breite": 0.8, "farbe": "#000000", "stil": "SolidLine"},
}
LINIENNAMEN = {"lichtschiene": "Lichtschiene / Stromschiene", "ledprofil": "LED-Profil",
               "kanal": "Brüstungskanal", "leitung": "Leitungsweg",
               "lichtlinie": "LED-Lichtlinie (Einbauprofil)", "voute": "LED-Lichtvoute (indirekt)",
               "stromschiene": "Stromschiene", "kontur": "Deckensegel / Deckenversprung",
               "langfeld": "Linearleuchte", "umriss": "Leuchtenumriss"}
LINIEN_STUECK = {"langfeld"}       # Linienelemente, die in der Legende als Stückzahl zählen
ENDSTRICH_M = 0.12                 # halbe Länge der Endstriche einer Linearleuchte
WAND_GERAETE = {"steckdose", "schalter", "tv", "daten", "telefon", "fernmelde", "geraet",
                "verteiler", "klingel", "wandleuchte"}


def _n(s) -> str:
    return str(s or "").strip()


def _zahl(v, std=0.0) -> float:
    if v in (None, ""):
        return std
    return float(str(v).replace(",", "."))


def _de(v: float, stellen=2) -> str:
    return f"{v:.{stellen}f}".replace(".", ",")


# --------------------------------------------------------------------------
class Raum:
    def __init__(self, d: dict, std_wand: float):
        self.name = _n(d.get("name"))
        if "polygon" in d:
            raise ValueError("Räume bitte als Rechteck angeben (x, y, b, t); "
                             "L-förmige Räume aus zwei Rechtecken zusammensetzen")
        self.x, self.y = _zahl(d.get("x")), _zahl(d.get("y"))
        self.b, self.t = _zahl(d.get("b") or d.get("breite")), _zahl(d.get("t") or d.get("tiefe"))
        if self.b <= 0 or self.t <= 0:
            raise ValueError(f"Raum {self.name!r}: Breite b und Tiefe t angeben (Meter)")
        w = d.get("wand", std_wand)
        if isinstance(w, dict):
            self.wand = {s: _zahl(w.get(s), std_wand) for s in "nosw"}
        else:
            self.wand = {s: _zahl(w, std_wand) for s in "nosw"}
        # offene Seiten: keine Umrisslinie (für L-förmige Räume aus zwei Rechtecken)
        self.offen = {str(x).lower()[:1].replace("e", "o") for x in (d.get("offen") or [])}
        self.zeige_flaeche = d.get("flaeche", True)
        self.textpos = d.get("textpos")
        self.zusatz = _n(d.get("zusatztext"))      # z. B. Ergebnis der Lichtberechnung

    def aussen(self):
        w = self.wand
        return (self.x - w["w"], self.y - w["n"], self.x + self.b + w["o"], self.y + self.t + w["s"])

    def enthaelt(self, x, y, rand=0.35):
        return (self.x - rand <= x <= self.x + self.b + rand and
                self.y - rand <= y <= self.y + self.t + rand)


class Grundriss:
    """Rechnet Meter in Blattpixel um."""

    def __init__(self, ursprung_px, px_pro_m):
        self.ox, self.oy = ursprung_px
        self.k = px_pro_m

    def p(self, x, y):
        return (round(self.ox + x * self.k, 2), round(self.oy + y * self.k, 2))


def _massstab(breite_m, hoehe_m, w_px, h_px, vorgabe=None):
    if vorgabe:
        return int(vorgabe)
    for m in MASSSTAEBE:
        k = 1000 / m / MM_PRO_PX
        if breite_m * k <= w_px and hoehe_m * k <= h_px:
            return m
    return MASSSTAEBE[-1]


# --------------------------------------------------------------------------
def _hintergrund(gr: dict, basis: Path | None):
    """Grundrissbild laden → (png_bytes, breite_px, hoehe_px, meter_pro_bildpixel)."""
    from PIL import Image
    pfad = Path(_n(gr.get("bild")))
    if not pfad.is_absolute() and basis is not None:
        pfad = basis / pfad
    if not pfad.exists():
        raise FileNotFoundError(f"Grundrissbild nicht gefunden: {pfad}")
    dpi = int(gr.get("dpi", 150))
    if pfad.suffix.lower() == ".pdf":
        import fitz
        with fitz.open(pfad) as doc:
            seite = doc[int(gr.get("seite", 1)) - 1]
            pix = seite.get_pixmap(dpi=dpi)
            im = Image.open(io.BytesIO(pix.tobytes("png")))
    else:
        im = Image.open(pfad)
    if gr.get("ausschnitt"):
        x0, y0, x1, y1 = [int(v) for v in gr["ausschnitt"]]
        im = im.crop((x0, y0, x1, y1))
    im = im.convert("RGB")
    # Grundriss aufhellen, damit die Elektrosymbole hervortreten
    hell = float(gr.get("aufhellen", 0.45))
    if hell:
        weiss = Image.new("RGB", im.size, (255, 255, 255))
        im = Image.blend(im, weiss, hell)
    if gr.get("breite_m"):
        m_pro_px = _zahl(gr["breite_m"]) / im.width
    elif gr.get("massstab"):
        # Bildpixel → mm auf dem Originalplan → Meter in der Wirklichkeit
        m_pro_px = (25.4 / dpi) * _zahl(gr["massstab"]) / 1000
    else:
        raise ValueError("Grundrissbild: 'massstab' (z. B. 100 für 1:100, nur bei PDF) oder "
                         "'breite_m' (wirkliche Breite des Bildes in Metern) angeben")
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue(), im.width, im.height, m_pro_px


# --------------------------------------------------------------------------
def _oeffnung(raum: Raum, d: dict):
    """Lage einer Tür/eines Fensters → (seite, a0, a1, wanddicke) in Metern entlang der Wand."""
    seite = _n(d.get("seite")).lower()[:1]
    seite = {"e": "o"}.get(seite, seite)
    if seite not in "nosw" or not seite:
        raise ValueError(f"Tür/Fenster in {raum.name!r}: 'seite' n, o, s oder w angeben")
    pos = _zahl(d.get("pos"))
    breite = _zahl(d.get("breite"), 0.885 if d.get("_art") == "tuer" else 1.0)
    return seite, pos, pos + breite, raum.wand[seite]


def _wandrechteck(raum: Raum, seite, a0, a1, dicke):
    if seite == "n":
        return raum.x + a0, raum.y - dicke, a1 - a0, dicke
    if seite == "s":
        return raum.x + a0, raum.y + raum.t, a1 - a0, dicke
    if seite == "w":
        return raum.x - dicke, raum.y + a0, dicke, a1 - a0
    return raum.x + raum.b, raum.y + a0, dicke, a1 - a0


def _zeichne_grundriss(bl: Blatt, g: Grundriss, raeume: list[Raum], tueren, fenster):
    # 1) Wände: Raum + Wanddicke grau füllen, 2) Räume weiß darüber
    for r in raeume:
        x0, y0, x1, y1 = r.aussen()
        p0, p1 = g.p(x0, y0), g.p(x1, y1)
        bl.rechteck(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], breite=0.5, farbe=FARBE_WAND,
                    fuellung=FARBE_WAND)
    for r in raeume:
        p0, p1 = g.p(r.x, r.y), g.p(r.x + r.b, r.y + r.t)
        # an offenen Seiten etwas überlappen, damit keine Naht sichtbar bleibt
        u = {s: (1.5 if s in r.offen else 0) for s in "nosw"}
        bl.rechteck(p0[0] - u["w"], p0[1] - u["n"], p1[0] - p0[0] + u["w"] + u["o"],
                    p1[1] - p0[1] + u["n"] + u["s"], breite=0, farbe="#FFFFFF", fuellung="#FFFFFF")
    for r in raeume:
        p0, p1 = g.p(r.x, r.y), g.p(r.x + r.b, r.y + r.t)
        kanten = {"n": (p0[0], p0[1], p1[0], p0[1]), "s": (p0[0], p1[1], p1[0], p1[1]),
                  "w": (p0[0], p0[1], p0[0], p1[1]), "o": (p1[0], p0[1], p1[0], p1[1])}
        for seite, k in kanten.items():
            if seite not in r.offen:
                bl.linie(*k, breite=0.7, farbe=FARBE_WAND_RAND)
    # Fenster: Wand aussparen, drei Linien (Rahmen innen/außen, Glas)
    for r, d in fenster:
        seite, a0, a1, dicke = _oeffnung(r, {**d, "_art": "fenster"})
        x, y, w, h = _wandrechteck(r, seite, a0, a1, dicke)
        p0, p1 = g.p(x, y), g.p(x + w, y + h)
        bl.rechteck(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], breite=0.5, farbe=FARBE_WAND_RAND,
                    fuellung="#FFFFFF")
        if seite in "ns":
            ym = (p0[1] + p1[1]) / 2
            bl.linie(p0[0], ym, p1[0], ym, breite=0.5, farbe=FARBE_WAND_RAND)
        else:
            xm = (p0[0] + p1[0]) / 2
            bl.linie(xm, p0[1], xm, p1[1], breite=0.5, farbe=FARBE_WAND_RAND)
    # Türen: Wand aussparen, Türblatt und Schwenkbogen in den Raum
    for r, d in tueren:
        seite, a0, a1, dicke = _oeffnung(r, {**d, "_art": "tuer"})
        x, y, w, h = _wandrechteck(r, seite, a0, a1, dicke)
        p0, p1 = g.p(x, y), g.p(x + w, y + h)
        bl.rechteck(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], breite=0, farbe="#FFFFFF",
                    fuellung="#FFFFFF")
        breite = a1 - a0
        anschlag_ende = _n(d.get("anschlag")).lower() in ("ende", "rechts", "unten")
        nach_aussen = _n(d.get("aufgehend")).lower() in ("aussen", "außen", "nach_aussen")
        # Drehpunkt auf der Rauminnenseite (bzw. Außenseite der Wand bei nach außen)
        if seite == "n":
            hy = r.y - (dicke if nach_aussen else 0)
            hx = r.x + (a1 if anschlag_ende else a0)
            richt = (0, -1) if nach_aussen else (0, 1)
            entlang = (-1, 0) if anschlag_ende else (1, 0)
        elif seite == "s":
            hy = r.y + r.t + (dicke if nach_aussen else 0)
            hx = r.x + (a1 if anschlag_ende else a0)
            richt = (0, 1) if nach_aussen else (0, -1)
            entlang = (-1, 0) if anschlag_ende else (1, 0)
        elif seite == "w":
            hx = r.x - (dicke if nach_aussen else 0)
            hy = r.y + (a1 if anschlag_ende else a0)
            richt = (-1, 0) if nach_aussen else (1, 0)
            entlang = (0, -1) if anschlag_ende else (0, 1)
        else:
            hx = r.x + r.b + (dicke if nach_aussen else 0)
            hy = r.y + (a1 if anschlag_ende else a0)
            richt = (1, 0) if nach_aussen else (-1, 0)
            entlang = (0, -1) if anschlag_ende else (0, 1)
        blatt_ende = (hx + richt[0] * breite, hy + richt[1] * breite)
        bl.linie(*g.p(hx, hy), *g.p(*blatt_ende), breite=0.8, farbe=FARBE_WAND_RAND)
        pts = []
        for i in range(13):
            phi = math.pi / 2 * i / 12
            vx = richt[0] * math.cos(phi) + entlang[0] * math.sin(phi)
            vy = richt[1] * math.cos(phi) + entlang[1] * math.sin(phi)
            pts.append(g.p(hx + vx * breite, hy + vy * breite))
        bl.polygon(pts, breite=0.4, farbe=FARBE_WAND_RAND, geschlossen=False)

# --------------------------------------------------------------------------
def _belegte_flaechen(bl: Blatt):
    """Umrisse aller gesetzten Symbole und Texte (Szenenpixel)."""
    from .model import drehe
    from .pruefung import textkaesten
    out = [k for _, k in textkaesten(bl)]
    for b in bl.bauteile:
        x0, y0, x1, y1 = b.symbol.grenzen()
        pts = [drehe(px, py, b.ori) for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        out.append((b.x + min(p[0] for p in pts), b.y + min(p[1] for p in pts),
                    b.x + max(p[0] for p in pts), b.y + max(p[1] for p in pts)))
    return out


def _raumnamen(bl: Blatt, g: Grundriss, raeume: list[Raum]):
    """Raumname und Fläche an eine freie Stelle im Raum setzen (Mitte bevorzugt)."""
    from .model import text_bei
    from .pruefung import _kasten, _ueberlappt
    belegt = _belegte_flaechen(bl)
    for r in raeume:
        if not r.name:
            continue
        eigene = r.zeige_flaeche
        flaeche = eigene if isinstance(eigene, (int, float)) and not isinstance(eigene, bool) \
            else r.b * r.t
        txt = r.name + (f"\n{_de(flaeche, 1)} m²" if eigene is not False else "") + \
            (f"\n{r.zusatz}" if r.zusatz else "")
        if r.textpos:
            kandidaten = [(r.x + _zahl(r.textpos[0]), r.y + _zahl(r.textpos[1]))]
        else:
            cx, cy = r.x + r.b / 2, r.y + r.t / 2
            versatz_y = [0, 0.55, -0.55, 0.9, -0.9, 1.3, -1.3]
            versatz_x = [0, 0.8, -0.8, 1.4, -1.4]
            kandidaten = [(cx + a, cy + b) for b in versatz_y for a in versatz_x
                          if r.x + 0.3 < cx + a < r.x + r.b - 0.3
                          and r.y + 0.3 < cy + b < r.y + r.t - 0.3] or [(cx, cy)]
        wahl = kandidaten[0]
        for kx, ky in kandidaten:
            t = text_bei(*g.p(kx, ky), txt, 7, h="mitte", v="mitte")
            box = _kasten(t.x, t.y, t.rot, t.zeilen, t.pt, t.fett)
            box = (box[0] - 4, box[1] - 4, box[2] + 4, box[3] + 4)
            if not any(_ueberlappt(box, b) for b in belegt):
                wahl = (kx, ky)
                break
        bl.text(*g.p(*wahl), txt, 7, h="mitte", v="mitte", farbe=FARBE_RAUMTEXT)


def _symbol_fuer(d: dict):
    art = _n(d.get("symbol")).lower()
    if art in ("steckdose", "sd"):
        return symbol("i_steckdose", anzahl=int(d.get("anzahl", 1)),
                      schutzkontakt=bool(d.get("schutzkontakt", True))), True
    if art == "schalter":
        return symbol("i_schalter", art=_n(d.get("art")) or "aus"), True
    if art == "taster":
        return symbol("i_schalter", art="taster"), True
    if art == "dimmer":
        return symbol("i_schalter", art="dimmer"), True
    if art == "leuchte":
        la = _n(d.get("art")) or "decke"
        return symbol("i_leuchte", art=la), la == "wand"
    if art == "wandleuchte":
        return symbol("i_leuchte", art="wand"), True
    if art in ("spot", "einbauleuchte"):
        return symbol("i_leuchte", art="spot"), False
    if art in ("tv", "sat", "antenne"):
        return symbol("i_fernmelde", text=_n(d.get("text")) or "TV"), True
    if art in ("daten", "lan", "netzwerk"):
        return symbol("i_fernmelde", text=_n(d.get("text")) or "LAN"), True
    if art in ("telefon", "tel"):
        return symbol("i_fernmelde", text="TEL"), True
    if art == "dose":
        return symbol("i_dose", art=_n(d.get("art")) or "abzweig"), False
    if art in ("geraet", "anschluss", "geraeteanschluss"):
        return symbol("i_geraet", text=_n(d.get("text")) or "H"), True
    if art == "verteiler":
        return symbol("i_verteiler"), True
    if art in ("melder", "rauchmelder", "bewegungsmelder", "sensor"):
        std = {"rauchmelder": "RM", "bewegungsmelder": "BWM"}.get(art, "RM")
        return symbol("i_melder", text=_n(d.get("text")) or std), False
    if art == "klingel":
        return symbol("i_klingel"), True
    raise ValueError(f"Unbekanntes Installationssymbol {art!r}")


def _an_wand(raum: Raum, x, y, wand):
    """Gerät auf die Wandinnenseite setzen; ohne Angabe die nächste Wand nehmen."""
    abst = {"n": abs(y - raum.y), "s": abs(raum.y + raum.t - y),
            "w": abs(x - raum.x), "o": abs(raum.x + raum.b - x)}
    w = (wand or min(abst, key=abst.get)).lower()[:1]
    w = {"e": "o"}.get(w, w)
    if w == "n":
        y = raum.y
    elif w == "s":
        y = raum.y + raum.t
    elif w == "w":
        x = raum.x
    elif w == "o":
        x = raum.x + raum.b
    x = min(max(x, raum.x), raum.x + raum.b)
    y = min(max(y, raum.y), raum.y + raum.t)
    return x, y, ORI[w]


def _beschriftung(d: dict) -> dict:
    label = _n(d.get("stromkreis") or d.get("bmk"))
    teile = []
    if d.get("hoehe") not in (None, ""):
        teile.append(f"h={_de(_zahl(d['hoehe']))}")
    if _n(d.get("text2") or d.get("bemerkung")):
        teile.append(_n(d.get("text2") or d.get("bemerkung")))
    return {"label": label, "comment": " ".join(teile)}


def _legende(bl: Blatt, x0, y0, breite, eintraege, massstab, linien=()):
    """Legende mit Symbol, Bezeichnung und Anzahl; darunter Maßstab und Hinweise.
    linien: (stil, name, länge_m) für Linienelemente (Lichtschiene, Kanal …)."""
    bl.text(x0, y0, "Legende", 9, fett=True)
    y = y0 + 22
    bl.linie(x0, y - 4, x0 + breite, y - 4, breite=0.8)
    for sym, name, anzahl in eintraege:
        bl.setze(sym, x0 + 20, y + 6 - _ankerversatz(sym), 0)
        bl.text(x0 + 52, y + 10, name, 6.5, v="mitte")
        bl.text(x0 + breite, y + 10, f"{anzahl}×", 6.5, h="rechts", v="mitte")
        y += 34
    for stil, name, laenge, stueck in linien:
        bl.linie(x0 + 4, y + 10, x0 + 38, y + 10, **stil)
        if stueck is not None:
            for xe in (x0 + 4, x0 + 38):
                bl.linie(xe, y + 5, xe, y + 15, breite=stil.get("breite", 1.0) * 0.6,
                         farbe=stil.get("farbe", "#000000"))
        bl.text(x0 + 52, y + 10, name, 6.5, v="mitte")
        wert = f"{stueck}×" if stueck is not None else f"ca. {_de(laenge, 1)} m"
        bl.text(x0 + breite, y + 10, wert, 6.5, h="rechts", v="mitte")
        y += 26
    bl.linie(x0, y - 4, x0 + breite, y - 4, breite=0.5)
    bl.text(x0, y + 4, "Beschriftung am Symbol: Stromkreis (z. B. F3), h = Montagehöhe "
                       "über OKFF in m", 5.5)
    return y + 20


def _texte_seitlich(b):
    """An senkrechten Wänden (ori 1/3) die Beschriftung neben das Symbol in den Raum
    legen, mittig auf Symbolhöhe – sonst landet sie auf dem Symbol darunter."""
    if b.ori not in (1, 3):
        return
    basis = b.symbol.texte
    kaesten = []
    for t in basis:
        wert = str(b.info.get(t.info, ""))
        if not wert.strip():
            continue
        zeilen = wert.split("\n")
        s = schriftpx(t.pt)
        w = max(textbreite(z, t.pt, t.fett) for z in zeilen) + 2 * TEXT_RAND
        h = (len(zeilen) - 1) * ZEILENHOEHE * s + (ASCENT + 0.212) * s + 2 * TEXT_RAND
        kaesten.append((t, w, h))
    if not kaesten:
        return
    x0 = min(t.x for t, w, h in kaesten)
    y0 = min(t.y for t, w, h in kaesten)
    x1 = max(t.x + w for t, w, h in kaesten)
    y1 = max(t.y + h for t, w, h in kaesten)
    gx0, gy0, gx1, gy1 = b.symbol.grenzen()
    tiefe = max(gy1, 26) + 2          # wie weit das Symbol (inkl. Ziffer) in den Raum ragt
    bw = x1 - x0
    fx = -(tiefe + bw / 2) if b.ori == 1 else tiefe + bw / 2
    cx, cy = drehe(fx, 0, (4 - b.ori) % 4)
    dx, dy = cx - (x0 + x1) / 2, cy - (y0 + y1) / 2
    b.texte = [DynText(t.info, t.x + dx, t.y + dy, t.pt, t.rot, t.fett) for t in basis]


def _ankerversatz(sym) -> float:
    """Symbole mit Ursprung auf der Wand in der Legende mittig setzen."""
    x0, y0, x1, y1 = sym.grenzen()
    return (y0 + y1) / 2


def _massstabsbalken(bl: Blatt, x0, y0, px_pro_m, massstab):
    schritte = 5
    meter = 0.25
    for m in (0.5, 1, 2, 5, 10, 20):
        if schritte * m * px_pro_m <= 300:
            meter = m
    for i in range(schritte):
        xa = x0 + i * meter * px_pro_m
        bl.rechteck(xa, y0, meter * px_pro_m, 5, breite=0.5,
                    fuellung="#000000" if i % 2 == 0 else "#FFFFFF")
        bl.text(xa, y0 + 7, f"{i * meter:g}".replace(".", ","), 5.5, h="mitte")
    bl.text(x0 + schritte * meter * px_pro_m, y0 + 7,
            f"{schritte * meter:g} m".replace(".", ","), 5.5, h="mitte")
    bl.text(x0, y0 - 4, f"Maßstab 1:{massstab} (bei Druck in Originalgröße)", 6.5, v="unten")


# --------------------------------------------------------------------------
def baue(daten: dict, fmt: Format, basis: Path | None = None) -> Projekt:
    proj = daten.get("projekt", {})
    titel = _n(daten.get("titel")) or "Installationsplan"
    gr = daten.get("grundriss", {}) or {}
    std_wand = _zahl(gr.get("wanddicke"), WAND_INNEN)
    raeume = [Raum(r, std_wand) for r in gr.get("raeume", [])]
    bild = None
    if gr.get("bild"):
        bild = _hintergrund(gr, basis or Path(daten.get("_basis", ".")))
    if not raeume and not bild:
        raise ValueError("Grundriss fehlt: 'raeume' (Innenmaße) oder 'bild' angeben")

    # Ausdehnung in Metern
    xs, ys = [], []
    for r in raeume:
        a = r.aussen()
        xs += [a[0], a[2]]
        ys += [a[1], a[3]]
    if bild:
        png, bw, bh, m_px = bild
        bx, by = (_zahl(v) for v in gr.get("versatz", [0, 0]))
        xs += [bx, bx + bw * m_px]
        ys += [by, by + bh * m_px]
    mx0, my0, mx1, my1 = min(xs), min(ys), max(xs), max(ys)

    bl = Blatt(fmt, titel, raster_anzeigen=False)
    fx, fy, fw, fh = fmt.zeichenflaeche(False)
    rand = 25
    plan_w = fw - LEGENDE_B - 3 * rand
    plan_h = fh - 2 * rand - 40
    massstab = _massstab(mx1 - mx0, my1 - my0, plan_w, plan_h, daten.get("massstab"))
    k = 1000 / massstab / MM_PRO_PX
    ox = fx + rand + (plan_w - (mx1 - mx0) * k) / 2 - mx0 * k
    oy = fy + rand + (plan_h - (my1 - my0) * k) / 2 - my0 * k
    g = Grundriss((ox, oy), k)

    if bild:
        png, bw, bh, m_px = bild
        bx, by = (_zahl(v) for v in gr.get("versatz", [0, 0]))
        px0 = g.p(bx, by)
        bl.bilder.append(Bild(png, px0[0], px0[1], bw, bh, skala=m_px * k))

    rname = {r.name.lower(): r for r in raeume if r.name}
    tueren, fenster = [], []
    for d in gr.get("tueren", []):
        tueren.append((rname[_n(d.get("raum")).lower()], d))
    for d in gr.get("fenster", []):
        fenster.append((rname[_n(d.get("raum")).lower()], d))
    if raeume:
        _zeichne_grundriss(bl, g, raeume, tueren, fenster)

    # Geräte
    zaehlung: "OrderedDict[str, list]" = OrderedDict()
    for d in daten.get("geraete", []):
        sym, an_wand = _symbol_fuer(d)
        x, y = _zahl(d.get("x")), _zahl(d.get("y"))
        raum = None
        if _n(d.get("raum")):
            raum = rname.get(_n(d.get("raum")).lower())
            if raum is None:
                raise ValueError(f"Gerät {d}: Raum {d.get('raum')!r} gibt es nicht")
            x, y = raum.x + x, raum.y + y
        else:
            raum = next((r for r in raeume if r.enthaelt(x, y)), None)
        ori = ORI.get(_n(d.get("wand")).lower()[:1], 0) if d.get("wand") else 0
        if an_wand and raum is not None and _n(d.get("wand")).lower() != "frei":
            x, y, ori = _an_wand(raum, x, y, _n(d.get("wand")) or None)
        px, py = g.p(x, y)
        _texte_seitlich(bl.setze(sym, px, py, ori, **_beschriftung(d)))
        leg = _n(d.get("legende"))       # eigener Legendentext (z. B. Leuchtentyp im Deckenspiegel)
        eintrag = zaehlung.setdefault((sym.key, leg), [sym, leg or sym.name, 0])
        eintrag[2] += 1

    # Dusche/Wanne (für die Bereiche nach VDE 0100-701): Umriss gestrichelt, Name in der Mitte
    for s in gr.get("sanitaer", []) or []:
        r = rname.get(_n(s.get("raum")).lower())
        if r is None:
            raise ValueError(f"Sanitärobjekt {s}: Raum {s.get('raum')!r} gibt es nicht")
        sx, sy = r.x + _zahl(s.get("x")), r.y + _zahl(s.get("y"))
        sb, st = _zahl(s.get("b"), 0.9), _zahl(s.get("t"), 0.9)
        ecken = [(sx, sy), (sx + sb, sy), (sx + sb, sy + st), (sx, sy + st), (sx, sy)]
        for (xa, ya), (xb, yb) in zip(ecken, ecken[1:]):
            bl.linie(*g.p(xa, ya), *g.p(xb, yb), breite=0.8, farbe=FARBE_RAUMTEXT, stil="DashLine")
        bl.text(*g.p(sx + sb / 2, sy + st / 2), _n(s.get("art")).capitalize() or "Dusche", 6,
                h="mitte", v="mitte", farbe=FARBE_RAUMTEXT)

    _raumnamen(bl, g, raeume)

    # Linienelemente (Lichtschiene, LED-Profil, Brüstungskanal …) und freie Texte
    linien_leg: "OrderedDict[tuple, list]" = OrderedDict()
    for d in daten.get("linien", []):
        art = _n(d.get("art")).lower() or "lichtschiene"
        stil = dict(LINIENARTEN.get(art, LINIENARTEN["lichtschiene"]))
        if d.get("farbe"):
            stil["farbe"] = d["farbe"]
        if d.get("mitte"):            # Alternative: Mitte, Winkel (Grad, im Uhrzeigersinn), Länge
            mx, my = (_zahl(v) for v in d["mitte"])
            w = math.radians(_zahl(d.get("winkel")))
            h = _zahl(d.get("laenge"), 1.0) / 2
            pts = [(mx - h * math.cos(w), my - h * math.sin(w)),
                   (mx + h * math.cos(w), my + h * math.sin(w))]
        else:
            pts = [(_zahl(p[0]), _zahl(p[1])) for p in d.get("punkte", [])]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            bl.linie(*g.p(xa, ya), *g.p(xb, yb), **stil)
        stueck = art in LINIEN_STUECK
        if stueck and len(pts) >= 2:  # Endstriche quer zur Leuchte
            for (xa, ya), (xb, yb) in ((pts[0], pts[1]), (pts[-1], pts[-2])):
                lx, ly = xb - xa, yb - ya
                n = math.hypot(lx, ly) or 1
                qx, qy = -ly / n * ENDSTRICH_M, lx / n * ENDSTRICH_M
                bl.linie(*g.p(xa - qx, ya - qy), *g.p(xa + qx, ya + qy),
                         breite=stil["breite"] * 0.6, farbe=stil["farbe"])
        laenge = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        if d.get("legende") is False:
            continue
        name = _n(d.get("name")) or LINIENNAMEN.get(art, art)
        e = linien_leg.setdefault((name, tuple(sorted(stil.items()))),
                                  [stil, name, 0.0, 0 if stueck else None])
        e[2] += laenge
        if stueck:
            e[3] += 1
        if _n(d.get("text") or d.get("stromkreis")) and pts:
            tx, ty = d.get("textpos") or pts[0]
            bl.text(*g.p(_zahl(tx), _zahl(ty)), _n(d.get("text") or d.get("stromkreis")), 6,
                    farbe=stil.get("farbe", "#000000"))
    for d in daten.get("texte", []):
        bl.text(*g.p(_zahl(d.get("x")), _zahl(d.get("y"))), _n(d.get("text")),
                float(d.get("groesse", 8)), fett=bool(d.get("fett", True)), h=_n(d.get("h")) or "mitte",
                v=_n(d.get("v")) or "mitte",
                farbe=_n(d.get("farbe")) or FARBE_RAUMTEXT)

    # Legende rechts
    lx = fx + fw - LEGENDE_B - rand
    reihenfolge = ["i_verteiler", "i_steckdose", "i_geraet", "i_fernmelde", "i_schalter",
                   "i_leuchte", "i_dose", "i_melder", "i_klingel"]
    def sortierung(e):
        key = e[0].key
        gruppe = next((i for i, r in enumerate(reihenfolge) if key.startswith(r)), 99)
        return (gruppe, key, e[1])
    y_ende = _legende(bl, lx, fy + rand, LEGENDE_B, sorted(zaehlung.values(), key=sortierung),
                      massstab, list(linien_leg.values()))
    _massstabsbalken(bl, lx, max(y_ende + 40, fy + fh - 70), k, massstab)

    felder = dict(kunde=_n(proj.get("kunde")), objekt=_n(proj.get("objekt")),
                  auftrag=_n(proj.get("auftrag")), datum=_n(proj.get("datum")),
                  bearbeiter=_n(proj.get("bearbeiter")) or _firma.bearbeiter(),
                  indexrev=_n(proj.get("revision")) or "A",
                  anlage=_n(daten.get("anlage")) or f"Maßstab 1:{massstab}",
                  plantyp=_n(daten.get("plantyp")) or "Installationsplan · Symbole nach DIN EN 60617-11")
    bl.felder = felder
    return Projekt(titel, [bl])
