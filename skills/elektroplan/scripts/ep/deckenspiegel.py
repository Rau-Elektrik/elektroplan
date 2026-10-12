"""Deckenspiegel mit Lichtberechnung (Wirkungsgradverfahren).

Je Raum: Nutzung → Wartungswert Ēm nach DIN EN 12464-1 (Wohnungen: Praxiswert),
Raumindex k = 2·A / (h·U), Raumwirkungsgrad ηR (Näherung), Wartungsfaktor MF.
Leuchten aus referenz/leuchten_katalog.json (LICHTZENTRALE Kernsortiment) werden nach
Ra, UGR, IP, Lichtfarbe, Montage und Raumgröße gefiltert, die Anzahl berechnet und im
Raster gesetzt. Ausgabe: Blatt 1 Deckenspiegel (Grundriss wie Installationsplan),
Blatt 2 ff. Lichtberechnung mit Alternativen und Stückliste.

Überschlagsrechnung – ersetzt keine Lichtberechnung mit Herstellerdaten (DIALux/Relux),
Uo und UGR werden nicht berechnet, sondern über Abstand und Katalogwerte plausibilisiert.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from .blatt import Format
from .model import Blatt, Projekt

REFERENZ = Path(__file__).resolve().parents[2] / "referenz"
ZEILE = 30
FARBE_OK = "#1E7B34"
FARBE_NEIN = "#B00020"
FARBE_GRAU = "#6E6E6E"
KENNUNGEN = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def _n(s) -> str:
    return str(s or "").strip()


def _z(v, std=0.0) -> float:
    if v in (None, ""):
        return std
    return float(str(v).replace(",", "."))


def _de(v: float, stellen=2) -> str:
    return f"{v:.{stellen}f}".replace(".", ",")


def _tsd(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


# --------------------------------------------------------------------------
# Daten laden
# --------------------------------------------------------------------------
def norm() -> dict:
    return json.loads((REFERENZ / "licht_din12464.json").read_text(encoding="utf-8"))


def katalog(daten: dict) -> tuple[dict, dict]:
    k = json.loads((REFERENZ / "leuchten_katalog.json").read_text(encoding="utf-8"))
    leuchten = {l["id"]: l for l in k["leuchten"]}
    licht = daten.get("licht") or {}
    for l in licht.get("katalog", []) or []:          # projektbezogene Leuchten
        leuchten[l["id"]] = {**leuchten.get(l["id"], {}), **l}
    empf = dict(k.get("empfehlung", {}))
    empf.update(licht.get("empfehlung", {}) or {})
    return leuchten, empf


def nutzung_fuer(name: str, angabe, n: dict, wohnung: bool) -> tuple[str | None, bool]:
    """Nutzungsschlüssel aus Angabe oder Raumname → (schlüssel, ist_annahme)."""
    if _n(angabe):
        key = _n(angabe).lower()
        if key not in n["nutzungen"]:
            raise ValueError(f"Licht: unbekannte Nutzung {angabe!r} – möglich: "
                             + ", ".join(sorted(n["nutzungen"])))
        return key, False
    low = name.lower()
    for muster, key in n["namen"]:
        if muster in low:
            if wohnung:
                key = n.get("wohnung_namen", {}).get(key, key)
            return key, any(a in low for a in n.get("annahme_namen", []))
    return None, True


# --------------------------------------------------------------------------
# Geometrie
# --------------------------------------------------------------------------
def flaeche(poly) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def umfang(poly) -> float:
    return sum(math.dist(a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def schwerpunkt(poly) -> tuple[float, float]:
    a = 0.0
    cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-9:
        return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
    return cx / (3 * a), cy / (3 * a)


def innen(poly, x, y) -> bool:
    drin = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            drin = not drin
    return drin


def randabstand(poly, x, y) -> float:
    best = 1e9
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        dx, dy = x1 - x0, y1 - y0
        l2 = dx * dx + dy * dy or 1e-12
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / l2))
        best = min(best, math.hypot(x - x0 - t * dx, y - y0 - t * dy))
    return best


def hauptwinkel(poly) -> float:
    """Richtung der längsten Kante (Grad, 0…90) – Raster folgt schrägen Räumen."""
    best, w = 0.0, 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        l = math.dist((x0, y0), (x1, y1))
        if l > best:
            best, w = l, math.degrees(math.atan2(y1 - y0, x1 - x0)) % 90
    return 0.0 if min(w, 90 - w) < 2 else w


def innerster_punkt(poly, schritt: float = 0.05):
    """Punkt im Raum mit dem größten Abstand zu den Wänden (bei Gleichstand nahe am Schwerpunkt)."""
    cx, cy = schwerpunkt(poly)
    x0, x1 = min(p[0] for p in poly), max(p[0] for p in poly)
    y0, y1 = min(p[1] for p in poly), max(p[1] for p in poly)
    best, bp = -1.0, (cx, cy)
    y = y0 + schritt / 2
    while y < y1:
        x = x0 + schritt / 2
        while x < x1:
            if innen(poly, x, y):
                g = round(randabstand(poly, x, y), 2) - 0.01 * math.hypot(x - cx, y - cy)
                if g > best:
                    best, bp = g, (x, y)
            x += schritt
        y += schritt
    return bp


def verteilen(poly, n: int, rand: float, schritt: float = 0.1):
    """n Punkte gleichmäßig über einen beliebigen Raum verteilen (k-Means über ein
    Stützpunktraster mit Wandabstand, deterministischer Start) → Punkte auf 5 cm gerundet."""
    x0, x1 = min(p[0] for p in poly), max(p[0] for p in poly)
    y0, y1 = min(p[1] for p in poly), max(p[1] for p in poly)
    stuetz = []
    for r in (rand, rand * 0.6, 0.0):
        stuetz = [(x0 + (i + 0.5) * schritt, y0 + (j + 0.5) * schritt)
                  for i in range(int((x1 - x0) / schritt) + 1) for j in range(int((y1 - y0) / schritt) + 1)]
        stuetz = [p for p in stuetz if innen(poly, *p) and randabstand(poly, *p) >= r]
        if len(stuetz) >= n * 3:
            break
    if not stuetz:
        return [schwerpunkt(poly)] * n
    zentren = [innerster_punkt(poly)]
    while len(zentren) < n:          # nächster Start: am weitesten entfernter Stützpunkt
        zentren.append(max(stuetz, key=lambda p: min(math.dist(p, z) for z in zentren)))
    for _ in range(40):
        gruppen = [[] for _ in zentren]
        for p in stuetz:
            gruppen[min(range(len(zentren)), key=lambda i: math.dist(p, zentren[i]))].append(p)
        neu = [(sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)) if g else z
               for g, z in zip(gruppen, zentren)]
        if max(math.dist(a, b) for a, b in zip(neu, zentren)) < 0.005:
            zentren = neu
            break
        zentren = neu
    out = []
    for z in zentren:   # Schwerpunkt außerhalb (konkave Ecke) → nächster Stützpunkt
        if not innen(poly, *z) or randabstand(poly, *z) < rand * 0.6:
            z = min(stuetz, key=lambda p: math.dist(p, z))
        out.append((round(z[0] * 20) / 20, round(z[1] * 20) / 20))
    return out


def textstelle(poly, belegt, abstand: float = 0.55):
    """Freie Stelle für den Raumtext: nahe der Mitte, weg von Leuchten und Wänden."""
    cx, cy = innerster_punkt(poly, 0.1)
    kandidaten = sorted(((cx + dx * 0.25, cy + dy * 0.25) for dx in range(-6, 7) for dy in range(-6, 7)),
                        key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
    best, bp = -1.0, (cx, cy)
    for x, y in kandidaten:
        if not innen(poly, x, y) or randabstand(poly, x, y) < 0.35:
            continue
        frei = min((math.hypot(x - px, y - py) for px, py in belegt), default=9.0)
        if frei >= abstand:
            return x, y
        if frei > best:
            best, bp = frei, (x, y)
    return bp


def _dreh(x, y, w):
    c, s = math.cos(w), math.sin(w)
    return x * c - y * s, x * s + y * c


def raster(poly, n: int, winkel: float, halbe_groesse: float, lang: bool, laenge: float = 0.0,
           s_max: float = 99.0):
    """Mindestens n Leuchten gleichmäßig im Raum verteilen – kleinste passende Anzahl,
    bei Gleichstand das gleichmäßigste Raster (Linearleuchten: in Längsrichtung gestreckt).
    → (punkte, abstand_m, längsrichtung_grad)"""
    w = math.radians(winkel)
    lok = [_dreh(x, y, -w) for x, y in poly]
    u0, u1 = min(p[0] for p in lok), max(p[0] for p in lok)
    v0, v1 = min(p[1] for p in lok), max(p[1] for p in lok)
    bu, bv = u1 - u0, v1 - v0
    laengs_u = bu >= bv
    laengs = winkel if laengs_u else winkel + 90
    rand = max(0.25, halbe_groesse + 0.15)
    ziel = 1.6 if lang else 1.0          # Zellverhältnis längs/quer
    if n == 1:                           # eine Leuchte: Punkt mit größtem Wandabstand (≈ Raummitte)
        p = innerster_punkt(poly)
        if randabstand(poly, *p) >= min(rand, 0.3):
            return [p], math.sqrt(flaeche(poly)), laengs
    if flaeche(poly) < 0.92 * bu * bv:   # schräger/verwinkelter Raum: gleichmäßige Flächenteilung
        a = flaeche(poly)
        while math.sqrt(a / n) > s_max * 1.05 and n < 60:
            n += 1
        return verteilen(poly, n, rand), math.sqrt(a / n), laengs
    beste = None
    for cu in range(1, 16):
        for cv in range(1, 16):
            if cu * cv < n or cu * cv > n * 3 + 4:
                continue
            su, sv = bu / cu, bv / cv
            if lang and laenge and (su if laengs_u else sv) < laenge + 0.2:
                continue
            zu_weit = max(su, sv) > s_max * 1.05      # Gleichmäßigkeit: Abstand begrenzen
            pts = []
            for i in range(cu):
                for j in range(cv):
                    pu, pv = u0 + (i + 0.5) * su, v0 + (j + 0.5) * sv
                    x, y = _dreh(pu, pv, w)
                    if innen(poly, x, y) and randabstand(poly, x, y) >= rand:
                        pts.append((x, y))
            if len(pts) < n:
                continue
            verh = (su / sv) if laengs_u else (sv / su)
            guete = (zu_weit, len(pts), abs(math.log(max(verh, 1e-6) / ziel)))
            if beste is None or guete < beste[0]:
                beste = (guete, pts, max(su, sv))
    if beste is None:   # sehr kleiner/verwinkelter Raum: Schwerpunkt
        return [schwerpunkt(poly)], max(bu, bv), laengs
    return beste[1], beste[2], laengs


# --------------------------------------------------------------------------
# Rechnung
# --------------------------------------------------------------------------
def eta_r(k: float, n: dict, reflexion: str, verteilung: str) -> float:
    t = n["raumwirkungsgrad"]
    ks, werte = t["k"], t.get(reflexion) or t["hell"]
    if k <= ks[0]:
        eta = werte[0] * k / ks[0]          # unterhalb der Tabelle linear gegen 0
    elif k >= ks[-1]:
        eta = werte[-1]
    else:
        i = next(i for i in range(len(ks) - 1) if ks[i] <= k <= ks[i + 1])
        f = (k - ks[i]) / (ks[i + 1] - ks[i])
        eta = werte[i] + f * (werte[i + 1] - werte[i])
    return eta * t.get("faktor_verteilung", {}).get(verteilung, 1.0)


def _groesse(l: dict) -> float:
    if l.get("laenge"):
        return _z(l["laenge"]) / 2
    if l.get("b"):
        return max(_z(l.get("b")), _z(l.get("t"))) / 2
    return _z(l.get("d"), 0.15) / 2


def eignung(l: dict, anf: dict, raum: dict) -> str | None:
    """None = geeignet, sonst Grund."""
    if l.get("auto") is False:
        return "keine Deckenleuchte"
    if anf.get("ra") and _z(l.get("ra")) < anf["ra"]:
        return f"Ra {l.get('ra')} < {anf['ra']}"
    if anf.get("rugl"):
        if l.get("ugr") is None and anf["rugl"] < 25:
            return f"UGR nicht angegeben (gefordert ≤ {anf['rugl']})"
        if l.get("ugr") is not None and _z(l["ugr"]) > anf["rugl"]:
            return f"UGR {l['ugr']} > {anf['rugl']}"
    ip = int(_z(raum.get("ip"), anf.get("ip", 0)))
    if ip and int(_z(l.get("ip"))) < ip:
        return f"IP{l.get('ip')} < IP{ip}"
    if anf.get("tcp"):
        lo, hi = anf["tcp"]
        if not any(lo <= t <= hi for t in l.get("tcp", [])):
            return f"Lichtfarbe {lo}–{hi} K nicht verfügbar"
    decke = _n(raum.get("decke")).lower()
    mont = _n(l.get("montage")) or "einbau"
    if decke in ("massiv", "beton", "anbau") and mont == "einbau":
        return "Einbauleuchte, Decke massiv"
    if l.get("nur_auf_wunsch") and not raum.get("pendel"):
        return "nur auf Wunsch"
    return None


def _variante(l, poly, a, u, h_lp, e_ziel, mf, n, reflexion, winkel, anzahl=None):
    k = 2 * a / (h_lp * u) if h_lp > 0 else 5.0
    eta = eta_r(k, n, reflexion, _n(l.get("verteilung")) or "direkt")
    if l.get("bauform") == "auslass":
        # Deckenauslass für die Kundenleuchte: Mindest-Lichtstrom je Leuchte berechnen
        laengste = max(math.dist(p1, p2) for p1, p2 in zip(poly, poly[1:] + poly[:1]))   # längste Wand
        anz = anzahl or max(1, math.ceil(a / _z(l.get("flaeche_je_auslass"), 18)),
                            math.ceil(laengste / 3.5 - 0.3))     # lange Räume: Auslass je ca. 3,5 m
        pts, s, laengs = raster(poly, anz, winkel, 0.15, False)
        lm_min = math.ceil(e_ziel * a / (len(pts) * eta * mf) / 50) * 50
        l2 = dict(l, lm=lm_min, w=round(lm_min / 100, 1),
                  name=f"Deckenauslass, Leuchte mind. {_tsd(lm_min)} lm")
        return {"leuchte": l2, "k": k, "eta": eta, "n_min": anz, "n": len(pts), "e": e_ziel,
                "punkte": pts, "abstand": s, "abstand_ok": True, "s_max": 99.0, "laengs": laengs,
                "w": len(pts) * l2["w"], "w_m2": len(pts) * l2["w"] / a, "auslass": True}
    lm = _z(l["lm"])
    n_min = anzahl or max(1, math.ceil(e_ziel * a / (lm * eta * mf)))
    lang = l.get("bauform") == "linear" or bool(l.get("b") and abs(_z(l["b"]) - _z(l.get("t"))) > 0.2)
    laenge = _z(l.get("laenge")) or max(_z(l.get("b")), _z(l.get("t")))
    s_max = _z(l.get("abstand_faktor"), 1.4) * h_lp
    pts, s, laengs = raster(poly, n_min, winkel, _groesse(l), lang, laenge if lang else 0.0, s_max)
    if anzahl:
        pts = pts[:anzahl]
    n_ist = len(pts)
    e_ist = n_ist * lm * eta * mf / a
    return {"leuchte": l, "k": k, "eta": eta, "n_min": n_min, "n": n_ist, "e": e_ist,
            "punkte": pts, "abstand": s, "abstand_ok": s <= s_max * 1.05, "s_max": s_max,
            "laengs": laengs, "w": n_ist * _z(l.get("w")), "w_m2": n_ist * _z(l.get("w")) / a}


def raeume(daten: dict) -> list[dict]:
    """Räume für die Lichtberechnung: 'lichtraeume' oder grundriss.raeume."""
    gr = daten.get("grundriss", {}) or {}
    rname = {_n(r.get("name")).lower(): r for r in gr.get("raeume", []) if _n(r.get("name"))}
    quelle = daten.get("lichtraeume")
    if quelle is None:
        quelle = [{"raum": r["name"]} for r in gr.get("raeume", []) if _n(r.get("name"))]
    out = []
    for d in quelle:
        d = dict(d)
        ref = rname.get(_n(d.get("raum")).lower()) if d.get("raum") else None
        if ref:
            d = {**{k: v for k, v in ref.items() if k not in ("x", "y", "b", "t", "polygon")}, **d,
                 "_aus_grundriss": _n(ref.get("name"))}
            x, y, b, t = (_z(ref.get(k)) for k in ("x", "y", "b", "t"))
            poly = [(x, y), (x + b, y), (x + b, y + t), (x, y + t)]
        elif d.get("polygon"):
            poly = [(_z(p[0]), _z(p[1])) for p in d["polygon"]]
        elif d.get("b"):
            x, y, b, t = (_z(d.get(k)) for k in ("x", "y", "b", "t"))
            poly = [(x, y), (x + b, y), (x + b, y + t), (x, y + t)]
        else:
            raise ValueError(f"Lichtraum {d}: 'raum' (Name aus grundriss.raeume), 'polygon' "
                             f"oder x/y/b/t angeben")
        d["name"] = _n(d.get("name") or d.get("raum")) or f"Raum {len(out) + 1}"
        d["_poly"] = poly
        out.append(d)
    return out


def berechne(daten: dict) -> dict:
    """Ergebnis je Raum (wird in daten['_licht'] zwischengespeichert)."""
    if daten.get("_licht"):
        return daten["_licht"]
    n = norm()
    leuchten, empf = katalog(daten)
    licht = daten.get("licht") or {}
    wohnung = bool(licht.get("wohnung"))
    mf = _z(licht.get("wartungsfaktor"), n.get("wartungsfaktor", 0.8))
    refl_std = _n(licht.get("reflexion")) or "hell"
    hoehe_std = _z(licht.get("deckenhoehe") or (daten.get("grundriss") or {}).get("deckenhoehe"), 2.50)
    stufe_std = _n(licht.get("stufe")) or "erforderlich"
    ergebnisse, hinweise = [], []
    for r in raeume(daten):
        name = r["name"]
        angabe = r.get("nutzung_licht") or r.get("licht_nutzung")
        if not angabe and isinstance(r.get("nutzung"), str) and _n(r["nutzung"]).lower() in n["nutzungen"]:
            angabe = r["nutzung"]
        key, annahme = nutzung_fuer(name, angabe, n, wohnung)
        if key is None:
            hinweise.append(f"{name}: Nutzung nicht erkannt – \"nutzung_licht\" angeben "
                            f"(z. B. buero, warteraum, untersuchung, flur, sanitaer)")
            continue
        anf = dict(n["nutzungen"][key])
        if annahme:
            hinweise.append(f"{name}: Nutzung angenommen als {anf['bereich']} "
                            f"({'DIN EN 12464-1 ' + anf['ref'] if anf['ref'] != 'Praxis' else 'Praxiswert'}) "
                            f"– bitte bestätigen oder \"nutzung_licht\" setzen")
        stufe = _n(r.get("stufe")) or stufe_std
        e_ziel = _z(r.get("ziel_lx")) or (anf.get("em_mod") if stufe.startswith("mod") and anf.get("em_mod")
                                         else anf["em"])
        poly = r["_poly"]
        a, u = flaeche(poly), umfang(poly)
        h_decke = _z(r.get("deckenhoehe"), hoehe_std)
        ebene = _z(r.get("nutzebene"), anf.get("ebene", 0.75))
        h_lp = max(0.3, h_decke - ebene)
        refl = _n(r.get("reflexion")) or refl_std
        winkel = _z(r.get("winkel")) if r.get("winkel") is not None else hauptwinkel(poly)
        if r.get("leuchte"):
            reihen = [r["leuchte"]]
        else:
            reihen = list(r.get("auswahl") or empf.get(key) or empf.get("standard", []))
        varianten, ausgeschlossen = [], []

        def pruefe_liste(liste):
            for lid in liste:
                l = leuchten.get(lid)
                if l is None:
                    raise ValueError(f"{name}: Leuchte {lid!r} nicht im Katalog")
                grund = None if r.get("leuchte") else eignung(l, anf, r)
                if not grund and not r.get("leuchte") and _z(l.get("min_raum")) > math.sqrt(a):
                    grund = "Raum zu klein"
                if grund:
                    ausgeschlossen.append((l, grund))
                    continue
                v = _variante(l, poly, a, u, h_lp, e_ziel, mf, n, refl, winkel,
                              int(r["anzahl"]) if r.get("anzahl") else None)
                v["ok"] = v["e"] >= e_ziel - 0.5
                varianten.append(v)

        pruefe_liste(reihen)
        if not r.get("leuchte") and not any(v["ok"] for v in varianten):   # Rückfall: allgemeine Liste
            pruefe_liste([i for i in empf.get("standard", []) if i not in reihen])
        if not varianten:
            hinweise.append(f"{name}: keine passende Leuchte im Katalog ("
                            + "; ".join(f"{l['name']}: {g}" for l, g in ausgeschlossen[:3]) + ")")
            continue
        gut = [v for v in varianten if v["ok"] and v["abstand_ok"]] or [v for v in varianten if v["ok"]]
        # Überdimensionierung vermeiden: erste passende Leuchte bis max_ueber × Sollwert,
        # sonst die mit der kleinsten Anschlussleistung
        ueber = _z(r.get("max_ueber") or licht.get("max_ueber"), 1.6)
        wahl = next((v for v in gut if v["e"] <= ueber * e_ziel), None) \
            or (min(gut, key=lambda v: v["w"]) if gut else varianten[0])
        alternativen = [v for v in varianten if v is not wahl and v["ok"]][:2]
        e = {"name": name, "nutzung": key, "anf": anf, "annahme": annahme, "e_ziel": e_ziel,
             "stufe": stufe, "a": a, "u": u, "h_decke": h_decke, "ebene": ebene, "h_lp": h_lp,
             "reflexion": refl, "winkel": winkel, "wahl": wahl, "alternativen": alternativen,
             "poly": poly, "stromkreis": _n(r.get("stromkreis")), "raum": r,
             "dali": bool(r.get("dali", licht.get("dali", False)))}
        ergebnisse.append(e)
        if not wahl["ok"]:
            hinweise.append(f"{name}: Ē ≈ {wahl['e']:.0f} lx < {e_ziel:.0f} lx mit {wahl['n']} × "
                            f"{wahl['leuchte']['name']} – Raum zu verwinkelt für das Raster, "
                            f"\"anzahl\" erhöhen oder Leuchten von Hand setzen")
        if not wahl["abstand_ok"]:
            hinweise.append(f"{name}: Leuchtenabstand {_de(wahl['abstand'])} m > {_de(wahl['s_max'])} m "
                            f"(≈ {wahl['leuchte'].get('abstand_faktor', 1.4)} × Höhe über Nutzebene) – "
                            f"Gleichmäßigkeit Uo ≥ {anf.get('uo', 0.4)} prüfen, ggf. mehr/kleinere Leuchten")
        if anf.get("hinweis"):
            hinweise.append(f"{name}: {anf['hinweis']}")
    # Kennbuchstaben je verwendetem Leuchtentyp
    kenn: dict[str, str] = {}
    for e in ergebnisse:
        lid = e["wahl"]["leuchte"]["id"]
        if lid not in kenn:
            kenn[lid] = KENNUNGEN[len(kenn) % len(KENNUNGEN)]
    res = {"raeume": ergebnisse, "hinweise": hinweise, "kennung": kenn, "mf": mf,
           "leuchten": leuchten, "wohnung": wohnung}
    daten["_licht"] = res
    return res


def hinweise(daten: dict) -> list[str]:
    if _n(daten.get("plan")).lower() not in ("deckenspiegel", "lichtplanung", "lichtplan"):
        return []
    res = berechne(daten)
    out = []
    for e in res["raeume"]:
        v = e["wahl"]
        ref = e["anf"]["ref"]
        quelle = "Praxiswert" if ref == "Praxis" else f"DIN EN 12464-1, {ref}"
        out.append(f"{e['name']}: {v['n']} × {res['kennung'][v['leuchte']['id']]} {v['leuchte']['name']} "
                   f"→ Ē ≈ {v['e']:.0f} lx (gefordert {e['e_ziel']:.0f} lx, {quelle}), "
                   f"{_de(v['w_m2'], 1)} W/m²")
    return out + res["hinweise"]


# --------------------------------------------------------------------------
# Zeichnen
# --------------------------------------------------------------------------
def _artnr(l: dict, dali: bool) -> str:
    """Art.-Nr. der Standard- bzw. DALI-Variante."""
    if dali and l.get("art_nr_dali"):
        return f"{l['art_nr_dali']} (DALI)"
    return _n(l.get("art_nr"))


def _umbruch(text: str, zeichen: int, zeilen: int = 2) -> str:
    out, akt = [], ""
    for wort in text.split():
        if len(akt) + len(wort) + 1 > zeichen and akt:
            out.append(akt)
            akt = wort
        else:
            akt = f"{akt} {wort}".strip()
    out.append(akt)
    if len(out) > zeilen:
        out = out[:zeilen]
        out[-1] = out[-1][:zeichen - 1] + "…"
    return "\n".join(out)


def _legname(kenn: str, l: dict) -> str:
    return f"{kenn}  {l['name']}"


def leuchten_geraete(daten: dict) -> tuple[list, list, list]:
    """Generierte Leuchten als Installationsplan-Elemente → (geraete, linien, texte, zusatz)."""
    res = berechne(daten)
    geraete, linien, texte, zusatz = [], [], [], {}
    beschriften = (daten.get("licht") or {}).get("beschriftung", True) is not False
    for e in res["raeume"]:
        v = e["wahl"]
        l = v["leuchte"]
        kenn = res["kennung"][l["id"]]
        leg = _legname(kenn, res["leuchten"].get(l["id"], l)) if v.get("auslass") else _legname(kenn, l)
        bau = l.get("bauform")
        for x, y in v["punkte"]:
            if bau == "linear" or (bau == "panel" and abs(_z(l.get("b")) - _z(l.get("t"))) > 0.2):
                laenge = _z(l.get("laenge")) or max(_z(l.get("b")), _z(l.get("t")))
                if bau == "panel":       # langes Panel: Umriss + Mittelpunkt
                    _umriss(linien, x, y, max(_z(l["b"]), _z(l["t"])), min(_z(l["b"]), _z(l["t"])),
                            v["laengs"])
                    geraete.append({"symbol": "leuchte", "x": x, "y": y, "legende": leg,
                                    "stromkreis": e["stromkreis"]})
                else:
                    linien.append({"art": "langfeld", "mitte": [x, y], "winkel": v["laengs"],
                                   "laenge": laenge, "name": leg})
            elif bau == "panel":
                _umriss(linien, x, y, _z(l["b"]), _z(l["t"]), v["laengs"])
                geraete.append({"symbol": "leuchte", "x": x, "y": y, "legende": leg,
                                "stromkreis": e["stromkreis"]})
            elif bau == "downlight":
                geraete.append({"symbol": "spot", "x": x, "y": y, "legende": leg,
                                "stromkreis": e["stromkreis"]})
            else:
                geraete.append({"symbol": "leuchte", "x": x, "y": y, "legende": leg,
                                "stromkreis": e["stromkreis"]})
        if beschriften:
            zeile = (f"{v['n']} × {kenn} ≥ {_tsd(_z(l['lm']))} lm" if v.get("auslass")
                     else f"{v['n']} × {kenn} · Ē ≈ {v['e']:.0f} lx (≥ {e['e_ziel']:.0f})")
            if e["raum"].get("_aus_grundriss"):
                zusatz[e["raum"]["_aus_grundriss"]] = zeile
            else:
                cx, cy = e["raum"].get("textpos") or textstelle(e["poly"], v["punkte"], 0.5 + _groesse(l))
                texte.append({"x": _z(cx), "y": _z(cy), "text": e["name"] + "\n" + zeile, "groesse": 6.5,
                              "fett": False, "farbe": FARBE_OK if v["ok"] else FARBE_NEIN})
    return geraete, linien, texte, zusatz


def _umriss(linien, x, y, lang, kurz, winkel):
    w = math.radians(winkel)
    ecken = [(-lang / 2, -kurz / 2), (lang / 2, -kurz / 2), (lang / 2, kurz / 2), (-lang / 2, kurz / 2),
             (-lang / 2, -kurz / 2)]
    pts = [[x + px * math.cos(w) - py * math.sin(w), y + px * math.sin(w) + py * math.cos(w)]
           for px, py in ecken]
    linien.append({"art": "umriss", "punkte": pts, "legende": False})


def _tabelle_kopf(bl, x0, y, spalten):
    xx = x0
    for name, w in spalten:
        bl.text(xx + 2, y, name, 6, fett=True)
        xx += w
    return y + 22


def _berechnungsblaetter(daten: dict, fmt: Format, titel: str, felder: dict) -> list[Blatt]:
    res = berechne(daten)
    fx, fy, fw, fh = fmt.zeichenflaeche(False)
    rand = 25
    x0, breite = fx + rand, fw - 2 * rand
    spalten = [("Raum", 120), ("Nutzung · Anforderung", 230), ("A m²", 42), ("h m", 40), ("k", 34),
               ("Ēm lx", 46), ("Ra/UGR/Uo", 70), ("Leuchte (Empfehlung)", 270), ("n", 28),
               ("Ē lx", 44), ("W/m²", 40), ("Abstand", 62), ("", 30)]
    rest = breite - sum(w for _, w in spalten)
    spalten.append(("Alternativen (erfüllen ebenfalls)", rest))
    blaetter = []
    zeilen = res["raeume"]
    pro_blatt = max(1, int((fh - 2 * rand - 420) // (ZEILE + 6)))
    teile = [zeilen[i:i + pro_blatt] for i in range(0, len(zeilen), pro_blatt)] or [[]]
    for nr, teil in enumerate(teile, 1):
        bl = Blatt(fmt, f"{titel} – Lichtberechnung" + (f" ({nr}/{len(teile)})" if len(teile) > 1 else ""),
                   raster_anzeigen=False)
        bl.text(x0, fy + rand, "Lichtberechnung je Raum (Wirkungsgradverfahren, Überschlag)", 9, fett=True)
        y = _tabelle_kopf(bl, x0, fy + rand + 26, spalten)
        bl.linie(x0, y - 6, x0 + breite, y - 6, breite=0.8)
        for e in teil:
            v = e["wahl"]
            l = v["leuchte"]
            anf = e["anf"]
            kenn = res["kennung"][l["id"]]
            ref = "Praxiswert (keine Norm)" if anf["ref"] == "Praxis" else f"DIN EN 12464-1, {anf['ref']}"
            werte = [
                e["name"],
                (anf["bereich"] if len(anf["bereich"]) <= 48 else anf["bereich"][:46] + "…")
                + f"\n{ref}" + (" – Annahme" if e["annahme"] else ""),
                _de(e["a"], 1), _de(e["h_lp"]), _de(v["k"]),
                f"{e['e_ziel']:.0f}" + ("*" if e["stufe"].startswith("mod") else ""),
                f"{anf.get('ra', '–')} / {anf.get('rugl') or '–'} / {_de(anf.get('uo', 0.4))}",
                f"{kenn}  {l['name']}\n{l.get('typ', '')}"
                + (f" · Art.-Nr. {_artnr(l, e['dali'])}" if _artnr(l, e["dali"]) else "")
                + f" · {_tsd(_z(l['lm']))} lm · {_de(_z(l['w']), 1)} W",
                str(v["n"]), f"{v['e']:.0f}", _de(v["w_m2"], 1),
                f"{_de(v['abstand'])} m" + ("" if v["abstand_ok"] else " !"),
            ]
            xx = x0
            mitte = y + ZEILE / 2
            for (sname, w), wert in zip(spalten, werte):
                rechts = sname in ("A m²", "h m", "k", "Ēm lx", "n", "Ē lx", "W/m²")
                farbe = FARBE_NEIN if (sname == "Abstand" and not v["abstand_ok"]) else "#000000"
                bl.text(xx + (w - 4 if rechts else 2), mitte, wert, 6 if "\n" not in wert else 5.5,
                        h="rechts" if rechts else "links", v="mitte", farbe=farbe,
                        fett=sname in ("Raum", "Ē lx"))
                xx += w
            ok = v["ok"]
            bl.text(xx + 15, mitte, "OK" if ok else "zu wenig", 6, h="mitte", v="mitte", fett=True,
                    farbe=FARBE_OK if ok else FARBE_NEIN)
            xx += spalten[-2][1]
            alt = "\n".join(f"{a['n']} × {a['leuchte']['name']} → {a['e']:.0f} lx" for a in e["alternativen"]) or "–"
            bl.text(xx + 2, mitte, alt, 5.5, v="mitte", farbe=FARBE_GRAU)
            y += ZEILE + 6
            bl.linie(x0, y - 3, x0 + breite, y - 3, breite=0.3, farbe="#BBBBBB")

        if nr == len(teile):
            y = _stueckliste(bl, x0, y + 18, breite, res)
            _fussnoten(bl, x0, max(y + 14, fy + fh - rand - 120), breite, res, daten)
        bl.felder = dict(felder)
        blaetter.append(bl)
    return blaetter


def _stueckliste(bl, x0, y, breite, res):
    bl.text(x0, y, "Leuchtenliste", 9, fett=True)
    spalten = [("", 26), ("Leuchte", 300), ("Typ", 200), ("Art.-Nr.", 110), ("Katalog", 70), ("Stück", 50),
               ("W gesamt", 70), ("Montage / Dimmung / Hinweis", breite - 826)]
    y = _tabelle_kopf(bl, x0, y + 22, spalten)
    bl.linie(x0, y - 6, x0 + breite, y - 6, breite=0.8)
    summe: dict[str, list] = {}
    for e in res["raeume"]:
        v = e["wahl"]
        lid = v["leuchte"]["id"]
        s = summe.setdefault((lid, e["dali"]), [res["leuchten"].get(lid, v["leuchte"]) if v.get("auslass")
                                                else v["leuchte"], 0])
        s[1] += v["n"]
    w_ges = 0.0
    for (lid, dali), (l, stk) in summe.items():
        w = stk * _z(l.get("w"))
        w_ges += w
        werte = [res["kennung"][lid], l["name"], l.get("typ", ""), _artnr(l, dali) or "–",
                 f"S. {l['seite']}" if l.get("seite") else "–", str(stk), _de(w, 0),
                 ({"einbau": "Einbau", "anbau": "Anbau", "pendel": "Pendel", "einbau_anbau": "Einbau/Anbau"}
                  .get(_n(l.get("montage")), _n(l.get("montage")))
                  + (" · DALI-dimmbar" if dali and l.get("art_nr_dali") else
                     (" · " + l["dimmung"] if l.get("dimmung") else ""))
                  + (" · " + l["hinweis"] if l.get("hinweis") else ""))]
        xx = x0
        for (sname, sw), wert in zip(spalten, werte):
            rechts = sname in ("Stück", "W gesamt")
            if sname.startswith("Montage"):
                wert = _umbruch(wert, int(sw / 4.4))
            bl.text(xx + (sw - 4 if rechts else 2), y + 10, wert, 6 if "\n" not in wert else 5.5,
                    h="rechts" if rechts else "links", v="mitte", fett=sname == "")
            xx += sw
        y += 22
        bl.linie(x0, y - 2, x0 + breite, y - 2, breite=0.3, farbe="#BBBBBB")
    bl.text(x0 + 26 + 300 + 200 + 110 + 70 + 50 + 70 - 4, y + 8, f"Σ {_de(w_ges, 0)} W", 6, h="rechts",
            v="mitte", fett=True)
    return y + 24


def _fussnoten(bl, x0, y, breite, res, daten):
    n = norm()
    t = n["raumwirkungsgrad"]
    refl = sorted({e["reflexion"] for e in res["raeume"]}) or ["hell"]
    kat = json.loads((REFERENZ / "leuchten_katalog.json").read_text(encoding="utf-8"))
    zeilen = [
        "Verfahren: Wirkungsgradverfahren  n = Ēm · A / (Φ · ηR · MF);  Ē = n · Φ · ηR · MF / A;  Raumindex k = 2 · A / (h · U), "
        "h = Lichtpunkthöhe über Nutzebene.",
        f"Wartungsfaktor MF = {_de(res['mf'])} (LED, saubere Räume, Wartung alle 3 Jahre). Reflexionsgrade: "
        + "; ".join(t["reflexion"].get(r, r) for r in refl)
        + ". ηR: Näherungswerte für direkt strahlende LED-Leuchten (direkt/indirekt × 0,85).",
        "Anforderungen: DIN EN 12464-1:2021-11, Tabellen 9–53 (Ēm erforderlich; * = modifiziert). In Arbeitsstätten zusätzlich ASR A3.4. "
        "Wohnungen: keine Norm, Praxiswerte.",
        f"Leuchtendaten: {kat.get('lieferant', '')}, {kat.get('stand', '')} – vor Bestellung mit dem Datenblatt abgleichen.",
        "Überschlag: Gleichmäßigkeit Uo und Blendung UGR sind nicht berechnet (Abstand und Katalog-UGR geprüft). "
        "Für den Nachweis Lichtberechnung mit Herstellerdaten (DIALux/Relux).",
    ]
    for z in zeilen:
        bl.text(x0, y, z, 5.5, farbe=FARBE_GRAU)
        y += 10
    return y


# --------------------------------------------------------------------------
def baue(daten: dict, fmt: Format) -> Projekt:
    from . import installationsplan
    res = berechne(daten)
    geraete, linien, texte, zusatz = leuchten_geraete(daten)
    plan = copy.deepcopy({k: v for k, v in daten.items() if not k.startswith("_")})
    plan["_basis"] = daten.get("_basis", ".")
    plan["plan"] = "installationsplan"
    plan["titel"] = _n(daten.get("titel")) or "Deckenspiegel"
    plan["plantyp"] = _n(daten.get("plantyp")) or "Deckenspiegel · Lichtberechnung DIN EN 12464-1 (Überschlag)"
    plan["geraete"] = (daten.get("geraete") or []) + geraete
    plan["linien"] = (daten.get("linien") or []) + linien
    plan["texte"] = (daten.get("texte") or []) + texte
    for r in (plan.get("grundriss") or {}).get("raeume", []):
        if _n(r.get("name")) in zusatz:
            r["zusatztext"] = zusatz[_n(r["name"])]
    proj = installationsplan.baue(plan, fmt)
    felder = proj.blaetter[0].felder
    proj.blaetter += _berechnungsblaetter(daten, fmt, plan["titel"], felder)
    # Ergebnis für die Übernahme in den Installationsplan
    daten["_leuchten_export"] = {"geraete": geraete, "linien": linien,
                                 "raeume": [{"name": e["name"], "leuchte": e["wahl"]["leuchte"]["id"],
                                             "anzahl": e["wahl"]["n"], "e_lx": round(e["wahl"]["e"]),
                                             "e_soll_lx": e["e_ziel"]} for e in res["raeume"]]}
    return proj
