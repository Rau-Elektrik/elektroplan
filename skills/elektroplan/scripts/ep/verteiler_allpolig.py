"""Stromlaufplan der Verteilung in allpoliger Darstellung (aus der Stromkreisliste).

Aufbau wie im Schaltschrankbau üblich:
  unten links  Einspeiseklemmen X1: 1, 2, 3, N, PE → Hauptschalter → senkrecht nach oben
  oben         Hauptschienen L1, L2, L3, N
  darunter     FI (4-polig) mit eigenen Unterschienen L1, L2, L3, N
  darunter     LS je Stromkreis an seiner Phase
  unten        Abgangsklemmen je Stromkreis: L (fortlaufend nummeriert), N, PE;
               PE-Schiene direkt über den Klemmen
"""
from __future__ import annotations

from . import firma as _firma
from .blatt import Format
from .model import ASCENT, TEXT_RAND, Blatt, DynText, Projekt, schriftpx, textbreite
from .symbole import symbol
from .verteilerplan import (KURZ_GERAET, _art, _fi_typ_text, _laenge_text, _leitung_text, _norm,
                            _passend, _zahl, gruppieren)

Y_SCHIENE = {"L1": 45, "L2": 65, "L3": 85, "N": 105}
Y_FI = 190
Y_UNTER = {"L1": 255, "L2": 275, "L3": 295, "N": 315}
Y_LS = 385
Y_GERAET = 480       # die folgenden Höhen richten sich nach dem Blattformat (siehe baue)
Y_ZWEIG_L = 535
Y_ZWEIG_N = 555
ZONE = 115           # Beschriftungsfeld unter den Klemmen (Ziel, Raum, Leitung)
PHASEN = ("L1", "L2", "L3")
LEITER = ("L1", "L2", "L3", "N")
KLEMME_B = 20
LUECKE = 20          # Abstand zwischen den Klemmenblöcken zweier Stromkreise
EXTRA_FILS = 20      # FI/LS braucht links mehr Platz (Auslöserkasten + Beschriftung)
RAND_GRUPPE = 45     # zusätzlicher Platz links vor FI/Überspannungsschutz


def _bmk(e, praefix) -> str:
    b = _norm(e.get("bmk"))
    if b and praefix and not b.startswith(praefix):
        return praefix + b
    return b


def _pol_zahl(e) -> int:
    p = _zahl(e.get("pole"))
    return 3 if (p.startswith("3") or p == "4") else 1


def _wert_ls(e) -> str:
    char, In = _norm(e.get("char")).upper(), _zahl(e.get("in"))
    return f"{char}{In}A" if In else char


def _wert_fi(e) -> str:
    idn, In = _zahl(e.get("idn")) or "30", _zahl(e.get("in"))
    return f"{idn}mA/{In}A" if In else f"{idn}mA"


def links_beschriften(b, rechts_bis: float | None = None):
    """Beschriftung rechtsbündig links neben das Bauteil setzen."""
    x0 = b.symbol.grenzen()[0] if rechts_bis is None else rechts_bis
    neu = []
    for t in b.symbol.texte:
        wert = str(b.info.get(t.info, "")).split("\n")[0]
        w = textbreite(wert, t.pt, t.fett)
        neu.append(DynText(t.info, x0 - 4 - w - TEXT_RAND, t.y, t.pt, 0, t.fett))
    b.texte = neu


def _klemme(bl: Blatt, x: float, y: float, text: str):
    """Reihenklemme mit senkrechter, mittig sitzender Bezeichnung."""
    b = bl.setze(symbol("reihenklemme"), x, y, label=text)
    h = (ASCENT + 0.212) * schriftpx(6.0)
    w = textbreite(text, 6.0)
    b.texte = [DynText("label", -TEXT_RAND - h / 2, 20 + TEXT_RAND + w / 2, 6.0, 270)]
    return b


def _leiste(bl, x_klemme, y_kl, name):
    bl.text(x_klemme - 14, y_kl + 20, name, 6.5, h="rechts", v="mitte")


def _zielfeld(bl, x_erste_klemme, anzahl, y_kl, zeilen):
    """Beschriftungsfeld unter einem Klemmenblock: wohin die Klemmen führen.

    Bekannte Angaben (Verbraucher, Raum, Leitung) stehen senkrecht darin, lesbar von
    unten, oben bündig unter den Klemmen. Leere Felder bleiben zum Beschriften frei.
    """
    x0 = x_erste_klemme - KLEMME_B / 2
    w = anzahl * KLEMME_B
    y0 = y_kl + 40 + 3
    h = ZONE - 8
    bl.rechteck(x0, y0, w, h, breite=0.5, farbe="#A0A0A0")
    platz = h - 8
    fertig = []
    for z in zeilen:
        if not z:
            continue
        teile, pt = _passend(z, platz, 6.0, 5.0)
        fertig += [(t, pt) for t in teile]
    max_zeilen = max(1, int((w - 6) // 9))
    fertig = fertig[:max_zeilen]
    if fertig:
        # jede Zeile einzeln, damit alle oben direkt unter den Klemmen enden
        pt = min(p for _, p in fertig)
        abstand = 1.15 * schriftpx(pt)
        for i, (t, _) in enumerate(fertig):
            xm = x0 + w / 2 + (i - (len(fertig) - 1) / 2) * abstand
            bl.text(xm, y0 + 4, t, pt, h="rechts", v="mitte", rot=270)


class Kette:
    """Schiene als Kette von Leitungen über die Abgriffe (Knotenpunkte entstehen automatisch)."""

    def __init__(self, bl: Blatt, y: float, start, start_t: str):
        self.bl, self.y = bl, y
        self.vorher, self.vt = start, start_t

    def an(self, b, t: str):
        tx, _ = b.pos(t)
        px, _ = self.vorher.pos(self.vt)
        self.bl.verbinde(self.vorher, self.vt, b, t, ueber=[(px, self.y), (tx, self.y)])
        self.vorher, self.vt = b, t


def _kreis_breite(e) -> float:
    n_kl = max(1, int(e.get("klemmen", 1) or 1))
    extra = EXTRA_FILS if _art(e) == "FILS" else 0
    return n_kl * ((_pol_zahl(e) + 2) * KLEMME_B + LUECKE) + extra


def _gruppen_breite(g) -> float:
    if g.kopf is not None and _art(g.kopf) == "SPD":
        return RAND_GRUPPE + 60 + 60
    if g.kopf is not None:
        return RAND_GRUPPE + max(sum(_kreis_breite(sp.eintrag) for sp in g.spalten), 60 + 80)
    return _kreis_breite(g.spalten[0].eintrag)


def baue(daten: dict, fmt: Format) -> Projekt:
    eintraege = daten.get("schutzorgane") or daten.get("stromkreise") or []
    if not eintraege:
        raise ValueError("Keine Schutzorgane angegeben")
    einsp, gruppen = gruppieren(eintraege)
    proj, vt, ein = daten.get("projekt", {}), daten.get("verteiler", {}), daten.get("einspeisung", {})
    praefix = daten.get("bmk_praefix", "-")
    leiste = (praefix or "") + (_norm(daten.get("klemmleiste")) or "X1")
    vt_name = _norm(vt.get("name") or vt.get("bezeichnung")) or "Unterverteilung"
    titel = _norm(daten.get("titel_allpolig")) or f"Stromlaufplan {vt_name}"
    felder = dict(
        kunde=_norm(proj.get("kunde")), objekt=_norm(proj.get("objekt")),
        auftrag=_norm(proj.get("auftrag")), datum=_norm(proj.get("datum")),
        bearbeiter=_norm(proj.get("bearbeiter")) or _firma.bearbeiter(),
        indexrev=_norm(proj.get("revision")) or "A",
        anlage=" · ".join(x for x in [vt_name, f"Standort: {_norm(vt.get('standort'))}"
                                       if vt.get("standort") else "",
                                       f"Netz: {_norm(vt.get('netz') or ein.get('netz'))}"
                                       if (vt.get("netz") or ein.get("netz")) else ""] if x),
        plantyp="Stromlaufplan Verteilung · allpolige Darstellung · DIN EN 61082 / DIN EN 60617")

    # Phasen ohne Angabe reihum verteilen – wird als Hinweis gemeldet
    hinweise, zyklus = [], 0
    for g in gruppen:
        for sp in g.spalten:
            e = sp.eintrag
            if sp.art in ("LS", "FILS") and _pol_zahl(e) == 1 and not _norm(e.get("phase")):
                e["_phase_auto"] = PHASEN[zyklus % 3]
                hinweise.append(f"{_norm(e.get('bmk'))}: keine Phase angegeben – "
                                f"{PHASEN[zyklus % 3]} angenommen")
                zyklus += 1
    daten["_hinweise_allpolig"] = hinweise

    fx, fy, fw, fh = fmt.zeichenflaeche()
    x_rechts = fx + fw
    # Klemmleiste so hoch, dass darunter ein Beschriftungsfeld frei bleibt;
    # Querverbindungen, PE-Schiene und Geräte richten sich nach ihr
    global Y_GERAET, Y_ZWEIG_L, Y_ZWEIG_N, ZONE
    hoch = fh >= 900                     # A3 quer / A4 hoch
    ZONE = 115 if hoch else 75
    y_kl = fy + fh - 40 - ZONE - 5       # Oberkante der Klemmen
    y_pe = y_kl - 15
    Y_ZWEIG_L, Y_ZWEIG_N = y_kl - 50, y_kl - 35
    Y_GERAET = 480 if hoch else 450
    vor = [e for e in einsp if _art(e) in ("SPD", "ABZ")]   # vor dem Hauptschalter
    einsp = [e for e in einsp if e not in vor]
    x_start1 = fx + 60 + 5 * KLEMME_B + 90
    if vor:
        x_start1 = _vor_x(fx + 60, vor)["ende"]
    x_start = fx + 80

    blaetter, akt, x = [], [], x_start1
    for g in gruppen:
        w = _gruppen_breite(g)
        if x + w > x_rechts - 50 and akt:
            blaetter.append(akt)
            akt, x = [], x_start
        if x + w > x_rechts - 50:
            raise ValueError(f"Gruppe {_norm((g.kopf or g.spalten[0].eintrag).get('bmk'))} ist zu "
                             "breit für ein Blatt – A3 quer wählen oder Gruppe teilen")
        akt.append(g)
        x += w
    if akt:
        blaetter.append(akt)

    projekt = Projekt(titel)
    zaehler = {"klemme": int(daten.get("klemmen_start", 4)), "blatt_offset": int(daten.get("_blatt_offset", 0))}
    for nr, gr in enumerate(blaetter, 1):
        bl = Blatt(fmt, titel, dict(felder))
        _blatt(bl, gr, einsp if nr == 1 else None, ein, nr, len(blaetter), praefix, leiste,
               zaehler, x_start1 if nr == 1 else x_start, y_kl, y_pe, vor)
        projekt.blaetter.append(bl)
    return projekt


def _vor_x(xe, vor) -> dict:
    """x-Positionen der Geräte vor dem Hauptschalter (Vorschiene) und des Hauptschalters."""
    x = xe + 5 * KLEMME_B
    pos = {}
    for e in vor:
        if _art(e) == "SPD":
            pos[id(e)] = x + RAND_GRUPPE
            x += RAND_GRUPPE + 60 + 40
        else:
            pos[id(e)] = x + LUECKE + 20
            x += LUECKE + 20 + _kreis_breite(e)
    pos["hs"] = x + 70
    pos["ende"] = pos["hs"] + 60 + 70
    return pos


def _einspeisung(bl, einsp, ein, praefix, leiste, y_kl, y_pe, vor=(), zaehler=None):
    fx = bl.format.zeichenflaeche()[0]
    xe = fx + 60
    kl = {}
    for i, (name, text) in enumerate((("L1", "1"), ("L2", "2"), ("L3", "3"), ("N", "N"), ("PE", "PE"))):
        kl[name] = _klemme(bl, xe + i * KLEMME_B, y_kl, text)
    _leiste(bl, xe, y_kl, leiste)
    quellen = {p: (kl[p], "1") for p in LEITER}
    if vor:
        return _einspeisung_vor(bl, einsp, ein, praefix, leiste, y_kl, y_pe, vor, zaehler, xe, kl)
    ys = [y_pe - 75, y_pe - 165]
    for e, y in zip(einsp[:2], ys):
        art = _art(e)
        n4 = _zahl(e.get("pole")) in ("4", "3+N")
        if art == "HS":
            sym, pole = symbol("hauptschalter_n", pole=4 if n4 else 3), (4 if n4 else 3)
        elif art == "SLS":
            sym, pole = symbol("ls_n", pole=3), 3
        elif art in ("SICH", "TR"):
            sym, pole = symbol("sicherung_n", pole=3), 3
        else:
            continue
        In = _zahl(e.get("in"))
        wert = (f"SLS {_wert_ls(e)}" if art == "SLS" else f"{In}A") if In else ""
        b = bl.setze(sym, xe, y, label=_bmk(e, praefix), comment=wert)
        links_beschriften(b, rechts_bis=-26 if art == "HS" else -10)
        for i, p in enumerate(LEITER[:pole]):
            q, qt = quellen[p]
            bl.verbinde(q, qt, b, b.symbol.anschluesse[2 * i + 1].name)   # unten rein
            quellen[p] = (b, b.symbol.anschluesse[2 * i].name)             # oben raus
    # Angaben zur Zuleitung ins Beschriftungsfeld unter den Einspeiseklemmen
    zul = " ".join(x for x in (_norm(ein.get("leitung")), _norm(ein.get("adern"))) if x)
    info = ["Einspeisung" + (f" von {_norm(ein.get('von'))}" if ein.get("von") else "")]
    if zul:
        info.append(zul + (f", {_zahl(ein.get('laenge'))} m" if ein.get("laenge") else ""))
    if _norm(ein.get("vorsicherung")):
        info.append(f"Vorsicherung {_norm(ein.get('vorsicherung'))}")
    _zielfeld(bl, xe, 5, y_kl, info)
    ketten = {p: Kette(bl, Y_SCHIENE[p], *quellen[p]) for p in LEITER}
    return ketten, Kette(bl, y_pe, kl["PE"], "1")


def _einspeisung_vor(bl, einsp, ein, praefix, leiste, y_kl, y_pe, vor, zaehler, xe, kl):
    """X1 → Vorschiene (Überspannungsschutz, ungesicherte Abzweige) → Hauptschalter → Schienen."""
    from .verteilerplan import Spalte
    pos = _vor_x(xe, vor)
    zaehler["x_ende_klemmen"] = xe + 4.5 * KLEMME_B
    vk = {p: Kette(bl, Y_UNTER[p], kl[p], "1") for p in LEITER}     # Vorschiene
    pe = Kette(bl, y_pe, kl["PE"], "1")
    for e in vor:
        x = pos[id(e)]
        if _art(e) == "SPD":
            b = bl.setze(symbol("spd4"), x, Y_LS, label=_bmk(e, praefix),
                         comment=_norm(e.get("typ")) or "SPD")
            links_beschriften(b)
            for p in LEITER:
                vk[p].an(b, p)
            pe.an(b, "PE")
        else:
            _stromkreis(bl, Spalte("LS", e), x, vk, pe, praefix, leiste, zaehler, y_kl)
    # Hauptschalter
    hs = next((e for e in einsp if _art(e) in ("HS", "SLS", "SICH", "TR")), None)
    xq = pos["hs"]
    if hs is not None:
        art = _art(hs)
        n4 = _zahl(hs.get("pole")) in ("4", "3+N")
        pole = 4 if (n4 and art == "HS") else 3
        sym = (symbol("hauptschalter_n", pole=pole) if art == "HS" else
               symbol("ls_n", pole=3) if art == "SLS" else symbol("sicherung_n", pole=3))
        In = _zahl(hs.get("in"))
        wert = (f"SLS {_wert_ls(hs)}" if art == "SLS" else f"{In}A") if In else ""
        q = bl.setze(sym, xq, Y_FI, label=_bmk(hs, praefix), comment=wert)
        links_beschriften(q, rechts_bis=-26 if art == "HS" else -10)
        an = q.symbol.anschluesse
        ketten = {}
        for i, p in enumerate(LEITER[:pole]):
            vk[p].an(q, an[2 * i + 1].name)                                  # unten rein
            ketten[p] = Kette(bl, Y_SCHIENE[p], q, an[2 * i].name)            # oben raus
        if pole == 3:                                    # N am Hauptschalter vorbei
            k = bl.setze(symbol("knoten"), xq + 60, Y_UNTER["N"])
            vk["N"].an(k, "1")
            ketten["N"] = Kette(bl, Y_SCHIENE["N"], k, "2")
    else:
        ketten = {}
        for p in LEITER:
            k = bl.setze(symbol("knoten"), xq + 20 * LEITER.index(p), Y_UNTER[p])
            vk[p].an(k, "1")
            ketten[p] = Kette(bl, Y_SCHIENE[p], k, "2")
    zul = " ".join(x for x in (_norm(ein.get("leitung")), _norm(ein.get("adern"))) if x)
    info = ["Einspeisung" + (f" von {_norm(ein.get('von'))}" if ein.get("von") else "")]
    if zul:
        info.append(zul + (f", {_zahl(ein.get('laenge'))} m" if ein.get("laenge") else ""))
    if _norm(ein.get("vorsicherung")):
        info.append(f"Vorsicherung {_norm(ein.get('vorsicherung'))}")
    _zielfeld(bl, xe, 5, y_kl, info)
    bl.text(xe + 2 * KLEMME_B, Y_UNTER["L1"] - 6, "vor Hauptschalter", 6, v="unten")
    return ketten, pe


def _blatt(bl, gruppen, einsp, ein, nr, n_bl, praefix, leiste, zaehler, x0, y_kl, y_pe, vor=()):
    zaehler["x_ende_klemmen"] = None          # neues Blatt: Leistenbezeichnung neu setzen
    if einsp is not None:
        ketten, pe = _einspeisung(bl, einsp, ein, praefix, leiste, y_kl, y_pe, vor, zaehler)
    else:
        ketten = {}
        for p in LEITER:
            s = bl.setze(symbol("schiene_anfang", text=p), x0 - 40, Y_SCHIENE[p])
            ketten[p] = Kette(bl, Y_SCHIENE[p], s, "1")
        s = bl.setze(symbol("schiene_anfang", text="PE"), x0 - 40, y_pe)
        pe = Kette(bl, y_pe, s, "1")
        bl.text(x0 - 60, Y_SCHIENE["L1"] - 6, f"von Blatt {nr - 1 + zaehler.get('blatt_offset', 0)}", 6, v="unten")

    x = x0
    for g in gruppen:
        gx = x
        if g.kopf is not None and _art(g.kopf) == "SPD":
            e = g.kopf
            xs = x + RAND_GRUPPE
            b = bl.setze(symbol("spd4"), xs, Y_FI, label=_bmk(e, praefix),
                         comment=_norm(e.get("typ")) or "SPD")
            links_beschriften(b)
            for p in LEITER:
                ketten[p].an(b, p)
            pe.an(b, "PE")
            x = gx + _gruppen_breite(g)
            continue
        if g.kopf is not None:                                  # FI-Gruppe
            e = g.kopf
            xf = x + RAND_GRUPPE
            pole = 2 if _zahl(e.get("pole")) in ("2", "1+N") else 4
            fi = bl.setze(symbol("fi_n", pole=pole), xf, Y_FI, label=_bmk(e, praefix),
                          comment=_wert_fi(e), function=_fi_typ_text(e))
            links_beschriften(fi, rechts_bis=-38)
            if pole == 4:
                for i, p in enumerate(LEITER):
                    ketten[p].an(fi, str(2 * i + 1))
                unter = {p: Kette(bl, Y_UNTER[p], fi, str(2 * i + 2)) for i, p in enumerate(LEITER)}
            else:
                erste = g.spalten[0].eintrag
                ph = _norm(erste.get("phase")).upper() or erste.get("_phase_auto", "L1")
                ketten[ph].an(fi, "1")
                ketten["N"].an(fi, "3")
                ein_l = Kette(bl, Y_UNTER[ph], fi, "2")
                unter = {"L1": ein_l, "L2": ein_l, "L3": ein_l, "N": Kette(bl, Y_UNTER["N"], fi, "4")}
            xc = xf
            if g.spalten[0].art == "FI":                        # FI ohne LS: Abgang direkt
                quelle = ({p: (fi, str(2 * i + 2)) for i, p in enumerate(LEITER)} if pole == 4 else
                          {"L1": (fi, "2"), "N": (fi, "4")})
                _abgang(bl, g.spalten[0], xc, quelle, unter, pe, praefix, leiste, zaehler, y_kl,
                        phasen=list(PHASEN) if pole == 4 else ["L1"])
            else:
                for sp in g.spalten:
                    xc = _stromkreis(bl, sp, xc, unter, pe, praefix, leiste, zaehler, y_kl)
            x = gx + _gruppen_breite(g)
            continue
        # direkt an der Schiene: Platz für die Beschriftung links vor dem Schutzorgan
        vorne = LUECKE + (EXTRA_FILS if _art(g.spalten[0].eintrag) == "FILS" else 0)
        _stromkreis(bl, g.spalten[0], x + vorne, ketten, pe, praefix, leiste, zaehler, y_kl)
        x += _gruppen_breite(g)

    # Schienenenden: auf dem letzten Blatt Bezeichnung, sonst Verweis aufs nächste Blatt
    x_ende = x + 10
    for p in LEITER:
        sym = symbol("verweis", text=p) if nr < n_bl else symbol("schiene_ende", text=p)
        ketten[p].an(bl.setze(sym, x_ende, Y_SCHIENE[p]), "1")
    sym = symbol("verweis", text="PE") if nr < n_bl else symbol("schiene_ende", text="PE")
    pe.an(bl.setze(sym, x_ende, y_pe), "1")
    if nr < n_bl:
        bl.text(x_ende + 7, Y_SCHIENE["N"] + 8, f"weiter Blatt {nr + 1 + zaehler.get('blatt_offset', 0)}", 6, h="rechts")


def _stromkreis(bl, sp, x, schienen, pe, praefix, leiste, zaehler, y_kl) -> float:
    """Schutzorgan (bei x), optional Gerät, Klemmen. Gibt das x des nächsten Stromkreises zurück."""
    e = sp.eintrag
    art = _art(e)
    pole = _pol_zahl(e)
    phase = _norm(e.get("phase")).upper() or e.get("_phase_auto", "L1")
    phase = phase if phase in PHASEN else "L1"
    phasen = list(PHASEN) if pole == 3 else [phase]
    if art == "FILS":
        ls = bl.setze(symbol("fils2"), x, Y_LS, label=_bmk(e, praefix), comment=_wert_ls(e),
                      function=f"{_zahl(e.get('idn')) or '30'}mA {_norm(e.get('fi_typ'))}".strip())
        links_beschriften(ls, rechts_bis=-38)
        schienen[phase].an(ls, "1")
        schienen["N"].an(ls, "3")
        quelle = {phase: (ls, "2"), "N": (ls, "4")}
    elif art == "SICH":
        ls = bl.setze(symbol("sicherung_n", pole=pole), x, Y_LS, label=_bmk(e, praefix),
                      comment=f"{_zahl(e.get('in'))}A" if _zahl(e.get("in")) else "")
        links_beschriften(ls)
        for i, p in enumerate(phasen):
            schienen[p].an(ls, str(2 * i + 1))
        quelle = {p: (ls, str(2 * i + 2)) for i, p in enumerate(phasen)}
    elif art in ("HS", "TR"):                       # Lasttrennschalter als Abgang (position: abgang)
        ls = bl.setze(symbol("hauptschalter_n", pole=3), x, Y_LS, label=_bmk(e, praefix),
                      comment=f"{_zahl(e.get('in'))}A" if _zahl(e.get("in")) else "")
        links_beschriften(ls, rechts_bis=-26)
        an = ls.symbol.anschluesse
        phasen = list(PHASEN)
        for i, p in enumerate(phasen):
            schienen[p].an(ls, an[2 * i].name)
        quelle = {p: (ls, an[2 * i + 1].name) for i, p in enumerate(phasen)}
    elif art == "ABZ":                              # Abzweig ohne Schutzorgan: Klemmen direkt an der Schiene
        phasen = list(PHASEN) if pole == 3 else [phase]
        bl.text(x - 6, Y_LS, _norm(e.get("hinweis")) or "ungesichert", 6, h="rechts", v="mitte", rot=270)
        quelle = {}
        ls = None
    else:
        ls = bl.setze(symbol("ls_n", pole=pole), x, Y_LS, label=_bmk(e, praefix), comment=_wert_ls(e))
        links_beschriften(ls)
        for i, p in enumerate(phasen):
            schienen[p].an(ls, str(2 * i + 1))
        quelle = {p: (ls, str(2 * i + 2)) for i, p in enumerate(phasen)}
    if sp.geraete and pole == 1 and ls is not None:
        gd = sp.geraete[0]
        name = _norm(gd.get("art") or gd.get("text"))
        kurz = _norm(gd.get("kurz")) or KURZ_GERAET.get(name.lower().replace(" ", ""), name[:4])
        gb = bl.setze(symbol("kasten", text=kurz), x, Y_GERAET, label=_bmk(gd, praefix))
        w = textbreite(gb.info.get("label", ""), 7.0, True)
        gb.texte = [DynText("label", gb.symbol.grenzen()[0] - 4 - w - TEXT_RAND, -26, 7.0, 0, True)]
        q, qt = quelle[phase]
        bl.verbinde(q, qt, gb, "1")
        quelle[phase] = (gb, "2")
    _abgang(bl, sp, x, quelle, schienen, pe, praefix, leiste, zaehler, y_kl, phasen)
    return x + _kreis_breite(e)


def _abgang(bl, sp, x, quelle, schienen, pe, praefix, leiste, zaehler, y_kl, phasen):
    """Klemmenblöcke L…, N, PE unter dem Schutzorgan; weitere Blöcke über Querverbindungen."""
    e = sp.eintrag
    n_kl = max(1, int(e.get("klemmen", 1) or 1))
    # Beschriftung je Klemmenblock: "ziele" (Liste) oder Verbraucher/Raum/Leitung im ersten Block
    ziele = e.get("ziele") or []
    if isinstance(ziele, str):
        ziele = [ziele]
    leitung = " ".join(x for x in (_leitung_text(e), _laenge_text(e)) if x)
    erste = {}
    for k in range(n_kl):
        xb = x + k * ((len(phasen) + 2) * KLEMME_B + LUECKE)
        if k < len(ziele) and ziele[k]:
            ziel = ziele[k] if isinstance(ziele[k], dict) else {"verbraucher": ziele[k]}
            zeilen = [_norm(ziel.get("verbraucher") or ziel.get("text")), _norm(ziel.get("raum")),
                      " ".join(x for x in (_leitung_text(ziel), _laenge_text(ziel)) if x)]
        elif k == 0 and not ziele:
            zeilen = [_norm(e.get("verbraucher")), _norm(e.get("raum")), leitung]
        else:
            zeilen = []
        _zielfeld(bl, xb, len(phasen) + 2, y_kl, zeilen)
        # Leistenbezeichnung nur am Anfang eines Klemmenabschnitts (nicht in engen Lücken)
        ende_vorher = zaehler.get("x_ende_klemmen")
        if ende_vorher is None or (xb - KLEMME_B / 2) - ende_vorher > 30:
            _leiste(bl, xb, y_kl, leiste)
        zaehler["x_ende_klemmen"] = xb + (len(phasen) + 1.5) * KLEMME_B
        bloecke = []
        for i, p in enumerate(phasen):
            bloecke.append((p, _klemme(bl, xb + i * KLEMME_B, y_kl, str(zaehler["klemme"]))))
            zaehler["klemme"] += 1
        bloecke.append(("N", _klemme(bl, xb + len(phasen) * KLEMME_B, y_kl, "N")))
        kpe = _klemme(bl, xb + (len(phasen) + 1) * KLEMME_B, y_kl, "PE")
        for i, (p, kb) in enumerate(bloecke):
            if k == 0:
                if p in quelle:
                    q, qt = quelle[p]
                    bl.verbinde(q, qt, kb, "1")
                else:                               # N bzw. ungesicherter Abzweig
                    schienen[p].an(kb, "1")
                erste[p] = kb
            else:
                y = Y_ZWEIG_N if p == "N" else Y_ZWEIG_L - 10 * (len(phasen) - 1 - i)
                vx, _ = erste[p].pos("1")
                nx, _ = kb.pos("1")
                bl.verbinde(erste[p], "1", kb, "1", ueber=[(vx, y), (nx, y)])
        pe.an(kpe, "1")
