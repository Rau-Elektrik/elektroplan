"""Stromlaufplan in aufgelöster Darstellung (DIN EN 61082 / Symbole DIN EN 60617).

L-Schienen oben, N und PE unten. Jeder Strompfad liegt in einer Rasterspalte, die
Spaltennummer am Blattrand ist damit die Strompfadnummer. Schaltungen werden aus
Bausteinen zusammengesetzt (siehe BAUSTEINE).
"""
from __future__ import annotations

from collections import defaultdict

from . import firma as _firma
from .blatt import Format
from .model import Blatt, Projekt, textbreite
from .symbole import symbol

SPALTE = 50
Y_SCHIENE = {"L1": 45, "L2": 57, "L3": 69, "N": 590, "PE": 605}
Y_LS = 140
Y_LAST = 505                 # Verbraucherreihe
Y_BESCHR = 622
OBEN = ("L1", "L2", "L3")


def _reihen(n: int) -> list[float]:
    """y-Mittelpunkte für n Schaltgeräte zwischen LS und Verbraucher."""
    if n <= 0:
        return []
    if n == 1:
        return [290]
    if n == 2:
        return [250, 360]
    if n == 3:
        return [235, 320, 405]
    return [220 + 70 * i for i in range(n)][:4]


def _n(s) -> str:
    return str(s or "").strip()


def _liste(v, std=1) -> list:
    """Zahl, Einzelangabe oder Liste → Liste von dicts."""
    if v is None:
        v = std
    if isinstance(v, int):
        return [{} for _ in range(v)]
    if isinstance(v, (dict, str)):
        v = [v]
    return [e if isinstance(e, dict) else {"text": e} for e in v]


class Pfadbau:
    """Hilfsobjekt für ein Blatt: Spalten, Schienenabgriffe, BMK-Zähler."""

    def __init__(self, bl: Blatt, zaehler: dict):
        self.bl = bl
        fx, fy, fw, fh = bl.format.zeichenflaeche()
        self.fx, self.fw = fx, fw
        self.abgriffe = defaultdict(list)     # schiene -> [(bauteil, anschluss, x_anfahrt)]
        self.zaehler = zaehler
        self.genutzt = set()

    def x(self, spalte: int) -> float:
        return self.fx + (spalte + 0.5) * SPALTE

    def bmk(self, buchstabe: str, vorgabe=None) -> str:
        if _n(vorgabe):
            return _n(vorgabe)
        self.zaehler[buchstabe] += 1
        return f"{buchstabe}{self.zaehler[buchstabe]}"

    def an(self, schiene: str, bauteil, anschluss: str, x_anfahrt=None):
        schiene = schiene.upper()
        if schiene not in Y_SCHIENE:
            raise ValueError(f"Unbekannte Schiene {schiene!r} (L1, L2, L3, N, PE)")
        self.abgriffe[schiene].append((bauteil, anschluss, x_anfahrt))
        self.genutzt.add(schiene)

    def beschreibung(self, sp0: int, n: int, text: str):
        if not text:
            return
        xl, xr = self.x(sp0) - SPALTE / 2, self.x(sp0 + n - 1) + SPALTE / 2
        breite = xr - xl - 6
        pt = 6.5
        while pt > 5 and textbreite(text, pt) > breite:
            pt -= 0.5
        zeilen = [text]
        if textbreite(text, pt) > breite:
            worte, zeilen, akt = text.split(), [], ""
            for w in worte:
                probe = f"{akt} {w}".strip()
                if textbreite(probe, pt) <= breite or not akt:
                    akt = probe
                else:
                    zeilen.append(akt)
                    akt = w
            zeilen.append(akt)
        self.bl.text((xl + xr) / 2, Y_BESCHR, "\n".join(zeilen[:3]), pt, h="mitte")
        self.bl.linie(xl + 3, Y_BESCHR - 3, xr - 3, Y_BESCHR - 3, breite=0.5)

    # --- gemeinsame Bausteine ------------------------------------------------------
    def ls(self, k: dict, x: float, phase: str):
        """LS am Pfadanfang (oder None, wenn "ls": false)."""
        ls = k.get("ls", {})
        if ls is False:
            return None
        ls = ls if isinstance(ls, dict) else {"bez": ls}
        b = self.bl.setze(symbol("ls"), x, Y_LS, label=self.bmk("F", ls.get("bmk")),
                          comment=_n(ls.get("bez") or ls.get("text")) or "B16")
        self.an(phase, b, "1")
        return b

    def leuchten(self, k: dict, sp0: int, quelle, quelle_t: str, schiene_n="N"):
        """Leuchten parallel ab Spalte sp0, gespeist von quelle/quelle_t. Gibt Anzahl zurück."""
        liste = k.get("leuchten", 1)
        if isinstance(liste, int):
            liste = [{} for _ in range(liste)]
        vorher = None
        for i, e in enumerate(liste):
            e = e if isinstance(e, dict) else {"text": e}
            x = self.x(sp0 + i)
            b = self.bl.setze(symbol("leuchte"), x, Y_LAST, label=self.bmk("E", e.get("bmk")),
                              comment=_n(e.get("text") or e.get("bez")))
            if vorher is None:
                qx, qy = quelle.pos(quelle_t)
                weg = [] if qx == x else [(qx, Y_LAST - 45), (x, Y_LAST - 45)]
                self.bl.verbinde(quelle, quelle_t, b, "1", ueber=weg)
            else:
                self.bl.verbinde(vorher, "1", b, "1",
                                 ueber=[(x - SPALTE, Y_LAST - 45), (x, Y_LAST - 45)])
            self.an(schiene_n, b, "2")
            vorher = b
        return len(liste)


# --------------------------------------------------------------------------
# Bausteine: f(pb, kreis, spalte0) -> Anzahl belegter Spalten
# --------------------------------------------------------------------------
def b_ausschaltung(pb: Pfadbau, k: dict, sp: int) -> int:
    x = pb.x(sp)
    phase = _n(k.get("phase")) or "L1"
    f = pb.ls(k, x, phase)
    sch = _liste(k.get("schalter"))[0]
    s = pb.bl.setze(symbol("schliesser", antrieb="hand"), x, _reihen(1)[0],
                    label=pb.bmk("S", sch.get("bmk")), comment=_n(sch.get("ort")))
    if f:
        pb.bl.verbinde(f, "2", s, "1")
    else:
        pb.an(phase, s, "1")
    n = pb.leuchten(k, sp, s, "2")
    return max(1, n)


def b_serienschaltung(pb: Pfadbau, k: dict, sp: int) -> int:
    x = pb.x(sp)
    phase = _n(k.get("phase")) or "L1"
    f = pb.ls(k, x, phase)
    sch = _liste(k.get("schalter"))[0]
    yr = _reihen(1)[0]
    s = pb.bl.setze(symbol("serienschalter"), x, yr, label=pb.bmk("S", sch.get("bmk")),
                    comment=_n(sch.get("ort")))
    if f:
        pb.bl.verbinde(f, "2", s, "L")
    else:
        pb.an(phase, s, "L")
    grp_a = k.get("leuchten_1", k.get("leuchten", 1))
    grp_b = k.get("leuchten_2", 1)
    na = pb.leuchten({"leuchten": grp_a}, sp, s, "1")
    # zweiter Ausgang: erst nach unten, dann nach rechts zur zweiten Gruppe
    sp_b = sp + max(na, 1) + (1 if na == 1 else 0)
    xb = pb.x(sp_b)
    nb_liste = grp_b if not isinstance(grp_b, int) else [{} for _ in range(grp_b)]
    vorher = None
    for i, e in enumerate(nb_liste):
        e = e if isinstance(e, dict) else {"text": e}
        xi = pb.x(sp_b + i)
        b = pb.bl.setze(symbol("leuchte"), xi, Y_LAST, label=pb.bmk("E", e.get("bmk")),
                        comment=_n(e.get("text") or e.get("bez")))
        if vorher is None:
            sx, sy = s.pos("2")
            pb.bl.verbinde(s, "2", b, "1", ueber=[(sx, sy + 15), (xi, sy + 15)])
        else:
            pb.bl.verbinde(vorher, "1", b, "1", ueber=[(xi - SPALTE, Y_LAST - 45), (xi, Y_LAST - 45)])
        pb.an("N", b, "2")
        vorher = b
    return sp_b - sp + len(nb_liste)


def _wechsel_kette(pb: Pfadbau, k: dict, sp: int, n_kreuz: int):
    x = pb.x(sp)
    phase = _n(k.get("phase")) or "L1"
    f = pb.ls(k, x, phase)
    schalter = _liste(k.get("schalter"), 0)
    reihen = _reihen(2 + n_kreuz)
    while len(schalter) < 2 + n_kreuz:
        schalter.append({})
    s1d, s2d = schalter[0], schalter[-1]
    s1 = pb.bl.setze(symbol("wechsler", antrieb="hand", oben=True, nc_rechts=True), x, reihen[0],
                     label=pb.bmk("S", s1d.get("bmk")), comment=_n(s1d.get("ort")))
    if f:
        pb.bl.verbinde(f, "2", s1, "c")
    else:
        pb.an(phase, s1, "c")
    a, at, b, bt = s1, "no", s1, "nc"
    for i in range(n_kreuz):
        kd = schalter[1 + i]
        kr = pb.bl.setze(symbol("kreuzschalter"), x, reihen[1 + i], label=pb.bmk("S", kd.get("bmk")),
                         comment=_n(kd.get("ort")))
        pb.bl.verbinde(a, at, kr, "a")
        pb.bl.verbinde(b, bt, kr, "b")
        a, at, b, bt = kr, "c", kr, "d"
    s2 = pb.bl.setze(symbol("wechsler", antrieb="hand", oben=False, nc_rechts=True), x, reihen[-1],
                     label=pb.bmk("S", s2d.get("bmk")), comment=_n(s2d.get("ort")))
    pb.bl.verbinde(a, at, s2, "no")
    pb.bl.verbinde(b, bt, s2, "nc")
    n = pb.leuchten(k, sp, s2, "c")
    return max(2, n)


def b_wechselschaltung(pb, k, sp):
    return _wechsel_kette(pb, k, sp, 0)


def b_kreuzschaltung(pb, k, sp):
    n = int(k.get("kreuzschalter", 1))
    if not 1 <= n <= 2:
        raise ValueError("Kreuzschaltung: 1 oder 2 Kreuzschalter möglich")
    return _wechsel_kette(pb, k, sp, n)


def _taster_relais(pb: Pfadbau, k: dict, sp: int, art: str) -> int:
    """Stromstoß- oder Treppenlichtschaltung: Taster parallel → Spule, Kontakt → Leuchten."""
    phase = _n(k.get("phase")) or "L1"
    taster = k.get("taster", 2)
    if isinstance(taster, int):
        taster = [{} for _ in range(taster)]
    x0 = pb.x(sp)
    f = pb.ls(k, x0, phase)
    y_t = 290
    tb = []
    for i, t in enumerate(taster):
        t = t if isinstance(t, dict) else {"ort": t}
        b = pb.bl.setze(symbol("schliesser", antrieb="druck"), pb.x(sp + i), y_t,
                        label=pb.bmk("S", t.get("bmk")), comment=_n(t.get("ort")))
        tb.append(b)
    rel = k.get("relais") or {}
    kurz = "SST" if art == "sst" else "TLZ"
    # Spule unter dem letzten Taster: ihr Zusatzkasten links liegt dann in einer Tasterspalte
    xs = pb.x(sp + len(taster) - 1)
    spule = pb.bl.setze(symbol("spule", art=art), xs, Y_LAST, label=pb.bmk("K", rel.get("bmk")),
                        comment=_n(rel.get("text")) or kurz)
    xk = pb.x(sp + len(tb))
    kont = pb.bl.setze(symbol("schliesser", oben="1" if art == "sst" else "", unten="2" if art == "sst" else ""),
                       xk, y_t, label=spule.info["label"])
    # Einspeisung: LS → erster Taster, Querverbindung oben zu allen Tastern und zum Kontakt
    if f:
        pb.bl.verbinde(f, "2", tb[0], "1")
    else:
        pb.an(phase, tb[0], "1")
    y_q = y_t - 55
    kette = tb + [kont]
    for a, b in zip(kette, kette[1:]):
        ax, _ = a.pos("1")
        bx, _ = b.pos("1")
        pb.bl.verbinde(a, "1", b, "1", ueber=[(ax, y_q), (bx, y_q)])
    # Tasterausgänge parallel auf die Spule
    pb.bl.verbinde(tb[-1], "2", spule, "1")
    y_u = y_t + 55
    for a, b in zip(tb, tb[1:]):
        ax, _ = a.pos("2")
        bx, _ = b.pos("2")
        pb.bl.verbinde(a, "2", b, "2", ueber=[(ax, y_u), (bx, y_u)])
    pb.an("N", spule, "2")
    n = pb.leuchten(k, sp + len(tb), kont, "2")
    # Kontaktspiegel unter der Spule: Schließer → Strompfad
    pfad = sp + len(tb) + 1
    pb.bl.text(xs + 4, Y_LAST + 34, f"{'1–2' if art == 'sst' else 'Kontakt'} → Pfad {pfad}", 5)
    return len(tb) + max(1, n)


def b_stromstoss(pb, k, sp):
    return _taster_relais(pb, k, sp, "sst")


def b_treppenlicht(pb, k, sp):
    return _taster_relais(pb, k, sp, "rv")


def _geraet_mit_n(pb: Pfadbau, k: dict, sp: int, text: str, buchstabe: str) -> int:
    x = pb.x(sp)
    phase = _n(k.get("phase")) or "L1"
    f = pb.ls(k, x, phase)
    g = k.get("geraet") or {}
    mit_n = k.get("mit_n", True)
    sym = symbol("kasten_n", text=text) if mit_n else symbol("kasten", text=text)
    d = pb.bl.setze(sym, x, _reihen(1)[0], label=pb.bmk(buchstabe, g.get("bmk")),
                    comment=_n(g.get("ort") or g.get("text")))
    if f:
        pb.bl.verbinde(f, "2", d, "1")
    else:
        pb.an(phase, d, "1")
    if mit_n:
        pb.an("N", d, "N", x_anfahrt=pb.x(sp + 1))
    n = pb.leuchten(k, sp, d, "2")
    # Kasten ist breiter als ein Kontakt: Beschriftung braucht die zweite Spalte
    return max(2, n)


def b_dimmer(pb, k, sp):
    return _geraet_mit_n(pb, {**k, "mit_n": k.get("mit_n", False)}, sp,
                         _n((k.get("geraet") or {}).get("kurz")) or "Dimmer", "S")


def b_bewegungsmelder(pb, k, sp):
    return _geraet_mit_n(pb, k, sp, _n((k.get("geraet") or {}).get("kurz")) or "BWM", "B")


def b_steckdosen(pb: Pfadbau, k: dict, sp: int) -> int:
    x = pb.x(sp)
    phase = _n(k.get("phase")) or "L1"
    f = pb.ls(k, x, phase)
    liste = k.get("steckdosen", 1)
    if isinstance(liste, int):
        liste = [{} for _ in range(liste)]
    vorher = None
    for i, e in enumerate(liste):
        e = e if isinstance(e, dict) else {"text": e}
        xi = pb.x(sp + i)
        b = pb.bl.setze(symbol("steckdose"), xi, Y_LAST, label=pb.bmk("XD", e.get("bmk")),
                        comment=_n(e.get("text") or e.get("ort")))
        if vorher is None:
            if f:
                pb.bl.verbinde(f, "2", b, "L")
            else:
                pb.an(phase, b, "L")
        else:
            pb.bl.verbinde(vorher, "L", b, "L", ueber=[(xi - SPALTE, Y_LAST - 50), (xi, Y_LAST - 50)])
        pb.an("N", b, "N")
        pb.an("PE", b, "PE")
        vorher = b
    return max(1, len(liste))


def b_drehstrom(pb: Pfadbau, k: dict, sp: int) -> int:
    xc = pb.x(sp) + SPALTE / 2
    ls = k.get("ls", {}) or {}
    ls = ls if isinstance(ls, dict) else {"bez": ls}
    f = pb.bl.setze(symbol("ls3"), xc - 20, Y_LS, label=pb.bmk("F", ls.get("bmk")),
                    comment=_n(ls.get("bez")) or "B16")
    v = k.get("verbraucher") or {}
    v = v if isinstance(v, dict) else {"text": v}
    b = pb.bl.setze(symbol("drehstrom", text=_n(v.get("text")) or "Herd"), xc, Y_LAST,
                    label=pb.bmk("E", v.get("bmk")), comment=_n(v.get("bez")))
    for i, ph in enumerate(OBEN):
        pb.an(ph, f, str(2 * i + 1))
        pb.bl.verbinde(f, str(2 * i + 2), b, f"L{i + 1}")
    pb.an("N", b, "N")
    pb.an("PE", b, "PE")
    return 2


_FREI_SYMBOL = {
    "ls": lambda e: symbol("ls"), "sicherung": lambda e: symbol("sicherung"),
    "schalter": lambda e: symbol("schliesser", antrieb="hand"),
    "taster": lambda e: symbol("schliesser", antrieb="druck"),
    "schliesser": lambda e: symbol("schliesser", oben=_n(e.get("oben")), unten=_n(e.get("unten"))),
    "oeffner": lambda e: symbol("oeffner", oben=_n(e.get("oben")), unten=_n(e.get("unten"))),
    "öffner": lambda e: symbol("oeffner", oben=_n(e.get("oben")), unten=_n(e.get("unten"))),
    "spule": lambda e: symbol("spule", art=_n(e.get("art"))),
    "leuchte": lambda e: symbol("leuchte"),
    "motor": lambda e: symbol("motor", text=_n(e.get("motor")) or "M\n1~"),
    "kasten": lambda e: symbol("kasten", text=_n(e.get("kurz"))),
    "geraet": lambda e: symbol("kasten", text=_n(e.get("kurz"))),
}
_FREI_BUCHSTABE = {"ls": "F", "sicherung": "F", "schalter": "S", "taster": "S", "schliesser": "K",
                   "oeffner": "K", "öffner": "K", "spule": "K", "leuchte": "E", "motor": "M",
                   "kasten": "K", "geraet": "K"}


def b_frei(pb: Pfadbau, k: dict, sp: int) -> int:
    """Freie Strompfade: je Pfad eine Spalte, Elemente von oben nach unten in Reihe."""
    pfade = k.get("pfade") or []
    for i, p in enumerate(pfade):
        x = pb.x(sp + i)
        el = p.get("elemente") or []
        if not el:
            raise ValueError("frei: Pfad ohne Elemente")
        if len(el) > 6:
            raise ValueError("frei: höchstens 6 Elemente je Pfad")
        n = len(el)
        if n == 1:
            ys = [Y_LAST]
        else:
            mitte = _reihen(n - 2)
            ys = [Y_LS] + mitte + [Y_LAST]
        vorher = None
        for e, y in zip(el, ys):
            art = _n(e.get("symbol")).lower()
            if art not in _FREI_SYMBOL:
                raise ValueError(f"frei: unbekanntes Symbol {art!r} – möglich: {', '.join(_FREI_SYMBOL)}")
            b = pb.bl.setze(_FREI_SYMBOL[art](e), x, y,
                            label=pb.bmk(_FREI_BUCHSTABE[art], e.get("bmk")),
                            comment=_n(e.get("text") or e.get("bez")))
            if vorher is None:
                pb.an(_n(p.get("phase")) or "L1", b, "1")
            else:
                pb.bl.verbinde(vorher, "2", b, "1")
            vorher = b
        ende = (_n(p.get("ende")) or "N").upper()
        if ende in ("N", "PE"):
            pb.an(ende, vorher, "2")
        pb.beschreibung(sp + i, 1, _n(p.get("beschreibung")))
    return max(1, len(pfade))


def _pfadnr(pb: Pfadbau, x: float) -> int:
    """Strompfadnummer (Spaltenkopf am Blattrand) zu einer x-Koordinate."""
    return int((x - pb.fx) // SPALTE) + 1


def b_wendeschuetz(pb: Pfadbau, k: dict, sp: int) -> int:
    """Wendeschützschaltung mit Selbsthaltung und Schützverriegelung (optional Tasterverriegelung).

    Hauptstromkreis links (F1 → K1/K2 → F2 → M1, K2 tauscht L1 und L3),
    Steuerstromkreis rechts: F3 → F2 95-96 → S0 → S1‖K1 → (S2) → K2 21-22 → K1, gespiegelt für K2.
    """
    from .model import DynText
    bl = pb.bl
    def d(key, std_bmk, std_text=""):
        v = k.get(key) or {}
        v = v if isinstance(v, dict) else {"text": v}
        return {"bmk": _n(v.get("bmk")) or std_bmk, "text": _n(v.get("text") or v.get("bez")) or std_text,
                "funktion": _n(v.get("funktion") or v.get("einstellung"))}
    f1, f2, f3 = d("f1", "F1", "3× 16 A gG"), d("f2", "F2", "Überlastrelais"), d("f3", "F3", "B6")
    k1, k2 = d("k1", "K1", "Rechtslauf"), d("k2", "K2", "Linkslauf")
    s0, s1, s2 = d("s0", "S0", "Aus"), d("s1", "S1", "Rechts"), d("s2", "S2", "Links")
    m1 = d("motor", "M1", "")
    tv = k.get("tasterverriegelung", True)
    ohne_f3 = k.get("f3") is False
    phase = _n(k.get("phase")) or "L1"
    rechts = [DynText("label", 48, -26, 7.0, fett=True), DynText("comment", 48, -13, 6.0)]

    # ---- Hauptstromkreis ----------------------------------------------------------
    xa = pb.x(sp)                 # Pol 1 von K1 (L1 → U1)
    xk = xa + 110                 # Pol 1 von K2
    F1 = bl.setze(symbol("sicherung_n", pole=3), xa, 120, label=f1["bmk"], comment=f1["text"])
    F1.texte = rechts
    for i, ph in enumerate(OBEN):
        pb.an(ph, F1, str(2 * i + 1))
    K1 = bl.setze(symbol("schuetz3"), xa, 220, label=k1["bmk"])
    K2 = bl.setze(symbol("schuetz3"), xk, 220, label=k2["bmk"])
    for i in range(3):
        bl.verbinde(F1, str(2 * i + 2), K1, str(2 * i + 1))
    # Abzweig zu K2 in gleicher Phasenfolge (L3 oben, damit sich wenig kreuzt)
    for i, y in ((2, 160), (1, 170), (0, 180)):
        bl.verbinde(F1, str(2 * i + 2), K2, str(2 * i + 1),
                    ueber=[(xa + 20 * i, y), (xk + 20 * i, y)])
    # K2 tauscht L1 und L3: Pol 1 → W, Pol 2 → V, Pol 3 → U
    for pol_k2, pol_k1, y in ((0, 2, 260), (1, 1, 270), (2, 0, 280)):
        bl.verbinde(K2, str(2 * pol_k2 + 2), K1, str(2 * pol_k1 + 2),
                    ueber=[(xk + 20 * pol_k2, y), (xa + 20 * pol_k1, y)])
    F2 = bl.setze(symbol("ueberlast3"), xa, 340, label=f2["bmk"], comment=f2["text"],
                  function=f2["funktion"])
    for i in range(3):
        bl.verbinde(K1, str(2 * i + 2), F2, str(2 * i + 1))
    M = bl.setze(symbol("motor3"), xa + 20, 440, label=m1["bmk"], comment=m1["text"])
    for i, t in enumerate(("U1", "V1", "W1")):
        bl.verbinde(F2, str(2 * i + 2), M, t)
    pb.an("PE", M, "PE")

    # ---- Steuerstromkreis ---------------------------------------------------------
    ca, cb, cc, cd = (pb.x(sp + i) for i in (5, 6, 7, 8))
    def kette(teile, start=None):
        for a, b in zip(teile, teile[1:]):
            bl.verbinde(a, "2", b, "1")
    F3 = None if ohne_f3 else bl.setze(symbol("ls"), ca, 110, label=f3["bmk"], comment=f3["text"])
    F2h = bl.setze(symbol("oeffner", oben="95", unten="96", antrieb="thermisch"), ca, 180,
                   label=f2["bmk"])
    S0 = bl.setze(symbol("oeffner", oben="11", unten="12", antrieb="druck"), ca, 250,
                  label=s0["bmk"], comment=s0["text"])
    pb.an(phase, F3 or F2h, "1")
    kette([F3, F2h, S0] if F3 else [F2h, S0])

    y_t, y_v1, y_v2, y_sp = 325, 395, 465, 535
    if not tv:
        y_v2 = 430
    taster = lambda b, txt, x: bl.setze(symbol("schliesser", oben="13", unten="14", antrieb="druck"),
                                        x, y_t, label=b, comment=txt)
    halte = lambda b, x: bl.setze(symbol("schliesser", oben="13", unten="14"), x, y_t, label=b)
    S1 = taster(s1["bmk"], s1["text"], ca)
    H1 = halte(k1["bmk"], cb)
    S2 = taster(s2["bmk"], s2["text"], cc)
    H2 = halte(k2["bmk"], cd)
    # gemeinsame Querverbindung nach S0, Selbsthaltekontakte parallel zu den Tastern
    y_q, y_u = y_t - 37, y_t + 35
    bl.verbinde(S0, "2", S1, "1")
    for a, b in ((S1, H1), (H1, S2), (S2, H2)):
        ax, _ = a.pos("1")
        bx, _ = b.pos("1")
        bl.verbinde(a, "1", b, "1", ueber=[(ax, y_q), (bx, y_q)])
    for t, h in ((S1, H1), (S2, H2)):
        bl.verbinde(h, "2", t, "2", ueber=[(h.pos("2")[0], y_u), (t.pos("2")[0], y_u)])

    zweige = []
    for x, taster_b, gegen_t, gegen_k, eigen in ((ca, S1, s2, k2, k1), (cc, S2, s1, k1, k2)):
        glieder = [taster_b]
        if tv:
            glieder.append(bl.setze(symbol("oeffner", oben="21", unten="22", antrieb="druck"), x, y_v1,
                                    label=gegen_t["bmk"]))
        glieder.append(bl.setze(symbol("oeffner", oben="21", unten="22"), x, y_v2, label=gegen_k["bmk"]))
        sp_ = bl.setze(symbol("spule"), x, y_sp, label=eigen["bmk"], comment=eigen["text"])
        glieder.append(sp_)
        kette(glieder)
        pb.an("N", sp_, "2")
        zweige.append(sp_)

    # Kontaktspiegel unter den Spulen
    for sp_, x_haupt, x_halte, x_verr in ((zweige[0], xa, cb, cc), (zweige[1], xk, cd, ca)):
        x, y = sp_.x, sp_.y
        bl.text(x + 20, y + 4, f"1–2, 3–4, 5–6 → {_pfadnr(pb, x_haupt)}\n13–14 → {_pfadnr(pb, x_halte)}"
                f"\n21–22 → {_pfadnr(pb, x_verr)}", 5)

    pb.beschreibung(sp, 5, _n(k.get("bezeichnung")) or "Hauptstromkreis Motor Rechts-/Linkslauf")
    pb.beschreibung(sp + 5, 2, f"Steuerstromkreis {k1['text']}")
    pb.beschreibung(sp + 7, 2, f"Steuerstromkreis {k2['text']}")
    return 9


BAUSTEINE = {
    "ausschaltung": b_ausschaltung, "serienschaltung": b_serienschaltung,
    "wechselschaltung": b_wechselschaltung, "kreuzschaltung": b_kreuzschaltung,
    "stromstoss": b_stromstoss, "stromstoßschaltung": b_stromstoss, "stromstossschaltung": b_stromstoss,
    "treppenlicht": b_treppenlicht, "treppenlichtschaltung": b_treppenlicht,
    "dimmer": b_dimmer, "bewegungsmelder": b_bewegungsmelder,
    "steckdosen": b_steckdosen, "steckdose": b_steckdosen,
    "drehstrom": b_drehstrom, "herd": b_drehstrom, "frei": b_frei,
    "wendeschuetz": b_wendeschuetz, "wendeschütz": b_wendeschuetz,
    "wendeschuetzschaltung": b_wendeschuetz, "wendeschützschaltung": b_wendeschuetz,
}
EIGENE_BESCHREIBUNG = {"frei", "wendeschuetz", "wendeschütz", "wendeschuetzschaltung",
                       "wendeschützschaltung"}
BREITE_SCHAETZUNG = {
    "wechselschaltung": 2, "kreuzschaltung": 2, "drehstrom": 2, "herd": 2, "bewegungsmelder": 2,
    "dimmer": 2, "wendeschuetz": 9, "wendeschütz": 9, "wendeschuetzschaltung": 9,
    "wendeschützschaltung": 9,
}


def _breite(k: dict) -> int:
    typ = _n(k.get("typ")).lower()
    def anz(v, std=1):
        return v if isinstance(v, int) else len(v or []) or std
    if typ in ("stromstoss", "stromstoßschaltung", "stromstossschaltung", "treppenlicht",
               "treppenlichtschaltung"):
        return anz(k.get("taster", 2), 2) + anz(k.get("leuchten", 1))
    if typ in ("steckdosen", "steckdose"):
        return anz(k.get("steckdosen", 1))
    if typ == "frei":
        return max(1, len(k.get("pfade") or []))
    if typ == "serienschaltung":
        na = anz(k.get("leuchten_1", k.get("leuchten", 1)))
        return na + (1 if na == 1 else 0) + anz(k.get("leuchten_2", 1))
    return max(BREITE_SCHAETZUNG.get(typ, 1), anz(k.get("leuchten", 1)))


def _schienen(pb: Pfadbau, x_ende: float):
    bl = pb.bl
    x_anf = pb.fx + 30
    for name, y in Y_SCHIENE.items():
        if name not in pb.genutzt:
            continue
        start = bl.setze(symbol("schiene_anfang", text=name), x_anf, y)
        ende = bl.setze(symbol("schiene_ende", text=name), x_ende, y)
        taps = sorted(pb.abgriffe[name], key=lambda t: (t[2] if t[2] is not None else t[0].pos(t[1])[0]))
        vorher, vt, vx = start, "1", None
        for b, t, xa in taps:
            tx, ty = b.pos(t)
            ax = xa if xa is not None else tx
            weg = []
            if vx is not None:
                px, py = vorher.pos(vt)
                if vx != px:
                    weg.append((vx, py))
                weg.append((vx, y))
            weg.append((ax, y))
            weg.append((ax, ty))
            bl.verbinde(vorher, vt, b, t, ueber=weg)
            vorher, vt, vx = b, t, ax
        weg = []
        if vx is not None:
            px, py = vorher.pos(vt)
            if vx != px:
                weg.append((vx, py))
            weg.append((vx, y))
        bl.verbinde(vorher, vt, ende, "1", ueber=weg)


def baue(daten: dict, fmt: Format) -> Projekt:
    kreise = daten.get("stromkreise") or daten.get("schaltungen") or []
    if not kreise:
        raise ValueError("Keine Stromkreise angegeben")
    proj = daten.get("projekt", {})
    titel = _n(daten.get("titel")) or "Stromlaufplan"
    felder = dict(kunde=_n(proj.get("kunde")), objekt=_n(proj.get("objekt")),
                  auftrag=_n(proj.get("auftrag")), datum=_n(proj.get("datum")),
                  bearbeiter=_n(proj.get("bearbeiter")) or _firma.bearbeiter(),
                  indexrev=_n(proj.get("revision")) or "A",
                  anlage=_n(daten.get("anlage")),
                  plantyp="Stromlaufplan in aufgelöster Darstellung · DIN EN 61082 / DIN EN 60617")
    projekt = Projekt(titel)
    zaehler = defaultdict(int)
    spalten_max = fmt.cols - 2           # Spalte 0: Schienennamen, letzte: Schienenende
    pb = None
    sp = 1
    for k in kreise:
        typ = _n(k.get("typ")).lower()
        if typ not in BAUSTEINE:
            raise ValueError(f"Unbekannter Schaltungstyp {typ!r} – möglich: {', '.join(BAUSTEINE)}")
        w = _breite(k)
        if w > spalten_max:
            raise ValueError(f"{typ}: braucht {w} Strompfade, das Blatt hat nur {spalten_max}")
        if pb is None or sp + w > spalten_max + 1:
            if pb is not None:
                _schienen(pb, pb.x(spalten_max) + 15)
            bl = Blatt(fmt, titel, dict(felder))
            projekt.blaetter.append(bl)
            pb = Pfadbau(bl, zaehler)
            sp = 1
        n = BAUSTEINE[typ](pb, k, sp)
        if typ not in EIGENE_BESCHREIBUNG:
            pb.beschreibung(sp, n, _n(k.get("bezeichnung") or k.get("beschreibung")))
        sp += n
    _schienen(pb, pb.x(spalten_max) + 15)
    return projekt
