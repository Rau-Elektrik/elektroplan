"""Datenmodell der Pläne – unabhängig vom Ausgabeformat.

Alle Koordinaten sind QElectroTech-Szenenkoordinaten in Pixeln (y nach unten).
Im PDF entspricht 1 px genau 0,25 mm (siehe blatt.MM_PRO_PX).
"""
from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field

from reportlab.pdfbase.pdfmetrics import stringWidth

_NS = _uuid.UUID("3b8f6a52-1c4e-4f0a-9d2b-7e5c8a1f2d30")

PX_PRO_PT = 96 / 72          # Qt rechnet Punktgrößen mit 96 dpi in Szenenpixel um
ASCENT = 0.905               # Arial/Helvetica, Anteil der Schriftgröße
ZEILENHOEHE = 1.15           # Zeilenabstand mehrzeiliger Texte
TEXT_RAND = 4.0              # Qt-Dokumentrand um jeden Text in QElectroTech
ORIENT_NUM = {"n": 0, "e": 1, "s": 2, "w": 3}
ORIENT_BUCHST = "nesw"


def det_uuid(*teile) -> str:
    """Reproduzierbare UUID: gleiche Eingabe ergibt gleiche Datei."""
    return "{%s}" % _uuid.uuid5(_NS, "\x1f".join(str(t) for t in teile))


def drehe(x: float, y: float, ori: int) -> tuple[float, float]:
    """Punkt um ori × 90° im Uhrzeigersinn drehen (Bildschirm, y nach unten)."""
    for _ in range(ori % 4):
        x, y = -y, x
    return x, y


def schriftpx(pt: float) -> float:
    return pt * PX_PRO_PT


def textbreite(text: str, pt: float, fett: bool = False) -> float:
    """Breite eines einzeiligen Texts in Szenenpixeln (Arial, sonst Helvetica)."""
    from . import schrift
    return stringWidth(text, schrift.name(fett), schriftpx(pt))


# --------------------------------------------------------------------------
# Symbole (Elementdefinitionen)
# --------------------------------------------------------------------------
@dataclass
class Prim:
    """Grafisches Grundelement einer Symboldefinition (Format wie .elmt)."""
    tag: str                 # line, rect, ellipse, arc, polygon, text
    attrs: dict


@dataclass
class Anschluss:
    name: str
    x: float
    y: float
    ori: str                 # n, e, s, w – Richtung, in die der Leiter abgeht


@dataclass
class DynText:
    """Text am Symbol, der aus einer Bauteil-Information kommt (label, comment …).

    x/y ist die linke obere Ecke des Textfelds inkl. 4 px Qt-Rand, so wie
    QElectroTech es speichert.
    """
    info: str
    x: float
    y: float
    pt: float = 7.0
    rot: float = 0.0
    fett: bool = False


@dataclass
class Symbol:
    key: str
    name: str
    kategorie: str
    prims: list[Prim]
    anschluesse: list[Anschluss] = field(default_factory=list)
    texte: list[DynText] = field(default_factory=list)
    beschreibung: str = ""

    @property
    def uuid(self) -> str:
        return det_uuid("symbol", self.key)

    def anschluss(self, name: str) -> Anschluss:
        for a in self.anschluesse:
            if a.name == name:
                return a
        raise KeyError(f"Symbol {self.key} hat keinen Anschluss {name!r}")

    def anschluss_uuid(self, name: str) -> str:
        return det_uuid("symbol", self.key, "anschluss", name)

    def grenzen(self) -> tuple[float, float, float, float]:
        """Umschließendes Rechteck der Zeichnung (x0, y0, x1, y1)."""
        xs, ys = [], []
        for p in self.prims:
            a = p.attrs
            if p.tag == "line":
                xs += [a["x1"], a["x2"]]
                ys += [a["y1"], a["y2"]]
            elif p.tag in ("rect", "ellipse", "arc"):
                xs += [a["x"], a["x"] + a["width"]]
                ys += [a["y"], a["y"] + a["height"]]
            elif p.tag == "polygon":
                i = 1
                while f"x{i}" in a:
                    xs.append(a[f"x{i}"])
                    ys.append(a[f"y{i}"])
                    i += 1
            elif p.tag == "text":
                w = textbreite(a["text"], a["pt"])
                xs += [a["x"], a["x"] + w]
                ys += [a["y"] - schriftpx(a["pt"]) * ASCENT, a["y"]]
        for t in self.anschluesse:
            xs.append(t.x)
            ys.append(t.y)
        return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------------------
# Inhalt eines Blatts
# --------------------------------------------------------------------------
@dataclass
class Bauteil:
    symbol: Symbol
    x: float
    y: float
    ori: int = 0                         # 0..3 = 0°, 90°, 180°, 270° im Uhrzeigersinn
    info: dict = field(default_factory=dict)   # label, comment, function, …
    uid: str = ""
    texte: list[DynText] | None = None   # abweichende Textpositionen

    def __post_init__(self):
        if not self.uid:
            self.uid = det_uuid("bauteil", self.symbol.key, self.x, self.y, self.ori,
                                tuple(sorted(self.info.items())))

    def pos(self, anschluss: str) -> tuple[float, float]:
        a = self.symbol.anschluss(anschluss)
        dx, dy = drehe(a.x, a.y, self.ori)
        return self.x + dx, self.y + dy

    def richtung(self, anschluss: str) -> str:
        a = self.symbol.anschluss(anschluss)
        return ORIENT_BUCHST[(ORIENT_NUM[a.ori] + self.ori) % 4]

    def dyn_texte(self) -> list[DynText]:
        """Textfelder dieses Bauteils, so dass sie nach der Drehung waagerecht stehen.

        QElectroTech speichert Textposition und -drehung relativ zum Bauteil.
        Wir legen sie so ab, dass der Text auf dem Blatt immer lesbar bleibt.
        """
        basis = self.texte if self.texte is not None else self.symbol.texte
        if self.ori == 0:
            return basis
        # Alle Beschriftungen bilden einen Block: dessen Mittelpunkt dreht mit dem
        # Symbol, Reihenfolge und Abstände der Zeilen bleiben, der Text bleibt waagerecht.
        kaesten = []
        for t in basis:
            wert = str(self.info.get(t.info, ""))
            zeilen = wert.split("\n") if wert else [""]
            s = schriftpx(t.pt)
            w = max(textbreite(z, t.pt, t.fett) for z in zeilen) + 2 * TEXT_RAND
            h = (len(zeilen) - 1) * ZEILENHOEHE * s + (ASCENT + 0.212) * s + 2 * TEXT_RAND
            kaesten.append((t, w, h, bool(wert.strip())))
        sichtbar = [k for k in kaesten if k[3]] or kaesten
        x0 = min(t.x for t, w, h, _ in sichtbar)
        y0 = min(t.y for t, w, h, _ in sichtbar)
        x1 = max(t.x + w for t, w, h, _ in sichtbar)
        y1 = max(t.y + h for t, w, h, _ in sichtbar)
        cx, cy = drehe((x0 + x1) / 2, (y0 + y1) / 2, self.ori)
        dx, dy = cx - (x0 + x1) / 2, cy - (y0 + y1) / 2
        out = []
        for t, w, h, _ in kaesten:
            # gewünschte Lage auf dem Blatt (relativ zum Bauteil) → lokal zurückdrehen
            lx, ly = drehe(t.x + dx, t.y + dy, (4 - self.ori) % 4)
            out.append(DynText(t.info, lx, ly, t.pt, (t.rot - 90 * self.ori) % 360, t.fett))
        return out


@dataclass
class Leitung:
    """Verbindung zwischen zwei Anschlüssen; punkte = kompletter Weg in Szenenkoordinaten."""
    a: Bauteil
    ta: str
    b: Bauteil
    tb: str
    punkte: list[tuple[float, float]]
    phasen: int = 0          # Markierungen der einpoligen Darstellung
    neutral: bool = False
    schutz: bool = False
    farbe: str = "#000000"
    breite: float = 1.0
    stil: str = "SolidLine"  # SolidLine, DashLine, DotLine
    nummer: str = ""

    @property
    def markiert(self) -> bool:
        return bool(self.phasen or self.neutral or self.schutz)

    def mittelsegment(self):
        """Segment, das die Leitungsmitte enthält (wie QElectroTech)."""
        segs = list(zip(self.punkte, self.punkte[1:]))
        laengen = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in segs]
        halb = sum(laengen) / 2
        acc = 0.0
        for (a, b), l in zip(segs, laengen):
            acc += l
            if acc >= halb:
                return a, b
        return segs[-1]


@dataclass
class Text:
    """Freier Text. x/y = linke obere Ecke inkl. 4 px Rand, Drehung um diesen Punkt."""
    x: float
    y: float
    text: str
    pt: float = 7.0
    rot: float = 0.0
    fett: bool = False
    farbe: str = "#000000"

    @property
    def zeilen(self) -> list[str]:
        return self.text.split("\n")


def text_bei(ax: float, ay: float, text: str, pt: float = 7.0, h: str = "links",
             v: str = "oben", rot: float = 0.0, fett: bool = False, farbe: str = "#000000") -> Text:
    """Text so platzieren, dass sein Glyphenkasten am Ankerpunkt ausgerichtet ist.

    h: links/mitte/rechts, v: oben/mitte/unten – bezogen auf die Leserichtung.
    rot: 0 = waagerecht, 270 = von unten nach oben lesbar.
    """
    zeilen = text.split("\n")
    s = schriftpx(pt)
    w = max(textbreite(z, pt, fett) for z in zeilen)
    hgt = (len(zeilen) - 1) * ZEILENHOEHE * s + (ASCENT + 0.212) * s
    ux = {"links": 0.0, "mitte": -w / 2, "rechts": -w}[h]
    uy = {"oben": 0.0, "mitte": -hgt / 2, "unten": -hgt}[v]
    # lokale Koordinate des Textursprungs (inkl. Rand) relativ zum Anker
    lx, ly = ux - TEXT_RAND, uy - TEXT_RAND
    import math
    r = math.radians(rot)
    gx = lx * math.cos(r) - ly * math.sin(r)
    gy = lx * math.sin(r) + ly * math.cos(r)
    return Text(ax + gx, ay + gy, text, pt, rot, fett, farbe)


@dataclass
class Form:
    art: str                       # Line, Rectangle, Ellipse, Polygon
    punkte: list[tuple[float, float]]
    breite: float = 1.0
    farbe: str = "#000000"
    stil: str = "SolidLine"
    fuellung: str | None = None    # Farbe oder None
    geschlossen: bool = True


@dataclass
class Bild:
    png: bytes
    x: float                       # linke obere Ecke
    y: float
    px_b: int                      # Pixelmaße der PNG-Datei
    px_h: int
    skala: float = 1.0             # Szenenpixel je Bildpixel


@dataclass
class Blatt:
    format: "Format"               # aus blatt.py
    titel: str
    felder: dict = field(default_factory=dict)   # Schriftfeld-Variablen
    bauteile: list[Bauteil] = field(default_factory=list)
    leitungen: list[Leitung] = field(default_factory=list)
    texte: list[Text] = field(default_factory=list)
    formen: list[Form] = field(default_factory=list)
    bilder: list[Bild] = field(default_factory=list)
    raster_anzeigen: bool = True   # Spalten-/Zeilenköpfe am Rand

    # Komfortfunktionen für die Layouts --------------------------------------
    def setze(self, symbol: Symbol, x: float, y: float, ori: int = 0, **info) -> Bauteil:
        b = Bauteil(symbol, x, y, ori, {k: v for k, v in info.items() if v not in (None, "")})
        self.bauteile.append(b)
        return b

    def verbinde(self, a: Bauteil, ta: str, b: Bauteil, tb: str, ueber=None, **kw) -> Leitung:
        """Rechtwinklige Verbindung; ueber = Liste von Zwischenpunkten."""
        p1, p2 = a.pos(ta), b.pos(tb)
        pts = [p1] + list(ueber or []) + [p2]
        pts = _rechtwinklig(pts)
        l = Leitung(a, ta, b, tb, pts, **kw)
        self.leitungen.append(l)
        return l

    def text(self, *args, **kw) -> Text:
        t = text_bei(*args, **kw)
        self.texte.append(t)
        return t

    def linie(self, x1, y1, x2, y2, breite=1.0, farbe="#000000", stil="SolidLine"):
        self.formen.append(Form("Line", [(x1, y1), (x2, y2)], breite, farbe, stil))

    def rechteck(self, x, y, w, h, breite=1.0, farbe="#000000", stil="SolidLine", fuellung=None):
        self.formen.append(Form("Rectangle", [(x, y), (x + w, y + h)], breite, farbe, stil, fuellung))

    def polygon(self, punkte, breite=1.0, farbe="#000000", stil="SolidLine", fuellung=None,
                geschlossen=True):
        self.formen.append(Form("Polygon", list(punkte), breite, farbe, stil, fuellung, geschlossen))

    def ellipse(self, x, y, w, h, breite=1.0, farbe="#000000", stil="SolidLine", fuellung=None):
        self.formen.append(Form("Ellipse", [(x, y), (x + w, y + h)], breite, farbe, stil, fuellung))


def _rechtwinklig(pts):
    """Doppelte Punkte entfernen und prüfen, dass nur waagerecht/senkrecht verbunden wird."""
    out = [pts[0]]
    for p in pts[1:]:
        if p == out[-1]:
            continue
        a = out[-1]
        if a[0] != p[0] and a[1] != p[1]:
            raise ValueError(f"Leitung nicht rechtwinklig: {a} → {p}")
        # kollineare Zwischenpunkte zusammenfassen
        if len(out) >= 2:
            z = out[-2]
            if (z[0] == a[0] == p[0]) or (z[1] == a[1] == p[1]):
                if (a[0] - z[0]) * (p[0] - a[0]) >= 0 and (a[1] - z[1]) * (p[1] - a[1]) >= 0:
                    out[-1] = p
                    continue
        out.append(p)
    if len(out) == 1:
        raise ValueError("Leitung ohne Länge")
    return out


@dataclass
class Projekt:
    titel: str
    blaetter: list[Blatt] = field(default_factory=list)
