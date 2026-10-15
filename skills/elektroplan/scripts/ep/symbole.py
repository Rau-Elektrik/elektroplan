"""Symbolsatz nach DIN EN 60617, gezeichnet im QElectroTech-Elementformat.

Raster 10 px, 1 px = 0,25 mm. Senkrechte Geräte haben Anschluss "1" oben bei
(0, -30) und "2" unten bei (0, 30). Installationssymbole für Grundrisse haben
keine Anschlüsse; ihr Ursprung (0, 0) liegt auf der Wand, das Symbol ragt in
+y-Richtung in den Raum.

Symbole mit Parametern (Klemmennummern, Beschriftung im Kasten …) werden bei
Bedarf erzeugt: symbol("kasten", text="SST").
"""
from __future__ import annotations

import math

from .model import Anschluss, DynText, Prim, Symbol

# --------------------------------------------------------------------------
# Grundelemente
# --------------------------------------------------------------------------


def _stil(ls="normal", lw="normal", fill="none"):
    return f"line-style:{ls};line-weight:{lw};filling:{fill};color:black"


def L(x1, y1, x2, y2, ls="normal", lw="normal"):
    return Prim("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, end1="none", end2="none",
                             length1=1.5, length2=1.5, style=_stil(ls, lw), antialias="false"))


def R(x, y, w, h, fill="none", lw="normal", ls="normal"):
    return Prim("rect", dict(x=x, y=y, width=w, height=h, rx=0, ry=0,
                             style=_stil(ls, lw, fill), antialias="false"))


def K(cx, cy, r, fill="none", lw="normal"):
    return Prim("ellipse", dict(x=cx - r, y=cy - r, width=2 * r, height=2 * r,
                                style=_stil("normal", lw, fill), antialias="true"))


def E(x, y, w, h, fill="none", ls="normal"):
    return Prim("ellipse", dict(x=x, y=y, width=w, height=h, style=_stil(ls, "normal", fill),
                                antialias="true"))


def B(x, y, w, h, start, winkel):
    """Kreisbogen wie Qt: Winkel in Grad, 0 = rechts, positiv = gegen den Uhrzeigersinn."""
    return Prim("arc", dict(x=x, y=y, width=w, height=h, start=start, angle=winkel,
                            style=_stil(), antialias="true"))


def P(*pts, closed=True, fill="none"):
    a = {}
    for i, (x, y) in enumerate(pts, 1):
        a[f"x{i}"] = x
        a[f"y{i}"] = y
    a["closed"] = "true" if closed else "false"
    a["style"] = _stil(fill=fill)
    a["antialias"] = "true"
    return Prim("polygon", a)


def T(x, y, text, pt=5.0):
    """Fester Text, x/y = Grundlinie links."""
    return Prim("text", dict(x=x, y=y, text=text, pt=pt))


def T_mitte(cx, cy, text, pt=6.0):
    """Fester Text, auf (cx, cy) zentriert."""
    from .model import ASCENT, schriftpx, textbreite
    w = textbreite(text, pt)
    s = schriftpx(pt)
    return T(cx - w / 2, cy + ASCENT * s / 2 - 0.5, text, pt)


# Beschriftung rechts neben senkrechten Geräten
TXT_RECHTS = [DynText("label", 8, -26, 7.0, fett=True), DynText("comment", 8, -13, 6.0),
              DynText("function", 8, -1, 6.0)]


def _auf_ab():
    return [Anschluss("1", 0, -30, "n"), Anschluss("2", 0, 30, "s")]


# Bausteine für Kontakte: Festkontakt endet bei y=-10, Drehpunkt bei y=10
def _messer(nach_rechts=False):
    return L(0, 10, 8 if nach_rechts else -8, -13)


def _zuleitungen():
    return [L(0, -30, 0, -10), L(0, 10, 0, 30)]


def _kreuz(y=-10):
    return [L(-3, y - 3, 3, y + 3), L(3, y - 3, -3, y + 3)]


def _antrieb(art: str, x_messer=-4, y=-1, x_ende=-20):
    """Betätigung links vom Kontakt: hand ├, druck [, keine."""
    if art == "keine":
        return []
    out = [L(x_messer, y, x_ende, y, ls="dashed")]
    out.append(L(x_ende, y - 5, x_ende, y + 5))
    if art == "druck":
        out += [L(x_ende, y - 5, x_ende + 3, y - 5), L(x_ende, y + 5, x_ende + 3, y + 5)]
    return out


def _nummern(oben, unten, x=3):
    out = []
    if oben:
        out.append(T(x, -22, oben))
    if unten:
        out.append(T(x, 27, unten))
    return out


# --------------------------------------------------------------------------
# Symbolfabriken
# --------------------------------------------------------------------------
_CACHE: dict[str, Symbol] = {}


def _reg(s: Symbol) -> Symbol:
    _CACHE[s.key] = s
    return s


def _ls(**_):
    return Symbol("ls", "Leitungsschutzschalter (LS)", "Schutzgeräte",
                  _zuleitungen() + [_messer()] + _kreuz(), _auf_ab(), TXT_RECHTS,
                  "Leistungsschalter-Funktion, einpolige Darstellung")


def _fi_teile(mit_kreuz: bool):
    teile = _zuleitungen() + [_messer()]
    if mit_kreuz:
        teile += _kreuz()
    # Summenstromwandler um die Leitung, mechanische Wirkverbindung zum Schaltmesser
    teile += [E(-7, 17, 14, 6), L(-7, 20, -14, 20, ls="dashed"), L(-14, 20, -14, -2, ls="dashed"),
              L(-14, -2, -5, -2, ls="dashed")]
    return teile


def _fi(**_):
    return Symbol("fi", "Fehlerstrom-Schutzschalter (FI/RCD)", "Schutzgeräte",
                  _fi_teile(False), _auf_ab(), TXT_RECHTS)


def _fils(**_):
    return Symbol("fils", "FI/LS-Schalter (RCBO)", "Schutzgeräte", _fi_teile(True), _auf_ab(),
                  TXT_RECHTS)


def _hauptschalter(**_):
    teile = [L(0, -30, 0, -14), K(0, -12, 2), L(-3, -14, 3, -14), _messer(), L(0, 10, 0, 30)]
    return Symbol("hauptschalter", "Hauptschalter (Lasttrennschalter)", "Schutzgeräte", teile,
                  _auf_ab(), TXT_RECHTS)


def _trenner(**_):
    teile = [L(0, -30, 0, -10), L(-3, -10, 3, -10), _messer(), L(0, 10, 0, 30)]
    return Symbol("trenner", "Trennschalter", "Schutzgeräte", teile, _auf_ab(), TXT_RECHTS)


def _sicherung(**_):
    return Symbol("sicherung", "Sicherung (Schmelzsicherung)", "Schutzgeräte",
                  [R(-5, -15, 10, 30), L(0, -30, 0, 30)], _auf_ab(), TXT_RECHTS)


def _spd(**_):
    teile = [L(0, -30, 0, -5), P((-2.5, -8), (2.5, -8), (0, -2), fill="black"), R(-5, -10, 10, 20),
             L(0, 10, 0, 30)]
    return Symbol("spd", "Überspannungsschutz (SPD)", "Schutzgeräte", teile, _auf_ab(), TXT_RECHTS)


def _erde(**_):
    teile = [L(0, -10, 0, 0), L(-8, 0, 8, 0), L(-5, 3, 5, 3), L(-2, 6, 2, 6)]
    return Symbol("erde", "Erde / Schutzleiteranschluss", "Allgemein", teile,
                  [Anschluss("1", 0, -10, "n")], [DynText("label", 9, -6, 6.0)])


def _klemme(**_):
    teile = [L(0, -10, 0, -2.5), K(0, 0, 2.5), L(0, 2.5, 0, 10)]
    return Symbol("klemme", "Klemme", "Allgemein", teile,
                  [Anschluss("1", 0, -10, "n"), Anschluss("2", 0, 10, "s")],
                  [DynText("label", 4, -10, 6.0)])


def _knoten(**_):
    """Unsichtbarer Durchgangspunkt (z. B. N an einem 3-poligen Hauptschalter vorbei)."""
    return Symbol("knoten", "Leitungspunkt", "Allgemein", [L(0, 0, 0, 0)],
                  [Anschluss("1", 0, 0, "s"), Anschluss("2", 0, 0, "n")], [])


def _abgang(**_):
    teile = [L(0, -10, 0, -3), K(0, 0, 3)]
    return Symbol("abgang", "Abgang / Anschlusspunkt", "Allgemein", teile,
                  [Anschluss("1", 0, -10, "n")], [DynText("label", 4, -2, 6.0)])


def _einspeisung(**_):
    teile = [K(0, 0, 3), L(0, 3, 0, 10)]
    return Symbol("einspeisung", "Einspeisung / Zuleitung", "Allgemein", teile,
                  [Anschluss("1", 0, 10, "s")], [DynText("label", 6, -14, 7.0, fett=True)])


def _zaehler(**_):
    teile = [L(0, -30, 0, -15), R(-15, -15, 30, 30), T_mitte(0, 0, "kWh", 6), L(0, 15, 0, 30)]
    return Symbol("zaehler", "Zähler (kWh)", "Allgemein", teile, _auf_ab(),
                  [DynText("label", 18, -26, 7.0, fett=True), DynText("comment", 18, -13, 6.0)])


def _kasten(text="", breite=30, **_):
    """Gerät als Kasten mit Kurztext (Stromstoßschalter, Treppenlicht, Dimmer …)."""
    from .model import textbreite
    b = max(breite, int(math.ceil((textbreite(text, 6) + 8) / 10.0)) * 10)
    teile = [L(0, -30, 0, -15), R(-b / 2, -15, b, 30), L(0, 15, 0, 30)]
    if text:
        teile.append(T_mitte(0, 0, text, 6))
    key = f"kasten_{text}_{b}" if text else f"kasten_{b}"
    return Symbol(key, f"Gerät {text}".strip(), "Allgemein", teile, _auf_ab(),
                  [DynText("label", b / 2 + 3, -26, 7.0, fett=True),
                   DynText("comment", b / 2 + 3, -13, 6.0)])


def _kasten_n(text="", breite=40, **_):
    """Gerät mit zusätzlichem N-Anschluss rechts (z. B. Bewegungsmelder, Dimmer mit N)."""
    from .model import textbreite
    b = max(breite, int(math.ceil((textbreite(text, 6) + 8) / 10.0)) * 10)
    teile = [L(0, -30, 0, -15), R(-b / 2, -15, b, 30), L(0, 15, 0, 30),
             L(b / 2, 0, b / 2 + 10, 0), T(b / 2 + 2, -2, "N")]
    if text:
        teile.append(T_mitte(0, 0, text, 6))
    return Symbol(f"kastenn_{text}_{b}", f"Gerät {text} mit N".strip(), "Allgemein", teile,
                  _auf_ab() + [Anschluss("N", b / 2 + 10, 0, "e")],
                  [DynText("label", b / 2 + 3, -30, 7.0, fett=True),
                   DynText("comment", -b / 2 - 4, 16, 6.0)])


# ---- Kontakte (allpolig) ---------------------------------------------------
def _schliesser(oben="", unten="", antrieb="keine", **_):
    teile = _zuleitungen() + [_messer()] + _antrieb(antrieb) + _nummern(oben, unten)
    name = {"keine": "Schließer", "hand": "Schalter (Schließer, handbetätigt)",
            "druck": "Taster (Schließer)"}[antrieb]
    return Symbol(f"schliesser_{antrieb}_{oben}_{unten}", name, "Kontakte", teile, _auf_ab(),
                  TXT_RECHTS)


def _oeffner(oben="", unten="", antrieb="keine", **_):
    teile = _zuleitungen() + [L(0, -10, 10, -10), _messer(nach_rechts=True)]
    if antrieb == "thermisch":      # Hilfskontakt Überlastrelais: Wirklinie zum Bimetall
        teile += [L(2, -1, -16, -1, ls="dashed"), L(-16, -1, -16, -5), L(-16, -5, -21, -5),
                  L(-21, -5, -21, 3), L(-21, 3, -26, 3)]
    elif antrieb != "keine":
        teile += _antrieb(antrieb, x_messer=-0, y=-1, x_ende=-20)
    teile += _nummern(oben, unten, x=-12)
    name = {"keine": "Öffner", "hand": "Schalter (Öffner, handbetätigt)",
            "druck": "Taster (Öffner)", "thermisch": "Öffner Überlastrelais"}[antrieb]
    return Symbol(f"oeffner_{antrieb}_{oben}_{unten}", name, "Kontakte", teile, _auf_ab(),
                  [DynText("label", 14, -26, 7.0, fett=True), DynText("comment", 14, -13, 6.0)])


def _wechsler(nc="", no="", com="", antrieb="keine", oben=False, nc_rechts=False, **_):
    """Wechsler. Grundform: gemeinsamer Anschluss "c" unten, Öffnerseite "nc" oben links
    (x=-20), Schließerseite "no" oben (x=0); das Messer liegt am Öffnerkontakt an.
    oben=True: gemeinsamer Anschluss oben. nc_rechts=True: Öffnerseite rechts (x=+20)."""
    sx, sy = (-1 if nc_rechts else 1), (-1 if oben else 1)
    basis = [(0, 10, 0, 30), (0, -30, 0, -10), (-20, -30, -20, -10), (-20, -10, -5, -10),
             (0, 10, -8, -13)]
    teile = [L(sx * a, sy * b, sx * c, sy * d) for a, b, c, d in basis]
    if antrieb != "keine":
        ym = -1 * sy
        xm = -4 * sx
        xe = -30 if not nc_rechts else -20
        teile += [L(xm, ym, xe, ym, ls="dashed"), L(xe, ym - 5, xe, ym + 5)]
        if antrieb == "druck":
            teile += [L(xe, ym - 5, xe + 3, ym - 5), L(xe, ym + 5, xe + 3, ym + 5)]
    if nc:
        teile.append(T(-20 * sx + 3, -22 * sy + (5 if oben else 0), nc))
    if no:
        teile.append(T(3, -22 * sy + (5 if oben else 0), no))
    if com:
        teile.append(T(3, 27 * sy + (5 if oben else 0), com))
    name = {"keine": "Wechsler", "hand": "Wechselschalter", "druck": "Taster (Wechsler)"}[antrieb]
    ri = {"n": "s", "s": "n"}
    o = (lambda r: ri[r]) if oben else (lambda r: r)
    texte = TXT_RECHTS if not (nc_rechts and not oben) else [
        DynText("label", 26, -26, 7.0, fett=True), DynText("comment", 26, -13, 6.0)]
    return Symbol(f"wechsler_{antrieb}_{nc}_{no}_{com}_{int(oben)}{int(nc_rechts)}", name,
                  "Kontakte", teile,
                  [Anschluss("c", 0, 30 * sy, o("s")), Anschluss("nc", -20 * sx, -30 * sy, o("n")),
                   Anschluss("no", 0, -30 * sy, o("n"))], texte)


def _kreuzschalter(**_):
    """Kreuzschalter (aufgelöst): Eingänge a/b oben, Ausgänge c/d unten, Abstand 20 px.
    Ruhestellung a–c und b–d, betätigt a–d und b–c (gestrichelt)."""
    teile = [
        L(0, -30, 0, -14), L(20, -30, 20, -14), L(0, 14, 0, 30), L(20, 14, 20, 30),
        K(0, -12, 2), K(20, -12, 2), K(0, 12, 2), K(20, 12, 2),
        L(0, -10, 0, 10), L(20, -10, 20, 10),                     # Ruhestellung
        L(1.5, -10.5, 18.5, 10.5, ls="dashed"), L(18.5, -10.5, 1.5, 10.5, ls="dashed"),
        L(-4, 0, -16, 0, ls="dashed"), L(-16, -5, -16, 5),         # Handbetätigung
    ]
    return Symbol("kreuzschalter", "Kreuzschalter", "Kontakte", teile,
                  [Anschluss("a", 0, -30, "n"), Anschluss("b", 20, -30, "n"),
                   Anschluss("c", 0, 30, "s"), Anschluss("d", 20, 30, "s")],
                  [DynText("label", 26, -26, 7.0, fett=True), DynText("comment", 26, -13, 6.0)])


def _serienschalter(**_):
    """Serienschalter: Zuleitung L oben, Ausgänge 1 (x=0) und 2 (x=30) unten."""
    teile = [L(0, -30, 0, -10), L(0, -20, 30, -20), L(30, -20, 30, -10),
             L(0, 10, 0, 30), L(30, 10, 30, 30), L(0, 10, -8, -13), L(30, 10, 22, -13),
             L(-4, -1, -16, -1, ls="dashed"), L(-16, -6, -16, 4),
             L(26, -1, 40, -1, ls="dashed"), L(40, -6, 40, 4)]
    return Symbol("serienschalter", "Serienschalter", "Kontakte", teile,
                  [Anschluss("L", 0, -30, "n"), Anschluss("1", 0, 30, "s"),
                   Anschluss("2", 30, 30, "s")],
                  [DynText("label", 44, -26, 7.0, fett=True), DynText("comment", 44, -13, 6.0)])


def _ls3(**_):
    """Dreipoliger Leitungsschutzschalter (allpolige Darstellung), Pole bei x = 0, 20, 40."""
    teile = []
    for x in (0, 20, 40):
        teile += [L(x, -30, x, -10), L(x, 10, x, 30), L(x, 10, x - 8, -13),
                  L(x - 3, -13, x + 3, -7), L(x + 3, -13, x - 3, -7)]
    teile.append(L(-4, -1, 36, -1, ls="dashed"))
    ans = []
    for i, x in enumerate((0, 20, 40)):
        ans += [Anschluss(str(2 * i + 1), x, -30, "n"), Anschluss(str(2 * i + 2), x, 30, "s")]
    return Symbol("ls3", "Leitungsschutzschalter 3-polig", "Schutzgeräte", teile, ans,
                  [DynText("label", 48, -26, 7.0, fett=True), DynText("comment", 48, -13, 6.0)])


def _schuetz3(**_):
    """Hauptkontakte Schütz 3-polig (Schließer mit Schützfunktion), Pole bei x = 0, 20, 40."""
    teile = []
    ans = []
    for i, x in enumerate((0, 20, 40)):
        teile += [L(x, -30, x, -10), L(x, 10, x, 30), L(x, 10, x - 8, -13),
                  B(x - 3, -13, 6, 6, 180, 180),
                  T(x + 2, -22, str(2 * i + 1)), T(x + 2, 27, str(2 * i + 2))]
        ans += [Anschluss(str(2 * i + 1), x, -30, "n"), Anschluss(str(2 * i + 2), x, 30, "s")]
    teile.append(L(-4, -1, 36, -1, ls="dashed"))
    return Symbol("schuetz3", "Schütz Hauptkontakte 3-polig", "Kontakte", teile, ans,
                  [DynText("label", 48, -26, 7.0, fett=True), DynText("comment", 48, -13, 6.0)])


def _ueberlast3(**_):
    """Thermisches Überlastrelais (Motorschutzrelais) 3-polig, Pole bei x = 0, 20, 40."""
    teile = [R(-12, -14, 64, 28)]
    ans = []
    for i, x in enumerate((0, 20, 40)):
        teile += [L(x, -30, x, -6), L(x, -6, x - 5, -6), L(x - 5, -6, x - 5, 6), L(x - 5, 6, x, 6),
                  L(x, 6, x, 30), T(x + 2, -17, str(2 * i + 1)), T(x + 2, 24, str(2 * i + 2))]
        ans += [Anschluss(str(2 * i + 1), x, -30, "n"), Anschluss(str(2 * i + 2), x, 30, "s")]
    return Symbol("ueberlast3", "Überlastrelais thermisch 3-polig", "Schutzgeräte", teile, ans,
                  [DynText("label", 56, -26, 7.0, fett=True), DynText("comment", 56, -13, 6.0),
                   DynText("function", 56, -1, 6.0)])


def _motor3(**_):
    """Drehstrommotor: U1 V1 W1 oben (x = -20, 0, 20), PE rechts unten."""
    teile = [K(0, 8, 24), L(-20, -30, -20, -5.3), L(0, -30, 0, -16), L(20, -30, 20, -5.3),
             T_mitte(0, 2, "M", 9), T_mitte(0, 15, "3~", 6),
             T(-18, -22, "U1"), T(2, -22, "V1"), T(22, -22, "W1"),
             L(24, 8, 34, 8), L(34, 8, 34, 30), T(36, 27, "PE")]
    return Symbol("motor3", "Drehstrommotor", "Verbraucher", teile,
                  [Anschluss("U1", -20, -30, "n"), Anschluss("V1", 0, -30, "n"),
                   Anschluss("W1", 20, -30, "n"), Anschluss("PE", 34, 30, "s")],
                  [DynText("label", 38, -30, 7.0, fett=True), DynText("comment", 38, -17, 6.0)])


# ---- Spulen / Antriebe -------------------------------------------------------
def _spule(art="", **_):
    teile = [L(0, -30, 0, -10), R(-15, -10, 30, 20), L(0, 10, 0, 30), T(3, -22, "A1"),
             T(3, 27, "A2")]
    name = "Relais-/Schützspule"
    if art == "rv":       # Rückfallverzögerung (Treppenlichtzeitschalter)
        teile.append(R(-25, -10, 10, 20, fill="black"))
        name = "Spule mit Rückfallverzögerung (Treppenlicht)"
    elif art == "sst":    # Stromstoßschalter (Remanenz-/Stromstoßantrieb)
        teile += [R(-25, -10, 10, 20), P((-25, 6), (-23, 6), (-17, -6), (-15, -6), closed=False)]
        name = "Spule Stromstoßschalter"
    elif art == "av":     # Ansprechverzögerung
        teile += [R(-25, -10, 10, 20), L(-25, -10, -15, 10), L(-25, 10, -15, -10)]
        name = "Spule mit Ansprechverzögerung"
    return Symbol(f"spule_{art}" if art else "spule", name, "Spulen", teile, _auf_ab(),
                  [DynText("label", 18, -26, 7.0, fett=True), DynText("comment", 18, -13, 6.0)])


# ---- Verbraucher -----------------------------------------------------------------
def _leuchte(**_):
    teile = [L(0, -30, 0, -10), K(0, 0, 10), L(-7, -7, 7, 7), L(-7, 7, 7, -7), L(0, 10, 0, 30)]
    return Symbol("leuchte", "Leuchte / Lampe", "Verbraucher", teile, _auf_ab(),
                  [DynText("label", 13, -26, 7.0, fett=True), DynText("comment", 13, 6, 6.0)])


def _steckdose(**_):
    teile = [L(0, -30, 0, -12), L(-10, -12, 10, -12), B(-10, -12, 20, 20, 0, 180),
             L(-10, -2, -10, 30), L(10, -2, 10, 30), T(-17, 24, "N"), T(13, 24, "PE")]
    return Symbol("steckdose", "Schutzkontaktsteckdose", "Verbraucher", teile,
                  [Anschluss("L", 0, -30, "n"), Anschluss("N", -10, 30, "s"),
                   Anschluss("PE", 10, 30, "s")],
                  [DynText("label", 4, -38, 7.0, fett=True), DynText("comment", 4, -27, 6.0)])


def _motor(text="M\n1~", **_):
    zeilen = text.split("\n")
    teile = [L(0, -30, 0, -12), K(0, 0, 12), L(0, 12, 0, 30)]
    if len(zeilen) == 1:
        teile.append(T_mitte(0, 0, zeilen[0], 7))
    else:
        teile += [T_mitte(0, -4, zeilen[0], 7), T_mitte(0, 5, zeilen[1], 5)]
    return Symbol(f"motor_{text.replace(chr(10), '_')}", "Motor", "Verbraucher", teile, _auf_ab(),
                  [DynText("label", 15, -26, 7.0, fett=True), DynText("comment", 15, 8, 6.0)])


def _drehstrom(text="Herd", **_):
    """Drehstromverbraucher: L1 L2 L3 oben, N und PE unten."""
    from .model import textbreite
    b = max(60, int(math.ceil((textbreite(text, 7) + 10) / 10.0)) * 10)
    teile = [R(-b / 2, -15, b, 30), T_mitte(0, 0, text, 7)]
    ans = []
    for i, x in enumerate((-20, 0, 20), 1):
        teile += [L(x, -30, x, -15), T(x + 2, -21, f"L{i}")]
        ans.append(Anschluss(f"L{i}", x, -30, "n"))
    teile += [L(-10, 15, -10, 30), L(10, 15, 10, 30), T(-8, 26, "N"), T(12, 26, "PE")]
    ans += [Anschluss("N", -10, 30, "s"), Anschluss("PE", 10, 30, "s")]
    return Symbol(f"drehstrom_{text}_{b}", f"Drehstromverbraucher {text}", "Verbraucher", teile, ans,
                  [DynText("label", b / 2 + 3, -30, 7.0, fett=True),
                   DynText("comment", b / 2 + 3, -17, 6.0)])


def _verbraucher(text="", **_):
    """Einphasiger Verbraucher als Kasten mit L oben, N und PE unten."""
    from .model import textbreite
    b = max(40, int(math.ceil((textbreite(text, 7) + 10) / 10.0)) * 10)
    teile = [L(0, -30, 0, -15), R(-b / 2, -15, b, 30), T_mitte(0, 0, text, 7),
             L(-10, 15, -10, 30), L(10, 15, 10, 30), T(-8, 26, "N"), T(12, 26, "PE")]
    return Symbol(f"verbraucher_{text}_{b}", f"Verbraucher {text}", "Verbraucher", teile,
                  [Anschluss("L", 0, -30, "n"), Anschluss("N", -10, 30, "s"),
                   Anschluss("PE", 10, 30, "s")],
                  [DynText("label", b / 2 + 3, -30, 7.0, fett=True),
                   DynText("comment", b / 2 + 3, -17, 6.0)])


# ---- Potentiale / Schienen ------------------------------------------------------
def _schiene_anfang(text="L1", **_):
    from .model import textbreite
    w = textbreite(text, 8)
    return Symbol(f"schiene_anfang_{text}", f"Potential {text} (Anfang)", "Allgemein",
                  [T(-w - 4, 4, text, 8), L(-2, 0, 0, 0)], [Anschluss("1", 0, 0, "e")], [])


def _schiene_ende(text="L1", **_):
    return Symbol(f"schiene_ende_{text}", f"Potential {text} (Ende)", "Allgemein",
                  [L(0, 0, 2, 0), T(5, 4, text, 8)], [Anschluss("1", 0, 0, "w")], [])


def _verweis(text="weiter Blatt 2", **_):
    """Pfeil am Ende einer Schiene mit Verweistext darüber (rechtsbündig)."""
    from .model import textbreite
    w = textbreite(text, 7)
    return Symbol(f"verweis_{text}", f"Verweis {text}", "Allgemein",
                  [P((0, -3), (7, 0), (0, 3), fill="black"), T(7 - w, -5, text, 7)],
                  [Anschluss("1", 0, 0, "w")], [])


# --------------------------------------------------------------------------
# Installationssymbole (Grundriss) – Ursprung auf der Wand, Symbol ragt nach +y
# --------------------------------------------------------------------------
TXT_INST = [DynText("label", 13, 4, 6.0, fett=True), DynText("comment", 13, 14, 5.0)]
_SC = (0.0, 20.0)       # Mittelpunkt des Schalterkreises
_SR = 7.0               # Radius Schalterkreis
_ARM = 16.0             # Armlänge


def _arm(winkel, tick=+1, ticks=1):
    """Schalterarm vom Kreis nach außen, Winkel in Grad (0 = rechts, 90 = in den Raum)."""
    d = (math.cos(math.radians(winkel)), math.sin(math.radians(winkel)))
    cx, cy = _SC
    a = (cx + _SR * d[0], cy + _SR * d[1])
    e = (cx + (_SR + _ARM) * d[0], cy + (_SR + _ARM) * d[1])
    out = [L(round(a[0], 2), round(a[1], 2), round(e[0], 2), round(e[1], 2))]
    perp = (d[1] * tick, -d[0] * tick)
    for i in range(ticks):
        bx, by = e[0] - d[0] * 5 * i, e[1] - d[1] * 5 * i
        out.append(L(round(bx, 2), round(by, 2), round(bx + 6 * perp[0], 2),
                     round(by + 6 * perp[1], 2)))
    return out


def _inst(key, name, teile, texte=None, beschreibung=""):
    return Symbol(key, name, "Installation", teile, [], texte if texte is not None else TXT_INST,
                  beschreibung)


def _i_steckdose(anzahl=1, schutzkontakt=True, **_):
    teile = [L(0, 0, 0, 6), B(-8, 6, 16, 16, 0, 180)]
    if schutzkontakt:
        teile.append(L(-8, 6, 8, 6))
    if anzahl > 1:
        teile.append(T(-3, 24, str(anzahl), 6))
    name = "Schutzkontaktsteckdose" if schutzkontakt else "Steckdose"
    if anzahl > 1:
        name = f"{anzahl}-fach-{name}"
    return _inst(f"i_steckdose_{anzahl}_{int(schutzkontakt)}", name, teile)


def _i_fernmelde(text="TV", **_):
    teile = [L(0, 0, 0, 6), P((-8, 14), (-8, 6), (8, 6), (8, 14), closed=False),
             T_mitte(0, 20, text, 5)]
    return _inst(f"i_fernmelde_{text}", f"Fernmelde-/Datensteckdose {text}", teile)


def _i_schalter(art="aus", **_):
    cx, cy = _SC
    teile = [K(cx, cy, _SR)]
    namen = {"aus": "Ausschalter", "zweipolig": "Ausschalter zweipolig", "serie": "Serienschalter",
             "wechsel": "Wechselschalter", "kreuz": "Kreuzschalter", "dimmer": "Dimmer",
             "taster": "Taster", "taster_licht": "Taster mit Kontrollleuchte",
             "kontroll": "Schalter mit Kontrollleuchte"}
    if art in ("aus", "kontroll"):
        teile += _arm(45)
    elif art == "zweipolig":
        teile += _arm(45, ticks=2)
    elif art == "serie":
        teile += _arm(55) + _arm(125, tick=-1)
    elif art == "wechsel":
        teile += _arm(45) + _arm(225)
    elif art == "kreuz":
        teile += _arm(45) + _arm(225) + _arm(135, tick=-1) + _arm(315, tick=-1)
    elif art == "dimmer":
        teile += _arm(45)
        teile.append(P((10, 38), (21, 30), (21, 38), fill="black"))
    elif art in ("taster", "taster_licht"):
        teile.append(K(cx, cy, 3.5))
        if art == "taster_licht":
            teile += [L(-2.5, cy - 2.5, 2.5, cy + 2.5), L(2.5, cy - 2.5, -2.5, cy + 2.5)]
    else:
        raise ValueError(f"unbekannte Schalterart {art!r}")
    if art == "kontroll":
        teile += [L(-5, cy - 5, 5, cy + 5), L(5, cy - 5, -5, cy + 5)]
    texte = [DynText("label", 26, 6, 6.0, fett=True), DynText("comment", 26, 16, 5.0)]
    # ohne Anschlussstrich zur Wand (so sieht das Schaltersymbol im Grundriss aus)
    return _inst(f"i_schalter_{art}", namen[art], teile, texte)


def _i_leuchte(art="decke", **_):
    namen = {"decke": "Leuchte (Deckenauslass)", "wand": "Wandleuchte (Wandauslass)",
             "spot": "Einbauleuchte / Spot", "lang": "Langfeldleuchte / LED-Leiste",
             "not": "Sicherheitsleuchte", "strahler": "Strahler (Stromschiene)"}
    if art == "decke":
        teile = [K(0, 0, 9), L(-6.4, -6.4, 6.4, 6.4), L(-6.4, 6.4, 6.4, -6.4)]
        texte = [DynText("label", 9, 4, 6.0, fett=True), DynText("comment", 9, 14, 5.0)]
    elif art == "wand":
        teile = [L(0, 0, 0, 8), L(-8, 8, 8, 24), L(-8, 24, 8, 8)]
        texte = TXT_INST
    elif art == "spot":
        teile = [K(0, 0, 5), L(-3.5, -3.5, 3.5, 3.5), L(-3.5, 3.5, 3.5, -3.5)]
        texte = [DynText("label", 5, 2, 6.0, fett=True), DynText("comment", 5, 11, 5.0)]
    elif art == "lang":
        teile = [L(-25, 0, 25, 0), L(-25, -5, -25, 5), L(25, -5, 25, 5)]
        texte = [DynText("label", 26, -8, 6.0, fett=True), DynText("comment", 26, 2, 5.0)]
    elif art == "strahler":          # Leuchte mit Richtungspfeil, Ausrichtung über ori
        teile = [K(0, 0, 5), L(-3.5, -3.5, 3.5, 3.5), L(-3.5, 3.5, 3.5, -3.5), L(0, 5, 0, 11),
                 P((0, 15), (-2.5, 10), (2.5, 10), fill="black")]
        texte = [DynText("label", 7, -4, 6.0, fett=True), DynText("comment", 7, 5, 5.0)]
    elif art == "not":
        teile = [L(-8, -8, 8, 8), L(-8, 8, 8, -8), K(0, 0, 2.5, fill="black"), R(-10, -10, 20, 20)]
        texte = [DynText("label", 10, 4, 6.0, fett=True), DynText("comment", 10, 14, 5.0)]
    else:
        raise ValueError(f"unbekannte Leuchtenart {art!r}")
    return _inst(f"i_leuchte_{art}", namen[art], teile, texte)


def _i_dose(art="abzweig", **_):
    teile = [K(0, 0, 5)]
    if art == "anschluss":
        teile.append(K(0, 0, 1.5, fill="black"))
    name = "Abzweigdose" if art == "abzweig" else "Geräteanschlussdose"
    return _inst(f"i_dose_{art}", name, teile,
                 [DynText("label", 6, 0, 6.0, fett=True), DynText("comment", 6, 10, 5.0)])


def _i_geraet(text="H", **_):
    """Geräteanschluss (Herd, Backofen, Geschirrspüler …) als Kasten mit Kurzzeichen."""
    from .model import textbreite
    b = max(16, math.ceil(textbreite(text, 6) + 6))
    teile = [L(0, 0, 0, 4), R(-b / 2, 4, b, 14), T_mitte(0, 11, text, 6)]
    return _inst(f"i_geraet_{text}", f"Geräteanschluss {text}", teile,
                 [DynText("label", b / 2 + 2, 2, 6.0, fett=True),
                  DynText("comment", b / 2 + 2, 12, 5.0)])


def _i_verteiler(**_):
    teile = [R(-18, 0, 36, 14), P((-18, 14), (18, 14), (18, 0), fill="black")]
    return _inst("i_verteiler", "Stromkreisverteiler", teile,
                 [DynText("label", 20, 0, 6.0, fett=True), DynText("comment", 20, 10, 5.0)])


def _i_melder(text="RM", **_):
    """Melder/Sensor als Kasten (Rauchmelder, Bewegungsmelder, Thermostat …)."""
    from .model import textbreite
    b = max(14, math.ceil(textbreite(text, 5) + 6))
    teile = [R(-b / 2, -7, b, 14), T_mitte(0, 0, text, 5)]
    return _inst(f"i_melder_{text}", f"Melder/Sensor {text}", teile,
                 [DynText("label", b / 2 + 2, -6, 6.0, fett=True),
                  DynText("comment", b / 2 + 2, 4, 5.0)])


def _i_klingel(**_):
    teile = [L(0, 0, 0, 6), B(-8, 6, 16, 16, 180, 180), L(-8, 14, 8, 14)]
    return _inst("i_klingel", "Klingel / Gong", teile)


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Allpolige Verteilerdarstellung: mehrpolige Geräte, Pole im Abstand 20 px
# --------------------------------------------------------------------------
TXT_LINKS = [DynText("label", -40, -40, 7.0, fett=True), DynText("comment", -40, -29, 6.0),
             DynText("function", -40, -18, 6.0)]


def _pole(n, kreuz=(), lasttrenn=False, oben=(), unten=()):
    """n Schaltglieder bei x = 0, 20, 40 …, Messer an der Linie y = -1 gekoppelt."""
    teile = []
    for i in range(n):
        x = 20 * i
        if lasttrenn:
            teile += [L(x, -30, x, -14), K(x, -12, 2), L(x - 3, -14, x + 3, -14)]
        else:
            teile.append(L(x, -30, x, -10))
        teile += [L(x, 10, x, 30), L(x, 10, x - 8, -13)]
        if i in kreuz:
            teile += [L(x - 3, -13, x + 3, -7), L(x + 3, -13, x - 3, -7)]
        if i < len(oben) and oben[i]:
            teile.append(T(x + 2, -22, oben[i]))
        if i < len(unten) and unten[i]:
            teile.append(T(x + 2, 27, unten[i]))
    return teile


def _ausloeser(n, text):
    """Wirkverbindung nach links zu einem Auslöserkasten (IΔ, I>) bzw. Handantrieb."""
    ende = 20 * (n - 1) - 4
    teile = [L(-22, -1, ende, -1, ls="dashed")] if n > 1 else [L(-22, -1, -4, -1, ls="dashed")]
    if text == "hand":
        teile.append(L(-22, -6, -22, 4))
    else:
        teile += [R(-36, -6, 14, 10), T_mitte(-29, -1, text, 5)]
    return teile


def _fi_n(pole=4, **_):
    """FI allpolig: 2 Pole (L, N) oder 4 Pole (L1, L2, L3, N)."""
    if pole == 2:
        oben, unten, namen = ("1", "N"), ("2", "N"), (("1", "2"), ("3", "4"))
    else:
        oben, unten = ("1", "3", "5", "7N"), ("2", "4", "6", "8N")
        namen = (("1", "2"), ("3", "4"), ("5", "6"), ("7", "8"))
    teile = _pole(pole, oben=oben, unten=unten) + _ausloeser(pole, "IΔ")
    ans = []
    for i, (o, u) in enumerate(namen):
        ans += [Anschluss(o, 20 * i, -30, "n"), Anschluss(u, 20 * i, 30, "s")]
    return Symbol(f"fi{pole}", f"FI-Schutzschalter {pole}-polig", "Schutzgeräte", teile, ans,
                  TXT_LINKS)


def _fils2(**_):
    teile = _pole(2, kreuz=(0,), oben=("1", "N"), unten=("2", "N")) + _ausloeser(2, "IΔ")
    return Symbol("fils2", "FI/LS-Schalter 2-polig (RCBO)", "Schutzgeräte", teile,
                  [Anschluss("1", 0, -30, "n"), Anschluss("2", 0, 30, "s"),
                   Anschluss("3", 20, -30, "n"), Anschluss("4", 20, 30, "s")], TXT_LINKS)


def _ls_n(pole=1, **_):
    """LS allpolig mit Klemmennummern; 1-, 2- (L+N) oder 3-polig."""
    oben = [str(2 * i + 1) for i in range(pole)]
    unten = [str(2 * i + 2) for i in range(pole)]
    teile = _pole(pole, kreuz=tuple(range(pole)), oben=oben, unten=unten)
    if pole > 1:
        teile.append(L(-4, -1, 20 * (pole - 1) - 4, -1, ls="dashed"))
    ans = []
    for i in range(pole):
        ans += [Anschluss(oben[i], 20 * i, -30, "n"), Anschluss(unten[i], 20 * i, 30, "s")]
    return Symbol(f"ls_a{pole}", f"Leitungsschutzschalter {pole}-polig", "Schutzgeräte", teile, ans,
                  [DynText("label", -40, -26, 7.0, fett=True), DynText("comment", -40, -15, 6.0)])


def _hauptschalter_n(pole=3, **_):
    oben = ["1", "3", "5", "7"][:pole]
    unten = ["2", "4", "6", "8"][:pole]
    teile = _pole(pole, lasttrenn=True, oben=oben, unten=unten) + _ausloeser(pole, "hand")
    ans = []
    for i in range(pole):
        ans += [Anschluss(oben[i], 20 * i, -30, "n"), Anschluss(unten[i], 20 * i, 30, "s")]
    return Symbol(f"hauptschalter{pole}", f"Hauptschalter {pole}-polig", "Schutzgeräte", teile, ans,
                  [DynText("label", -40, -26, 7.0, fett=True), DynText("comment", -40, -15, 6.0)])


def _sicherung_n(pole=3, **_):
    teile = []
    ans = []
    for i in range(pole):
        x = 20 * i
        teile += [R(x - 4, -15, 8, 30), L(x, -30, x, 30)]
        ans += [Anschluss(str(2 * i + 1), x, -30, "n"), Anschluss(str(2 * i + 2), x, 30, "s")]
    return Symbol(f"sicherung{pole}", f"Sicherungen {pole}-polig", "Schutzgeräte", teile, ans,
                  [DynText("label", -40, -26, 7.0, fett=True), DynText("comment", -40, -15, 6.0)])


def _spd4(**_):
    """Überspannungsschutz 3+1: Ableiter je Leiter, gemeinsamer PE-Anschluss."""
    teile = []
    ans = []
    for i, n in enumerate(("L1", "L2", "L3", "N")):
        x = 20 * i
        teile += [L(x, -30, x, -5), P((x - 2.5, -8), (x + 2.5, -8), (x, -2), fill="black"),
                  R(x - 5, -10, 10, 20), L(x, 10, x, 20), T(x + 2, -22, n)]
        ans.append(Anschluss(n, x, -30, "n"))
    teile += [L(0, 20, 60, 20), L(30, 20, 30, 30), T(32, 28, "PE")]
    ans.append(Anschluss("PE", 30, 30, "s"))
    return Symbol("spd4", "Überspannungsschutz 3+1", "Schutzgeräte", teile, ans, TXT_LINKS)


def _reihenklemme(**_):
    """Reihenklemme als Kasten, Anschluss oben; Bezeichnung senkrecht (pro Bauteil gesetzt)."""
    return Symbol("reihenklemme", "Reihenklemme", "Allgemein", [R(-10, 0, 20, 40)],
                  [Anschluss("1", 0, 0, "n")], [DynText("label", -6, 36, 6.0, rot=270)])


FABRIKEN = {
    # Verteilerplan (einpolig)
    "ls": _ls, "fi": _fi, "fils": _fils, "hauptschalter": _hauptschalter, "trenner": _trenner,
    "sicherung": _sicherung, "spd": _spd, "erde": _erde, "klemme": _klemme, "knoten": _knoten, "abgang": _abgang,
    "einspeisung": _einspeisung, "zaehler": _zaehler, "kasten": _kasten, "kasten_n": _kasten_n,
    # Stromlaufplan
    "schliesser": _schliesser, "oeffner": _oeffner, "wechsler": _wechsler,
    "kreuzschalter": _kreuzschalter, "serienschalter": _serienschalter, "spule": _spule,
    "ls3": _ls3, "schuetz3": _schuetz3, "ueberlast3": _ueberlast3, "motor3": _motor3,
    "leuchte": _leuchte, "steckdose": _steckdose, "motor": _motor, "drehstrom": _drehstrom,
    "verbraucher": _verbraucher, "schiene_anfang": _schiene_anfang, "schiene_ende": _schiene_ende,
    "verweis": _verweis,
    # Verteiler allpolig
    "fi_n": _fi_n, "fils2": _fils2, "ls_n": _ls_n, "hauptschalter_n": _hauptschalter_n,
    "sicherung_n": _sicherung_n, "spd4": _spd4, "reihenklemme": _reihenklemme,
    # Installationsplan
    "i_steckdose": _i_steckdose, "i_fernmelde": _i_fernmelde, "i_schalter": _i_schalter,
    "i_leuchte": _i_leuchte, "i_dose": _i_dose, "i_geraet": _i_geraet,
    "i_verteiler": _i_verteiler, "i_melder": _i_melder, "i_klingel": _i_klingel,
}


def symbol(typ: str, /, **params) -> Symbol:
    """Symbol holen oder erzeugen; gleiche Parameter liefern dasselbe Objekt."""
    if typ not in FABRIKEN:
        raise KeyError(f"Unbekanntes Symbol {typ!r}")
    s = FABRIKEN[typ](**params)
    if s.key in _CACHE:
        return _CACHE[s.key]
    return _reg(s)
