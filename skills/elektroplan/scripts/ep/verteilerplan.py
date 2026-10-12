"""Verteilerplan (Übersichtsschaltplan, einpolige Darstellung) aus einer Stromkreisliste.

Aufbau von oben nach unten:
  Einspeisung → Hauptschalter (Zähler, SLS …) → Sammelschiene
  Zeile 1: FI-Schalter und Überspannungsschutz an der Sammelschiene
  Zeile 2: LS / FI-LS je Stromkreis (unter ihrem FI oder direkt an der Schiene)
  Zeile 3: optional nachgeschaltetes Gerät (Stromstoßschalter, Treppenlicht …)
  Abgang und darunter die Stromkreistabelle (BMK, Schutzorgan, FI, Phase, Leitung, Verbraucher)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import firma as _firma
from .blatt import Format
from .model import Blatt, DynText, Projekt, textbreite
from .symbole import TXT_RECHTS, symbol

SPALTE = 50
X_KOPF_ENDE = 130          # Tabellenkopf links bis hier, danach Stromkreisspalten
X_EINSP = 75
Y_EINSP = 45
Y_SCHIENE = 240
Y_REIHE1 = 310
Y_UNTERSCHIENE = 380
Y_REIHE2 = 440
Y_REIHE3 = 520
Y_ABGANG = 590
Y_TABELLE = 600

TXT_FI = [DynText("label", 8, -42, 7.0, fett=True), DynText("comment", 8, -30, 6.0),
          DynText("function", 8, -19, 6.0)]

KURZ_GERAET = {
    "stromstoßschalter": "SST", "stromstossschalter": "SST", "fernschalter": "SST",
    "treppenlicht": "TLZ", "treppenlichtzeitschalter": "TLZ", "treppenlichtautomat": "TLZ",
    "schütz": "K", "schuetz": "K", "installationsschütz": "K", "relais": "K",
    "zeitschaltuhr": "ZSU", "schaltuhr": "ZSU", "dimmer": "DIM", "aktor": "AKT",
    "smart-home-aktor": "AKT", "lastabwurfrelais": "LAR", "lastabwurf": "LAR",
    "netzfreischalter": "NFS", "klingeltrafo": "TR", "trafo": "TR", "netzteil": "NT",
    "steckdose": "SD", "hutschienensteckdose": "SD", "energiezähler": "kWh", "zähler": "kWh",
}


def _norm(s) -> str:
    return str(s or "").strip()


def _art(e: dict) -> str:
    a = _norm(e.get("art") or e.get("schutzorgan")).lower().replace(" ", "")
    a = a.replace("-", "/") if a in ("fi-ls", "fi-ls-schalter") else a
    if a in ("fi", "rcd", "fi/rcd", "rccb", "fehlerstromschutzschalter", "fi-schalter"):
        return "FI"
    if a in ("fi/ls", "rcbo", "fils", "fi/ls/schalter", "fi-ls", "fi/ls(rcbo)", "fi-ls(rcbo)"):
        return "FILS"
    if a in ("ls", "mcb", "leitungsschutzschalter", "ls-schalter", "sicherungsautomat"):
        return "LS"
    if a in ("hauptschalter", "lasttrennschalter", "hs"):
        return "HS"
    if a in ("spd", "überspannungsschutz", "ueberspannungsschutz", "üsg", "usg", "ableiter"):
        return "SPD"
    if a in ("sls", "slsschalter", "selektiverhauptleitungsschutzschalter"):
        return "SLS"
    if a in ("sicherung", "neozed", "diazed", "nh", "schmelzsicherung", "nh-sicherung",
             "neozed-sicherung", "diazed-sicherung"):
        return "SICH"
    if a in ("trenner", "trennschalter"):
        return "TR"
    if a in ("zähler", "zaehler", "kwh", "energiezähler"):
        return "ZAE"
    if a in ("abzweig", "verteilerklemme", "abzweigklemme", "ungesichert"):
        return "ABZ"     # Abzweig ohne Schutzorgan direkt von der Schiene/Verteilerklemme
    return "GERAET"


def adern_zahl(adern: str) -> int | None:
    m = re.match(r"\s*(\d+)\s*[x×*]", _norm(adern))
    return int(m.group(1)) if m else None


def markierung(adern: str, pen: bool = False) -> dict:
    """Leitermarkierungen der einpoligen Darstellung aus der Aderzahl."""
    n = adern_zahl(adern)
    return {2: dict(phasen=1, neutral=True), 3: dict(phasen=1, neutral=True, schutz=True),
            4: dict(phasen=3, schutz=True), 5: dict(phasen=3, neutral=True, schutz=True)}.get(n, {})


def _zahl(v) -> str:
    s = _norm(v)
    return s[:-2] if s.endswith(".0") else s.replace(".", ",")


def _pol(v) -> str:
    """Polzahl als Kurztext: "1" → "", "3" → "3p", "1+N" → "1+N"."""
    p = _zahl(v)
    if p in ("", "1"):
        return ""
    return p if "+" in p else f"{p}p"


def _schutz_text(e: dict) -> str:
    art = _art(e)
    char, In = _norm(e.get("char")).upper(), _zahl(e.get("in"))
    pole = _zahl(e.get("pole"))
    if art in ("LS", "FILS", "SLS"):
        t = f"{char}{In}" if char else (f"{In} A" if In else "")
        if art == "SLS":
            t = f"SLS {char} {In} A".replace("  ", " ")
        if _pol(pole):
            t += f" {_pol(pole)}"
        return t
    if art == "FI":
        idn = _zahl(e.get("idn")) or "30"
        return f"{In}A/{idn}mA" if In else f"{idn} mA"
    if art == "SPD":
        return _norm(e.get("typ")) or "SPD"
    if art == "HS":
        return f"{In} A" + (f" {_pol(pole)}" if _pol(pole) else "") if In else ""
    if art == "SICH":
        return f"{_norm(e.get('typ') or char)} {In} A".strip() if In else ""
    return _norm(e.get("typ")) or (f"{In} A" if In else "")


def _fi_typ_text(e: dict) -> str:
    t = _norm(e.get("fi_typ") or e.get("fityp"))
    pole = _zahl(e.get("pole"))
    teile = []
    if t:
        teile.append(f"Typ {t}")
    if _pol(pole):
        teile.append(_pol(pole))
    return " ".join(teile)


def _phase_text(e: dict) -> str:
    p = _norm(e.get("phase"))
    if p:
        return p
    if _zahl(e.get("pole")) in ("3", "4", "3+N"):
        return "L1–L3"
    return ""


def _leitung_text(e: dict) -> str:
    l, a = _norm(e.get("leitung")), _norm(e.get("adern"))
    a = a.replace("x", "×").replace("*", "×")
    return f"{l} {a}".strip()


def _laenge_text(e: dict) -> str:
    v = _zahl(e.get("laenge") or e.get("länge"))
    return f"{v} m" if v else ""


# --------------------------------------------------------------------------
@dataclass
class Spalte:
    art: str                    # SPD, FI (FI ohne LS), LS, FILS
    eintrag: dict
    fi: dict | None = None      # vorgeschalteter FI (nur LS)
    geraete: list = field(default_factory=list)


@dataclass
class Gruppe:
    kopf: dict | None           # FI-Eintrag, SPD-Eintrag oder None (direkt an der Schiene)
    spalten: list[Spalte]


def gruppieren(eintraege: list[dict]):
    """Einspeisungsgeräte, Gruppen (FI mit seinen LS, SPD, einzelne LS) bestimmen."""
    einsp, gruppen = [], []
    fis = {_norm(e.get("bmk")): e for e in eintraege if _art(e) == "FI"}
    unter_fi: dict[str, list[dict]] = {k: [] for k in fis}
    geraete_fuer: dict[str, list[dict]] = {}
    for e in eintraege:
        if _art(e) == "GERAET" and _norm(e.get("vor") or e.get("ls")):
            geraete_fuer.setdefault(_norm(e.get("vor") or e.get("ls")), []).append(e)
    def nachgeschaltet(k: dict) -> list:
        eigene = k.get("geraete") if isinstance(k.get("geraete"), list) else []
        if isinstance(k.get("geraet"), dict):
            eigene = eigene + [k["geraet"]]
        return geraete_fuer.get(_norm(k.get("bmk")), []) + eigene

    reihenfolge = []
    for e in eintraege:
        art = _art(e)
        bmk = _norm(e.get("bmk"))
        pos = _norm(e.get("position")).lower()
        if pos in ("einspeisung", "vor_hauptschalter", "vorhauptschalter", "vor hauptschalter") or (
                art in ("HS", "ZAE", "SLS", "TR") and pos != "abgang") or (
                art == "SICH" and pos != "abgang" and not _norm(e.get("verbraucher"))):
            einsp.append(e)
            continue
        if art == "GERAET" and _norm(e.get("vor") or e.get("ls")):
            continue
        fi = _norm(e.get("fi"))
        if art in ("LS", "GERAET", "SICH") and fi:
            if fi not in fis:
                raise ValueError(f"{bmk}: vorgeschalteter FI {fi!r} steht nicht in der Liste")
            unter_fi[fi].append(e)
            continue
        reihenfolge.append(e)
    for e in reihenfolge:
        art = _art(e)
        bmk = _norm(e.get("bmk"))
        if art == "FI":
            kinder = unter_fi.get(bmk, [])
            if kinder:
                sp = [Spalte("LS", k, e, nachgeschaltet(k)) for k in kinder]
            else:
                sp = [Spalte("FI", e)]
            gruppen.append(Gruppe(e, sp))
        elif art == "SPD":
            gruppen.append(Gruppe(e, [Spalte("SPD", e)]))
        else:
            gruppen.append(Gruppe(None, [Spalte("FILS" if art == "FILS" else "LS", e, None,
                                                nachgeschaltet(e))]))
    return einsp, gruppen


# --------------------------------------------------------------------------
def _passend(text: str, laenge: float, pt: float = 6.5, min_pt: float = 5.0):
    """Text auf eine Länge bringen: erst verkleinern, dann umbrechen."""
    if not text:
        return [], pt
    p = pt
    while p > min_pt and textbreite(text, p) > laenge:
        p -= 0.5
    if textbreite(text, p) <= laenge:
        return [text], p
    worte, zeilen, akt = text.split(), [], ""
    for w in worte:
        probe = f"{akt} {w}".strip()
        if textbreite(probe, p) <= laenge or not akt:
            akt = probe
        else:
            zeilen.append(akt)
            akt = w
    zeilen.append(akt)
    return zeilen[:2], p


def baue(daten: dict, fmt: Format) -> Projekt:
    eintraege = daten.get("schutzorgane") or daten.get("stromkreise") or []
    if not eintraege:
        raise ValueError("Keine Schutzorgane/Stromkreise angegeben")
    einsp_geraete, gruppen = gruppieren(eintraege)
    # einpolig: Geräte vor dem Hauptschalter (SPD, Abzweige) vorn an der Schiene zeichnen
    vor = [e for e in einsp_geraete if _art(e) in ("SPD", "ABZ")]
    einsp_geraete = [e for e in einsp_geraete if e not in vor]
    gruppen = [Gruppe(e, [Spalte("SPD", e)]) if _art(e) == "SPD" else
               Gruppe(None, [Spalte("LS", e)]) for e in vor] + gruppen
    proj = daten.get("projekt", {})
    vt = daten.get("verteiler", {})
    ein = daten.get("einspeisung", {})
    vt_name = _norm(vt.get("name") or vt.get("bezeichnung")) or "Unterverteilung"
    felder = dict(
        kunde=_norm(proj.get("kunde")), objekt=_norm(proj.get("objekt")),
        auftrag=_norm(proj.get("auftrag")), datum=_norm(proj.get("datum")),
        bearbeiter=_norm(proj.get("bearbeiter")) or _firma.bearbeiter(),
        indexrev=_norm(proj.get("revision")) or "A",
        anlage=" · ".join(x for x in [vt_name,
                                       f"Standort: {_norm(vt.get('standort'))}" if vt.get("standort") else "",
                                       f"Netz: {_norm(vt.get('netz') or ein.get('netz'))}"
                                       if (vt.get("netz") or ein.get("netz")) else ""] if x),
        plantyp="Übersichtsschaltplan · einpolige Darstellung nach DIN EN 60617",
    )
    titel = _norm(daten.get("titel")) or f"Verteilerplan {vt_name}"
    x_rechts = fmt.zeichenflaeche()[0] + fmt.zeichenflaeche()[2]
    # Spaltenbreite: 50 px (12,5 mm); passt alles auf ein Blatt, breiter bis 80 px
    global SPALTE
    SPALTE = 50
    kap = int((x_rechts - X_KOPF_ENDE) // SPALTE)
    gesamt = sum(len(g.spalten) for g in gruppen)
    if gesamt <= kap - 1:
        SPALTE = int(max(50, min(80, (x_rechts - X_KOPF_ENDE - 30) // gesamt // 10 * 10)))
        kap = int((x_rechts - X_KOPF_ENDE) // SPALTE)

    # Gruppen auf Blätter verteilen (Gruppen werden nicht geteilt)
    blaetter_gruppen, akt, belegt = [], [], 0
    for g in gruppen:
        n = len(g.spalten)
        if n > kap - 1:
            raise ValueError(f"FI {_norm((g.kopf or {}).get('bmk'))} hat {n} Stromkreise – "
                             f"passt nicht auf ein Blatt ({kap - 1} Spalten). A3 quer wählen "
                             "oder Gruppe teilen.")
        reserve = 1  # Platz für den Verweis aufs nächste Blatt
        if belegt + n > kap - reserve and akt:
            blaetter_gruppen.append(akt)
            akt, belegt = [], 0
        akt.append(g)
        belegt += n
    if akt:
        blaetter_gruppen.append(akt)

    projekt = Projekt(titel)
    n_bl = len(blaetter_gruppen)
    for nr, gr in enumerate(blaetter_gruppen, 1):
        bl = Blatt(fmt, titel, dict(felder))
        _blatt(bl, gr, einsp_geraete if nr == 1 else None, ein, nr, n_bl, x_rechts)
        projekt.blaetter.append(bl)
    return projekt


def _blatt(bl: Blatt, gruppen: list[Gruppe], einsp_geraete, ein: dict, nr: int, n_bl: int,
           x_rechts: float):
    fmt = bl.format
    fx, fy, fw, fh = fmt.zeichenflaeche()
    y_unten = fy + fh

    # ---- Einspeisung -------------------------------------------------------
    if einsp_geraete is not None:
        start = bl.setze(symbol("einspeisung"), X_EINSP, Y_EINSP)
        zeilen = [f"Einspeisung von {_norm(ein.get('von')) or 'Zählerplatz'}"]
        lt = _leitung_text(ein)
        if lt:
            zeilen.append(lt + (" mm²" if "mm" not in lt and lt[-1:].isdigit() else "")
                          + (f", {_laenge_text(ein)}" if _laenge_text(ein) else ""))
        if _norm(ein.get("vorsicherung")):
            zeilen.append(f"Vorsicherung: {_norm(ein.get('vorsicherung'))}")
        if _norm(ein.get("netz")):
            zeilen.append(f"Netz: {_norm(ein.get('netz'))}")
        bl.text(X_EINSP + 12, Y_EINSP - 12, "\n".join(zeilen), 6.5)
        kette = einsp_geraete[:2]
        if len(einsp_geraete) > 2:
            raise ValueError("Höchstens zwei Geräte in der Einspeisung (z. B. Zähler + Hauptschalter)")
        mitten = {0: [], 1: [150], 2: [115, 185]}[len(kette)]
        vorher, vt = start, "1"
        mark = markierung(_norm(ein.get("adern")) or "5×", bool(ein.get("pen")))
        for e, ym in zip(kette, mitten):
            art = _art(e)
            sym = {"HS": symbol("hauptschalter"), "ZAE": symbol("zaehler"), "SLS": symbol("ls"),
                   "SICH": symbol("sicherung"), "TR": symbol("trenner")}.get(art, symbol("kasten"))
            b = bl.setze(sym, X_EINSP, ym, label=_norm(e.get("bmk")), comment=_schutz_text(e),
                         function=_norm(e.get("bemerkung")))
            bl.verbinde(vorher, vt, b, "1", **(mark if vorher is start else {}))
            vorher, vt = b, "2"
        schiene_start, schiene_t = vorher, vt
        bus_mark = mark if vorher is start else {}
    else:
        schiene_start = bl.setze(symbol("schiene_anfang", text=f"von Blatt {nr - 1}"),
                                 X_KOPF_ENDE - 20, Y_SCHIENE)
        schiene_t = "1"
        bus_mark = {}

    # ---- Spalten ---------------------------------------------------------------
    x = X_KOPF_ENDE + SPALTE / 2
    abzweige = []                     # (bauteil, anschluss) an der Hauptschiene, links → rechts
    spalten_info = []                 # (x, Spalte) für die Tabelle
    for g in gruppen:
        if g.kopf is not None and _art(g.kopf) == "SPD":
            e = g.kopf
            b = bl.setze(symbol("spd"), x, Y_REIHE1, label=_norm(e.get("bmk")),
                         comment=_schutz_text(e), function=_fi_typ_text(e) if e.get("pole") else "")
            pe = bl.setze(symbol("erde"), x, Y_UNTERSCHIENE, label="PE")
            bl.verbinde(b, "2", pe, "1")
            abzweige.append((b, "1"))
            spalten_info.append((x, g.spalten[0]))
            x += SPALTE
            continue
        if g.kopf is not None:                       # FI-Gruppe
            e = g.kopf
            fi = bl.setze(symbol("fi"), x, Y_REIHE1, label=_norm(e.get("bmk")),
                          comment=_schutz_text(e), function=_fi_typ_text(e))
            fi.texte = TXT_FI
            abzweige.append((fi, "1"))
            if g.spalten[0].art == "FI":             # FI ohne LS: direkter Abgang
                ab = bl.setze(symbol("abgang"), x, Y_ABGANG)
                bl.verbinde(fi, "2", ab, "1", **markierung(_norm(e.get("adern"))))
                spalten_info.append((x, g.spalten[0]))
                x += SPALTE
                continue
            vorher, vt = fi, "2"
            for i, sp in enumerate(g.spalten):
                ls = _stromkreis(bl, sp, x)
                if i == 0:
                    bl.verbinde(vorher, vt, ls, "1")
                else:
                    bl.verbinde(vorher, vt, ls, "1",
                                ueber=[(x - SPALTE, Y_UNTERSCHIENE), (x, Y_UNTERSCHIENE)])
                vorher, vt = ls, "1"
                spalten_info.append((x, sp))
                x += SPALTE
            continue
        sp = g.spalten[0]                            # LS / FI-LS direkt an der Schiene
        ls = _stromkreis(bl, sp, x)
        abzweige.append((ls, "1"))
        spalten_info.append((x, sp))
        x += SPALTE

    # ---- Sammelschiene (Kette über die Abzweige) ---------------------------------
    vorher, vt = schiene_start, schiene_t
    for i, (b, t) in enumerate(abzweige):
        bx, _ = b.pos(t)
        if i == 0:
            px, py = vorher.pos(vt)
            ueber = [(px, Y_SCHIENE), (bx, Y_SCHIENE)] if py != Y_SCHIENE else [(bx, Y_SCHIENE)]
            bl.verbinde(vorher, vt, b, t, ueber=ueber, **bus_mark)
        else:
            px, _ = vorher.pos(vt)
            bl.verbinde(vorher, vt, b, t, ueber=[(px, Y_SCHIENE), (bx, Y_SCHIENE)])
        vorher, vt = b, t
    x_ende = x - SPALTE / 2
    if nr < n_bl:
        weiter = bl.setze(symbol("verweis", text=f"weiter Blatt {nr + 1}"), x_ende + 30, Y_SCHIENE)
        px, _ = vorher.pos(vt)
        bl.verbinde(vorher, vt, weiter, "1", ueber=[(px, Y_SCHIENE)])
    x_start = X_EINSP if einsp_geraete is not None else X_KOPF_ENDE - 20
    bl.text(x_start + 6, Y_SCHIENE - 3, "L1, L2, L3, N, PE", 6, v="unten")

    # ---- Tabelle ----------------------------------------------------------------
    _tabelle(bl, spalten_info, fx, Y_TABELLE, y_unten, x_ende + SPALTE / 2)


def _stromkreis(bl: Blatt, sp: Spalte, x: float):
    """Schutzorgan in Zeile 2, optional Gerät in Zeile 3, Abgang. Gibt das Schutzorgan zurück."""
    e = sp.eintrag
    art = _art(e)
    if art == "FILS":
        ls = bl.setze(symbol("fils"), x, Y_REIHE2, label=_norm(e.get("bmk")),
                      comment=_schutz_text(e))
        ls.texte = TXT_FI[:2]
    elif art in ("SICH", "HS", "TR"):              # HS/TR nur hier, wenn position = abgang
        sym = {"SICH": "sicherung", "HS": "hauptschalter", "TR": "trenner"}[art]
        ls = bl.setze(symbol(sym), x, Y_REIHE2, label=_norm(e.get("bmk")),
                      comment=_schutz_text(e))
    elif art == "ABZ":                             # ungesicherter Abzweig: nur Klemme
        ls = bl.setze(symbol("klemme"), x, Y_REIHE2, label=_norm(e.get("bmk")) or "ungesichert")
    else:
        ls = bl.setze(symbol("ls"), x, Y_REIHE2, label=_norm(e.get("bmk")), comment=_schutz_text(e))
    letzter, lt = ls, "2"
    if sp.geraete:
        g = sp.geraete[0]
        name = _norm(g.get("art") or g.get("text"))
        kurz = _norm(g.get("kurz")) or KURZ_GERAET.get(name.lower().replace(" ", ""), name[:4])
        gb = bl.setze(symbol("kasten", text=kurz), x, Y_REIHE3, label=_norm(g.get("bmk")),
                      comment=_norm(g.get("typ")))
        bl.verbinde(ls, "2", gb, "1")
        letzter, lt = gb, "2"
    ab = bl.setze(symbol("abgang"), x, Y_ABGANG)
    bl.verbinde(letzter, lt, ab, "1", **markierung(_norm(e.get("adern"))))
    return ls


def _fi_schutz_text(sp: Spalte) -> str:
    e = sp.eintrag
    if sp.fi:
        return _norm(sp.fi.get("bmk"))
    if sp.art in ("FILS", "FI"):
        return f"{_zahl(e.get('idn')) or '30'} mA"
    return "–"


def _tabelle(bl: Blatt, spalten, x_links, y0, y_unten, x_rechts):
    zeilen = [("BMK", 20), ("Schutzorgan", 20), ("FI-Schutz", 20), ("Phase", 20),
              ("Leitung / Länge", 110), ("Verbraucher / Raum", 0)]
    rest = y_unten - y0 - sum(h for _, h in zeilen)
    zeilen[-1] = (zeilen[-1][0], rest)
    # Rahmen und Kopfspalte
    y = y0
    bl.linie(x_links, y0, x_rechts, y0, breite=1.5)
    for name, h in zeilen:
        bl.text(x_links + 4, y + (10 if h <= 20 else 8), name, 6, v="mitte" if h <= 20 else "oben",
                fett=True)
        y += h
        if y < y_unten - 0.5:
            bl.linie(x_links, y, x_rechts, y, breite=0.5)
    bl.linie(X_KOPF_ENDE, y0, X_KOPF_ENDE, y_unten, breite=1.0)
    bl.linie(x_rechts, y0, x_rechts, y_unten, breite=1.0)
    for i, (x, sp) in enumerate(spalten):
        xl = x - SPALTE / 2
        if i:
            bl.linie(xl, y0, xl, y_unten, breite=0.5)
        e = sp.eintrag
        art = sp.art
        y = y0
        werte = {
            "BMK": _norm(e.get("bmk")),
            "Schutzorgan": _schutz_text(e) if art != "FI" else _schutz_text(e),
            "FI-Schutz": _fi_schutz_text(sp),
            "Phase": _phase_text(e) or ("L1–L3, N" if art == "SPD" else ""),
        }
        for name, h in zeilen:
            if name in werte:
                txt = werte[name]
                pt = 6.5 if name == "BMK" else 6
                while pt > 4.5 and textbreite(txt, pt, name == "BMK") > SPALTE - 6:
                    pt -= 0.5
                if txt:
                    bl.text(x, y + h / 2, txt, pt, h="mitte", v="mitte", fett=name == "BMK")
            elif name == "Leitung / Länge":
                lt = _leitung_text(e) if art != "SPD" else ""
                teile = [t for t in (lt, _laenge_text(e)) if t]
                if teile:
                    z, pt = _passend(lt, h - 10) if lt else ([], 6.5)
                    text = "\n".join(z + ([_laenge_text(e)] if _laenge_text(e) else []))
                    bl.text(x, y + h - 5, text, pt, h="links", v="mitte", rot=270)
            else:
                verb = _norm(e.get("verbraucher")) or (
                    "Überspannungsschutz" if art == "SPD" else "")
                raum = _norm(e.get("raum"))
                z1, pt1 = _passend(verb, h - 10, 6.5)
                text = "\n".join(z1[:2] + ([raum] if raum else []))
                if text:
                    bl.text(x, y + h - 5, text, pt1, h="links", v="mitte", rot=270)
            y += h


# --------------------------------------------------------------------------
# Fachliche Plausibilität (nur Hinweise – Bemessung bleibt Sache des Elektrikers)
# --------------------------------------------------------------------------
# Typische Höchstwerte LS-Nennstrom je Cu-Querschnitt (Verlegeart C, ohne Häufung),
# angelehnt an DIN VDE 0298-4 / VDE 0100-430. Nur zur Erkennung von Tippfehlern.
_MAX_LS_1P = {1.0: 10, 1.5: 16, 2.5: 25, 4: 32, 6: 40, 10: 63, 16: 80, 25: 100}
_MAX_LS_3P = {1.0: 10, 1.5: 16, 2.5: 20, 4: 32, 6: 40, 10: 50, 16: 63, 25: 80}


def _querschnitt(adern: str) -> float | None:
    m = re.match(r"\s*\d+\s*[x×*]\s*([\d,\.]+)", _norm(adern))
    return float(m.group(1).replace(",", ".")) if m else None


def plausibilitaet(daten: dict) -> list[str]:
    eintraege = daten.get("schutzorgane") or daten.get("stromkreise") or []
    out = []
    bmks = [_norm(e.get("bmk")) for e in eintraege]
    for b in sorted({b for b in bmks if b and bmks.count(b) > 1}):
        out.append(f"BMK {b} kommt mehrfach vor")
    fis = {_norm(e.get("bmk")): e for e in eintraege if _art(e) == "FI"}
    anzahl_je_fi = {}
    for e in eintraege:
        art = _art(e)
        bmk = _norm(e.get("bmk"))
        if art not in ("LS", "FILS", "SICH"):
            continue
        fi = _norm(e.get("fi"))
        if fi:
            anzahl_je_fi[fi] = anzahl_je_fi.get(fi, 0) + 1
        mit_fi = bool(fi) or art == "FILS"
        text = f"{_norm(e.get('verbraucher'))} {_norm(e.get('raum'))}".lower()
        if not mit_fi:
            if "steckdose" in text:
                out.append(f"{bmk}: Steckdosenstromkreis ohne FI – VDE 0100-410 (411.3.3): "
                           "30-mA-FI für Steckdosen bis 32 A prüfen")
            elif re.search(r"\bbad\b|dusche|wc", text):
                out.append(f"{bmk}: Stromkreis im Bad ohne FI – VDE 0100-701: 30-mA-FI prüfen "
                           "(Ausnahmen beachten)")
            elif re.search(r"außen|aussen|balkon|terrasse|garten|garage", text):
                out.append(f"{bmk}: Außenbereich ohne FI – 30-mA-FI prüfen (VDE 0100-410)")
        if fi and _zahl(fis.get(fi, {}).get("idn")) not in ("", "30", "10"):
            if "steckdose" in text:
                out.append(f"{bmk}: Steckdosen hinter {fi} mit IΔn {_zahl(fis[fi].get('idn'))} mA – "
                           "30 mA erforderlich")
        q = _querschnitt(_norm(e.get("adern")))
        try:
            In = float(_zahl(e.get("in")).replace(",", "."))
        except ValueError:
            In = None
        pole = _zahl(e.get("pole"))
        dreiphasig = pole in ("3", "3+N", "4")
        if q and In:
            tab = _MAX_LS_3P if dreiphasig else _MAX_LS_1P
            grenze = next((v for k, v in sorted(tab.items()) if abs(k - q) < 1e-6), None)
            if grenze and In > grenze:
                out.append(f"{bmk}: {_schutz_text(e)} an {_leitung_text(e)} – Strombelastbarkeit "
                           f"prüfen (typisch höchstens {grenze} A, Verlegeart/Häufung beachten)")
        n = adern_zahl(_norm(e.get("adern")))
        if n and dreiphasig and n < 4:
            out.append(f"{bmk}: {pole}-poliges Schutzorgan, aber Leitung mit {n} Adern")
        if n and pole in ("1", "1+N") and n >= 5:
            out.append(f"{bmk}: einpoliges Schutzorgan an {n}-adriger Leitung – richtig?")
    for fi, n in anzahl_je_fi.items():
        if n > 6:
            out.append(f"{fi}: {n} Stromkreise an einem FI – Ableitströme und Verfügbarkeit "
                       "prüfen, ggf. auf mehrere FI aufteilen")
    return out
