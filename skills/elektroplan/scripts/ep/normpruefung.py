"""Normprüfung – nur Hinweise, keine Bemessung. Die Entscheidung bleibt bei der Elektrofachkraft.

Normstand: DIN-Normen-Handbuch Elektrotechniker-Handwerk, 13. Aufl. 2025 (Stand 09/2025),
abgeglichen am 12.10.2026 – Fundstellen in referenz/fachliches.md.

Verteilung (schutzorgane):
  - Spannungsfall je Stromkreis aus Länge, Querschnitt und Nennstrom (DIN 18015-1:2020-05, 5.2.1:
    hinter der Messeinrichtung höchstens 3 %, gerechnet mit dem Nennstrom der Schutzeinrichtung)
  - Anzahl Steckdosen-/Beleuchtungsstromkreise zur Wohnfläche (DIN 18015-2:2021-10, Tabelle 1)
  - Herd/Kochmulde 3L+N+PE und 20 A, Durchlauferhitzer ≥ 35 A, Ladeeinrichtung ≥ 32 A,
    Zuleitung Wohnungsverteiler ≥ 63 A (DIN 18015-1, 5.2.5 / 5.3.2)
Installationsplan:
  - Ausstattung je Raum nach DIN 18015-2 Tabelle 2 bzw. RAL-RG 678 (Ausstattungswert 2/3)
  - Schaltstelle je Raumzugang (DIN 18015-2, 4.5.2)
  - Installationszonen und Montagehöhen (DIN 18015-3:2016-09), barrierefrei 0,85 m (DIN 18040-2)
  - Schalter an der Schlossseite im Streifen 10–30 cm neben der Tür (DIN 18015-3, 4.2.3)
  - Rauchwarnmelder (DIN 14676-1:2025-05)
  - Steckdosen/Schalter in Bereich 1/2 von Dusche oder Wanne (DIN VDE 0100-701), wenn "sanitaer" angegeben
Wandansicht (Küchenplan): siehe wandansicht.normhinweise
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from .verteilerplan import _art, _norm, _querschnitt, _zahl

REFERENZ = Path(__file__).resolve().parents[2] / "referenz" / "ausstattung_din18015.json"

KAPPA_CU = 56.0                 # m/(Ω·mm²), Kupfer
SPANNUNGSFALL_MAX = 3.0         # %
FESTE_VERBRAUCHER = re.compile(
    r"herd|koch|backofen|geschirr|spül|wasch|trockner|durchlauf|boiler|speicher|wallbox|lade|"
    r"heiz|pumpe|klima|sauna|dunstab|kühl|gefrier|uv\b|zuleitung|aufzug|motor|rollladen|jalousie", re.I)

ZW_U = (0.15, 0.45)             # DIN 18015-3, 4.2.2
ZW_M = (1.00, 1.30)             # nur in Räumen mit Arbeitsflächen vor den Wänden
ZS = (0.10, 0.30)               # senkrechte Zonen neben Rohbaukanten/-ecken
TOL = 0.03
SCHALTER_MAX = 1.05             # DIN 18015-3, 5.3: Schaltermitte höchstens 1,05 m
BEDIENHOEHE_BF = 0.85           # DIN 18040-2, 4.5.2
RAEUME_MIT_ARBEITSFLAECHE = {"kueche", "hausarbeitsraum"}
WANDGERAETE_HOEHE = {"steckdose", "sd", "schalter", "taster", "dimmer", "tv", "sat", "antenne", "daten",
                     "lan", "netzwerk", "telefon", "tel"}
SCHALTER = {"schalter", "taster", "dimmer"}
SCHALTSTELLEN = SCHALTER | {"bewegungsmelder"}
GERAETE_KUECHE = {
    "Elektroherd/Kochfeld (3 × 230 V)": (r"^(h|he|hd|herd|kf|km|ko)$", r"herd|kochfeld|kochmulde"),
    "Geschirrspülmaschine": (r"^(gs|gsp|gsm|spm)$", r"geschirr|spülmasch"),
    "Mikrowellengerät/Dampfgarer": (r"^(mw|mwg|dg|dga|mik)$", r"mikro|dampf"),
}


def _f(v, std=None):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return std


def _de(x: float, stellen=1) -> str:
    return f"{x:.{stellen}f}".replace(".", ",")


def tabelle() -> dict | None:
    try:
        return json.loads(REFERENZ.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _stufe(stufen, wert: float, schluessel: str | None = None) -> int:
    """Zahl oder Stufenliste [{bis_m2|bis_laenge_m, anzahl}] → Anzahl."""
    if stufen is None:
        return 0
    if isinstance(stufen, (int, float)):
        return int(stufen)
    for s in stufen:
        k = schluessel or next((k for k in s if k.startswith("bis_")), None)
        if k is None or s.get(k) is None or wert <= s[k] + 1e-9:
            return int(s["anzahl"])
    return int(stufen[-1]["anzahl"])


def _wert(werte: dict, feld: str, flaeche: float, laenge: float) -> int:
    v = werte.get(feld)
    if isinstance(v, list) and v and "bis_laenge_m" in v[0]:
        return _stufe(v, laenge, "bis_laenge_m")
    return _stufe(v, flaeche, "bis_m2")


def ausstattungswert(daten: dict) -> str:
    """1 = DIN 18015-2 (Mindestausstattung), 2/3 = RAL-RG 678; auch "★★" oder "**"."""
    v = str(daten.get("ausstattungswert") or "1").strip()
    if "★" in v or "*" in v:
        v = str(v.count("★") + v.count("*"))
    v = v[:1]
    return v if v in ("1", "2", "3") else "1"


def _quelle(w: str) -> str:
    return "DIN 18015-2 Tab. 2" if w == "1" else f"RAL-RG 678 Ausstattungswert {w}"


# ------------------------------------------------------------------ Verteilung

def spannungsfall(daten: dict) -> list[str]:
    out = []
    grenze = _f(daten.get("spannungsfall_max"), SPANNUNGSFALL_MAX)
    for e in daten.get("schutzorgane") or []:
        if _art(e) not in ("LS", "FILS"):
            continue
        laenge, strom, q = _f(e.get("laenge")), _f(_zahl(e.get("in"))), _querschnitt(_norm(e.get("adern")))
        if not (laenge and strom and q):
            continue
        pole = _zahl(e.get("pole"))
        if pole in ("3", "3+N", "4"):
            du = math.sqrt(3) * laenge * strom / (KAPPA_CU * q) / 400 * 100
        else:
            du = 2 * laenge * strom / (KAPPA_CU * q) / 230 * 100
        if du > grenze:
            out.append(f"{_norm(e.get('bmk'))}: Spannungsfall ca. {_de(du)} % bei {_zahl(e.get('in'))} A über "
                       f"{_de(laenge, 0)} m {_norm(e.get('adern'))} mm² – DIN 18015-1 (5.2.1): hinter dem Zähler "
                       f"insgesamt höchstens {_de(grenze)} %, Zuleitung zur UV kommt noch dazu; Querschnitt oder Länge prüfen")
    return out


def stromkreisanzahl(daten: dict) -> list[str]:
    flaeche = _f(daten.get("wohnflaeche"))
    t = tabelle()
    if not flaeche or not t:
        return []
    soll = _stufe(t["stromkreise_steckdosen_beleuchtung"], flaeche, "bis_m2")
    ist = 0
    for e in daten.get("schutzorgane") or []:
        if _art(e) not in ("LS", "FILS"):
            continue
        text = f"{_norm(e.get('verbraucher'))} {_norm(e.get('raum'))}"
        if FESTE_VERBRAUCHER.search(text) or _zahl(e.get("pole")) in ("3", "3+N", "4"):
            continue
        if re.search(r"keller|dachboden|speicher", text, re.I):
            continue                      # Keller-/Bodenräume zählen zusätzlich (DIN 18015-2, 4.5.1)
        ist += 1
    if ist < soll:
        return [f"{ist} Steckdosen-/Beleuchtungsstromkreise für {_de(flaeche, 0)} m² Wohnfläche – "
                f"DIN 18015-2 (Tabelle 1) verlangt mindestens {soll}, Stromkreise für besondere Verbrauchsmittel "
                "und Keller/Dachboden zusätzlich"]
    return []


def anschlussleitungen(daten: dict) -> list[str]:
    """DIN 18015-1:2020-05, 5.2.5 und 5.3.2 – Mindestwerte für Herd, DLE, Ladeeinrichtung, Zuleitung."""
    out = []
    for e in daten.get("schutzorgane") or []:
        if _art(e) not in ("LS", "FILS"):
            continue
        bmk = _norm(e.get("bmk"))
        text = f"{_norm(e.get('verbraucher'))} {_norm(e.get('raum'))}".lower()
        pole = _zahl(e.get("pole"))
        dreiphasig = pole in ("3", "3+N", "4")
        In = _f(_zahl(e.get("in")))
        q = _querschnitt(_norm(e.get("adern")))
        if re.search(r"herd|kochfeld|kochmulde", text):
            if not dreiphasig or (In and In < 20):
                out.append(f"{bmk}: Herd/Kochmulde – DIN 18015-1 (5.2.5) sieht 3L+N+PE mit mindestens 20 A "
                           "Strombelastbarkeit und eine 20-A-Schutzeinrichtung vor")
        elif re.search(r"durchlauf|dle\b", text):
            if not dreiphasig or (q and q < 6):
                out.append(f"{bmk}: Durchlauferhitzer – DIN 18015-1 (5.2.5): Leitung 3L (ggf. N) + PE mit "
                           "mindestens 35 A Strombelastbarkeit (meist ≥ 6 mm², Verlegeart prüfen)")
        elif re.search(r"wallbox|ladeeinr|ladestation|ladepunkt|e-auto", text):
            if not dreiphasig or (q and q < 6):
                out.append(f"{bmk}: Ladeeinrichtung – DIN 18015-1 (5.3.2): Zuleitung 3L+N+PE mit mindestens "
                           "32 A Strombelastbarkeit plus Leerrohr für Netzwerkkabel; Dauerlast beachten")
    ein = daten.get("einspeisung") or {}
    qz = _querschnitt(_norm(ein.get("adern")))
    if qz and qz < 10:
        out.append(f"Zuleitung {_norm(ein.get('adern'))} mm² – DIN 18015-1 (5.2.5): vom Zählerplatz zum ersten "
                   "Wohnungsverteiler 3L+N+PE mit mindestens 63 A Strombelastbarkeit")
    return out


# ------------------------------------------------------------------ Installationsplan

def _raumtyp(name: str, nutzung, t: dict) -> dict | None:
    if isinstance(nutzung, list):
        nutzung = nutzung[0] if nutzung else ""
    n = (nutzung or name or "").lower()
    bester, laenge = None, 0
    for typ in t["raeume"]:
        if nutzung and nutzung.lower() == typ["typ"]:
            return typ
        for w in typ["erkennen"]:
            if w in n and len(w) > laenge:
                bester, laenge = typ, len(w)
    if bester is None:                    # „Zimmer 3“ o. ä. → Wohnraum, wenn sonst nichts passt
        bester = next((typ for typ in t["raeume"] if any(w in n for w in typ.get("auffang", []))), None)
    return bester


def _typen(name: str, nutzung, t: dict) -> list[dict]:
    """Ein Raum kann mehrere Nutzungsbereiche haben (Wohn-Ess-Küche): "nutzung": ["kueche", "essen"]."""
    if isinstance(nutzung, list) and len(nutzung) > 1:
        out = [next((x for x in t["raeume"] if x["typ"] == str(n).lower()), None) for n in nutzung]
        return [x for x in out if x]
    typ = _raumtyp(name, nutzung, t)
    return [typ] if typ else []


def _raeume(daten: dict):
    """Räume mit gleichem Namen zusammenfassen: {name: {flaeche, laenge, rects, nutzung, ...}}"""
    gr = daten.get("grundriss") or {}
    std_wand = _f(gr.get("wanddicke"), 0.115)
    out: dict[str, dict] = {}
    letzter = None
    for r in gr.get("raeume") or []:
        name = _norm(r.get("name"))
        b, tt = _f(r.get("b") or r.get("breite"), 0), _f(r.get("t") or r.get("tiefe"), 0)
        x, y = _f(r.get("x"), 0), _f(r.get("y"), 0)
        if not name and letzter:          # unbenanntes Rechteck gehört zum Raum davor (L-Form)
            name = letzter
        if not name:
            continue
        e = out.setdefault(name, {"flaeche": 0.0, "laenge": 0.0, "rects": [], "nutzung": "", "vorgabe": None,
                                  "arbeitsflaeche": None, "wand": std_wand})
        e["flaeche"] += b * tt
        e["laenge"] = max(e["laenge"], b, tt)
        e["rects"].append((x, y, b, tt))
        e["nutzung"] = e["nutzung"] or r.get("nutzung") or ""
        if _f(r.get("flaeche")):
            e["vorgabe"] = _f(r.get("flaeche"))
        if _f(r.get("arbeitsflaeche_m")):
            e["arbeitsflaeche"] = _f(r.get("arbeitsflaeche_m"))
        w = r.get("wand")
        if w is not None and not isinstance(w, dict):
            e["wand"] = _f(w, std_wand)
        letzter = name
    for e in out.values():
        if e["vorgabe"]:
            e["flaeche"] = e["vorgabe"]
    return out


def _abs(d: dict, raeume: dict) -> tuple[float, float]:
    x, y = _f(d.get("x"), 0), _f(d.get("y"), 0)
    name = _norm(d.get("raum"))
    if name and name in raeume:
        rx, ry, _, _ = raeume[name]["rects"][0]
        x, y = rx + x, ry + y
    return x, y


def _raum_von(d: dict, raeume: dict) -> str | None:
    if _norm(d.get("raum")):
        return _norm(d.get("raum"))
    x, y = _f(d.get("x"), 0), _f(d.get("y"), 0)
    for name, e in raeume.items():
        for rx, ry, b, t in e["rects"]:
            if rx - 0.35 <= x <= rx + b + 0.35 and ry - 0.35 <= y <= ry + t + 0.35:
                return name
    return None


def _code(d: dict) -> str:
    return _norm(d.get("text")).lower()


def _ist_geraet(d: dict, muster) -> bool:
    kurz, wort = muster
    art = _norm(d.get("symbol")).lower()
    text = " ".join(_norm(d.get(k)).lower() for k in ("text", "bemerkung", "text2"))
    return (art in ("geraet", "anschluss", "geraeteanschluss") and re.match(kurz, _code(d))) \
        or bool(re.search(wort, text))


def ausstattung(daten: dict) -> list[str]:
    t = tabelle()
    raeume = _raeume(daten)
    if not t or not raeume:
        return []
    w = ausstattungswert(daten)
    einsatz = str(daten.get("zaehlweise") or "").lower().startswith("eins")   # Standard: Kombination = 1 Auslass
    zaehl = {n: {"sd": 0, "licht": 0, "kom": 0, "geraete": []} for n in raeume}
    for d in daten.get("geraete") or []:
        name = _raum_von(d, raeume)
        if name not in raeume:
            continue
        art = _norm(d.get("symbol")).lower()
        z = zaehl[name]
        if art in ("steckdose", "sd"):
            z["sd"] += int(d.get("anzahl", 1) or 1) if einsatz else 1
        elif art in ("leuchte", "wandleuchte", "spot", "einbauleuchte"):
            z["licht"] += 1
        elif art in ("tv", "sat", "antenne", "daten", "lan", "netzwerk", "telefon", "tel"):
            z["kom"] += 1
        z["geraete"].append(d)
    for li in daten.get("linien") or []:
        if _norm(li.get("art")).lower() in ("langfeld", "lichtschiene", "lichtlinie", "ledprofil") and li.get("punkte"):
            x, y = li["punkte"][0]
            name = _raum_von({"x": x, "y": y}, raeume)
            if name in raeume:
                zaehl[name]["licht"] += 1
    out = []
    for name, e in raeume.items():
        typen = _typen(name, e["nutzung"], t)
        z = zaehl[name]
        if not typen:
            # nicht in Tabelle 2: mindestens 1 Licht, 1 Steckdose (4.5.2)
            if z["licht"] < 1 or z["sd"] < 1:
                out.append(f"{name}: Raum ohne Tabellenwert – DIN 18015-2 (4.5.2) verlangt mindestens einen "
                           "Beleuchtungsanschluss, eine Schaltstelle und eine Steckdose")
            continue
        fl, la = e["flaeche"], e["laenge"]
        soll_sd = soll_l = soll_kom = 0
        teile = []
        af_unbekannt = False
        for typ in typen:
            werte = typ["werte"].get(w) or typ["werte"]["1"]
            allg = _wert(werte, "steckdosen", fl, la) - (1 if len(typen) > 1 else 0)
            af = _wert(werte, "sd_arbeitsflaeche", fl, la)
            if af:
                laenge_af = e["arbeitsflaeche"]
                if laenge_af is None:
                    af_unbekannt, segmente = True, 1
                else:
                    segmente = max(1, math.ceil(laenge_af / 1.2 - 1e-9))
                af *= segmente
            extra = [(k, _wert(werte, k, fl, la)) for k in ("sd_iuk_ruk", "sd_kuehl", "sd_dunstabzug")]
            soll_sd += allg + af + sum(v for _, v in extra)
            soll_l += _wert(werte, "beleuchtung", fl, la)
            soll_kom += _wert(werte, "iuk", fl, la) + _wert(werte, "ruk", fl, la)
            namen = {"sd_iuk_ruk": "IuK/RuK", "sd_kuehl": "Kühlgerät", "sd_dunstabzug": "Dunstabzug"}
            teile.append(f"{allg} allgemein" + (f" + {af} Arbeitsfläche" if af else "") +
                         "".join(f" + {v} {namen[k]}" for k, v in extra if v))
        fehlt = []
        if z["sd"] < soll_sd:
            fehlt.append(f"{z['sd']} von {soll_sd} Steckdosen ({'; '.join(teile)})")
        if z["licht"] < soll_l:
            fehlt.append(f"{z['licht']} von {soll_l} Beleuchtungsanschlüssen")
        if z["kom"] < soll_kom:
            fehlt.append(f"{z['kom']} von {soll_kom} IuK/RuK-Anschlüssen")
        if any(x["typ"] == "kueche" for x in typen):
            for geraet, muster in GERAETE_KUECHE.items():
                if not any(_ist_geraet(d, muster) for d in z["geraete"]):
                    fehlt.append(f"kein Anschluss {geraet} (eigener Stromkreis)")
        if fehlt:
            bez = " + ".join(x["name"] for x in typen)
            zusatz = " – Arbeitsflächenlänge fehlt (\"arbeitsflaeche_m\" am Raum), mit 1 × 1,20 m gerechnet" \
                if af_unbekannt else ""
            out.append(f"{name} ({bez}, {_de(fl)} m²): " + ", ".join(fehlt) + f" nach {_quelle(w)}{zusatz}")
    return out


# ------------------------------------------------------------------ Öffnungen (Türen/Fenster) absolut

def _oeffnungen(daten: dict, raeume: dict) -> list[dict]:
    """Türen und Fenster als absolute Wandabschnitte: achse x (Wand n/s) oder y (Wand o/w)."""
    gr = daten.get("grundriss") or {}
    out = []
    for art, liste in (("tuer", gr.get("tueren") or []), ("fenster", gr.get("fenster") or [])):
        for d in liste:
            name = _norm(d.get("raum"))
            if name not in raeume:
                continue
            rx, ry, b, t = raeume[name]["rects"][0]
            s = _norm(d.get("seite")).lower()[:1].replace("e", "o")
            pos = _f(d.get("pos"), 0)
            br = _f(d.get("breite"), 0.885 if art == "tuer" else 1.0)
            if s in ("n", "s"):
                achse, linie, a0 = "x", (ry if s == "n" else ry + t), rx + pos
            elif s in ("o", "w"):
                achse, linie, a0 = "y", (rx if s == "w" else rx + b), ry + pos
            else:
                continue
            anschlag_ende = _norm(d.get("anschlag")).lower() in ("ende", "rechts", "unten")
            out.append({"art": art, "raum": name, "achse": achse, "linie": linie, "a0": a0, "a1": a0 + br,
                        "band": (a0 + br if anschlag_ende else a0) if d.get("anschlag") else None,
                        "fluegel": int(d.get("fluegel", 1) or 1), "dicke": raeume[name]["wand"]})
    return out


def _wandlage(d: dict, raeume: dict, name: str):
    """(wand n/o/s/w, achse, wandlinie absolut, lage absolut, rect)"""
    x, y = _abs(d, raeume)
    best = None
    for rect in raeume[name]["rects"]:
        rx, ry, b, t = rect
        w = _norm(d.get("wand")).lower()[:1].replace("e", "o")
        abst = {"n": abs(y - ry), "s": abs(ry + t - y), "w": abs(x - rx), "o": abs(rx + b - x)}
        if w not in abst:
            w = min(abst, key=abst.get)
        if best is None or abst[w] < best[0]:
            best = (abst[w], w, rect)
    _, w, (rx, ry, b, t) = best
    if w in ("n", "s"):
        return w, "x", (ry if w == "n" else ry + t), x, (rx, ry, b, t)
    return w, "y", (rx if w == "w" else rx + b), y, (rx, ry, b, t)


def _oeffnungen_an(oeff: list[dict], achse: str, linie: float) -> list[dict]:
    return [o for o in oeff if o["achse"] == achse and abs(o["linie"] - linie) <= o["dicke"] + 0.06]


def _in_senkrechter_zone(lage: float, achse: str, linie: float, rect, oeff: list[dict]) -> bool:
    rx, ry, b, t = rect
    w0, w1 = (rx, rx + b) if achse == "x" else (ry, ry + t)
    kanten = [w0, w1]                     # Wandecken
    for o in _oeffnungen_an(oeff, achse, linie):
        if o["art"] == "tuer" and o["band"] is not None and o["fluegel"] == 1:
            kanten.append(o["a1"] if abs(o["band"] - o["a0"]) < 1e-6 else o["a0"])   # nur Schlossseite
        else:
            kanten += [o["a0"], o["a1"]]
    return any(ZS[0] - TOL <= abs(lage - k) <= ZS[1] + TOL for k in kanten)


def installationszonen(daten: dict) -> list[str]:
    out = []
    t = tabelle() or {"raeume": []}
    decke = _f((daten.get("grundriss") or {}).get("deckenhoehe") or daten.get("deckenhoehe"), 2.50)
    zw_o = (decke - 0.45, decke - 0.15)
    raeume = _raeume(daten)
    oeff = _oeffnungen(daten, raeume)
    barrierefrei = bool(daten.get("barrierefrei"))
    ausserhalb: dict[str, list[str]] = {}
    for d in daten.get("geraete") or []:
        art = _norm(d.get("symbol")).lower()
        h = _f(d.get("hoehe"))
        if art not in WANDGERAETE_HOEHE or h is None:
            continue
        name = _raum_von(d, raeume)
        wo = name or _norm(d.get("raum")) or "?"
        if art in SCHALTER:
            if barrierefrei and abs(h - BEDIENHOEHE_BF) > TOL:
                zusatz = " (85–105 cm nur in begründeten Fällen bzw. bei mehreren Bedienelementen übereinander)" \
                    if h <= SCHALTER_MAX + TOL else ""
                out.append(f"{wo}: {art} bei h = {_de(h, 2)} m – barrierefrei nach DIN 18040-2 (4.5.2) "
                           f"Bedienhöhe grundsätzlich 0,85 m{zusatz}")
            elif not barrierefrei and h > SCHALTER_MAX + TOL:
                out.append(f"{wo}: {art} bei h = {_de(h, 2)} m – DIN 18015-3 (5.3): Schaltermitte höchstens 1,05 m "
                           "über Fußboden")
        typen = _typen(name, raeume[name]["nutzung"], t) if name in raeume else []
        zonen = [ZW_U, zw_o]
        if any(x["typ"] in RAEUME_MIT_ARBEITSFLAECHE for x in typen):
            zonen.append(ZW_M)
        if any(lo - TOL <= h <= hi + TOL for lo, hi in zonen):
            continue
        if name in raeume:
            _, achse, linie, lage, rect = _wandlage(d, raeume, name)
            if _in_senkrechter_zone(lage, achse, linie, rect, oeff):
                continue
        ausserhalb.setdefault(wo, []).append(f"{art} h = {_de(h, 2)} m")
    for wo, liste in ausserhalb.items():
        out.append(f"{wo}: {', '.join(liste)} außerhalb der Installationszonen nach DIN 18015-3 (waagerecht "
                   "0,15–0,45 m über OKFF / unter Decke, 1,00–1,30 m nur bei Arbeitsflächen; senkrecht 10–30 cm "
                   "neben Türen, Fenstern, Ecken) – Leitung als senkrechte Stichleitung aus einer Zone führen")
    # Schalter neben Türen: Schlossseite, Streifen 10–30 cm neben der Rohbaukante
    for d in daten.get("geraete") or []:
        art = _norm(d.get("symbol")).lower()
        name = _raum_von(d, raeume)
        if art not in SCHALTER or name not in raeume:
            continue
        _, achse, linie, lage, rect = _wandlage(d, raeume, name)
        naechste = None
        for o in _oeffnungen_an(oeff, achse, linie):
            if o["art"] != "tuer":
                continue
            dist = o["a0"] - lage if lage < o["a0"] else (lage - o["a1"] if lage > o["a1"] else 0.0)
            if naechste is None or dist < naechste[0]:
                kante = o["a0"] if lage < o["a0"] else o["a1"]
                naechste = (dist, o, kante)
        if naechste is None or naechste[0] >= 0.6:
            continue
        dist, o, kante = naechste
        if o["band"] is not None and o["fluegel"] == 1 and abs(kante - o["band"]) < 1e-6:
            out.append(f"{name}: Schalter auf der Bandseite der Tür – DIN 18015-3 (4.2.3) legt die senkrechte Zone "
                       "an einflügeligen Türen nur an die Schlossseite (sonst hinter dem offenen Türblatt)")
        elif not (ZS[0] - TOL <= dist <= ZS[1] + TOL):
            out.append(f"{name}: Schalter {_de(dist * 100, 0)} cm neben der Tür – DIN 18015-3 sieht den "
                       "Streifen 10–30 cm neben der Rohbaukante vor")
    if barrierefrei:
        for d in daten.get("geraete") or []:
            art = _norm(d.get("symbol")).lower()
            name = _raum_von(d, raeume)
            if art not in SCHALTER or name not in raeume:
                continue
            _, achse, linie, lage, (rx, ry, b, t) = _wandlage(d, raeume, name)
            w0, w1 = (rx, rx + b) if achse == "x" else (ry, ry + t)
            ecke = min(abs(lage - w0), abs(lage - w1))
            if ecke < 0.5 - TOL:
                out.append(f"{name}: Schalter {_de(ecke * 100, 0)} cm von der Raumecke – DIN 18040-2 (4.5.2, "
                           "Rollstuhlnutzung): seitlich mindestens 50 cm zu Wänden/Einrichtungen")
    return out


def schaltstellen(daten: dict) -> list[str]:
    """Jedem Raumzugang eine Schaltstelle (DIN 18015-2, 4.5.2)."""
    t = tabelle() or {"raeume": []}
    raeume = _raeume(daten)
    oeff = [o for o in _oeffnungen(daten, raeume) if o["art"] == "tuer"]
    if not oeff:
        return []
    zugaenge = {n: 0 for n in raeume}
    for o in oeff:
        zugaenge[o["raum"]] += 1
        mitte = (o["a0"] + o["a1"]) / 2
        # Raum auf der anderen Wandseite
        for name, e in raeume.items():
            if name == o["raum"]:
                continue
            for rx, ry, b, tt in e["rects"]:
                if o["achse"] == "x" and rx - 0.01 <= mitte <= rx + b + 0.01 and \
                        min(abs(ry - o["linie"]), abs(ry + tt - o["linie"])) <= o["dicke"] + 0.06:
                    zugaenge[name] += 1
                    break
                if o["achse"] == "y" and ry - 0.01 <= mitte <= ry + tt + 0.01 and \
                        min(abs(rx - o["linie"]), abs(rx + b - o["linie"])) <= o["dicke"] + 0.06:
                    zugaenge[name] += 1
                    break
    stellen = {n: 0 for n in raeume}
    melder = {n: False for n in raeume}
    for d in daten.get("geraete") or []:
        art = _norm(d.get("symbol")).lower()
        name = _raum_von(d, raeume)
        if name not in raeume:
            continue
        if art in SCHALTSTELLEN:
            stellen[name] += 1
        if art in ("bewegungsmelder", "melder") and re.search(r"bwm|pm|präsenz|bewegung", _code(d) or "bwm"):
            melder[name] = True
    out = []
    for name, n in zugaenge.items():
        typen = _typen(name, raeume[name]["nutzung"], t)
        if any(x["typ"] in ("freisitz",) for x in typen) or n == 0 or melder[name]:
            continue
        if stellen[name] < n:
            out.append(f"{name}: {n} Zugänge, {stellen[name]} Schaltstelle(n) – DIN 18015-2 (4.5.2): jedem "
                       "Raumzugang eine Schaltstelle, Licht von jedem Zugang schaltbar (Flur alternativ Melder)")
    return out


def rauchwarnmelder(daten: dict) -> list[str]:
    """DIN 14676-1:2025-05 – Pflicht über die Landesbauordnung (Bayern: BayBO Art. 46 Abs. 4)."""
    t = tabelle() or {"raeume": []}
    raeume = _raeume(daten)
    if not raeume:
        return []
    rm = {n: [] for n in raeume}
    for d in daten.get("geraete") or []:
        art = _norm(d.get("symbol")).lower()
        if art == "rauchmelder" or (art == "melder" and _code(d) in ("", "rm", "rwm")):
            name = _raum_von(d, raeume)
            if name in raeume:
                rm[name].append(d)
    if not any(rm.values()):
        return []                         # Plan ohne Rauchmelder: keine Einzelhinweise
    out = []
    for name, e in raeume.items():
        typen = _typen(name, e["nutzung"], t)
        pflicht = any(x["typ"] in ("schlafen", "flur") for x in typen)
        if pflicht and not rm[name]:
            out.append(f"{name}: kein Rauchwarnmelder – DIN 14676-1 / Landesbauordnung: Schlafräume, Kinderzimmer und Flure "
                       "als Rettungsweg")
        if rm[name] and e["flaeche"] > 60 * len(rm[name]) + 1e-6:
            out.append(f"{name}: {len(rm[name])} Rauchwarnmelder für {_de(e['flaeche'])} m² – je angefangene 60 m² "
                       "einer (DIN 14676-1, 4.3.3)")
        for d in rm[name]:
            x, y = _abs(d, raeume)
            for rx, ry, b, tt in e["rects"]:
                if rx - 0.01 <= x <= rx + b + 0.01 and ry - 0.01 <= y <= ry + tt + 0.01:
                    abst = min(x - rx, rx + b - x, y - ry, ry + tt - y)
                    if abst < 0.5 - 1e-6:
                        out.append(f"{name}: Rauchwarnmelder {_de(abst * 100, 0)} cm von der Wand – DIN 14676-1: "
                                   "mindestens 0,5 m von Wand, Unterzug und Einrichtung, möglichst Raummitte")
                    break
    return out


def sanitaer(daten: dict) -> list[str]:
    """Bereich 1 = Grundfläche Dusche/Wanne, Bereich 2 = 0,60 m darum (DIN VDE 0100-701)."""
    gr = daten.get("grundriss") or {}
    raeume = _raeume(daten)
    out = []
    for s in gr.get("sanitaer") or []:
        name = _norm(s.get("raum"))
        if name not in raeume:
            continue
        rx, ry, _, _ = raeume[name]["rects"][0]
        sx, sy = rx + _f(s.get("x"), 0), ry + _f(s.get("y"), 0)
        sb, st = _f(s.get("b"), 0.9), _f(s.get("t"), 0.9)
        for d in daten.get("geraete") or []:
            art = _norm(d.get("symbol")).lower()
            if art not in {"steckdose", "sd"} | SCHALTER or _raum_von(d, raeume) != name:
                continue
            x, y = _abs(d, raeume)
            dx = max(sx - x, 0, x - (sx + sb))
            dy = max(sy - y, 0, y - (sy + st))
            abstand = math.hypot(dx, dy)
            was = "Steckdose" if art in ("steckdose", "sd") else "Schalter"
            if abstand <= 1e-6:
                out.append(f"{name}: {was} liegt in Bereich 1 ({(_norm(s.get('art')) or 'Dusche/Wanne').capitalize()}) – "
                           "nicht zulässig (VDE 0100-701)")
            elif abstand < 0.60:
                out.append(f"{name}: {was} {_de(abstand * 100, 0)} cm von {(_norm(s.get('art')) or 'Dusche/Wanne').capitalize()} – "
                           "in Bereich 2 (0,60 m) nicht zulässig (VDE 0100-701)")
    return out


def pruefe(daten: dict) -> list[str]:
    art = str(daten.get("plan", "")).lower()
    out: list[str] = []
    if daten.get("schutzorgane"):
        out += spannungsfall(daten) + stromkreisanzahl(daten) + anschlussleitungen(daten)
    if art == "installationsplan":
        out += (ausstattung(daten) + schaltstellen(daten) + installationszonen(daten) +
                rauchwarnmelder(daten) + sanitaer(daten))
    if art in ("wandansicht", "kuechenplan", "küchenplan"):
        from .wandansicht import normhinweise
        out += normhinweise(daten)
    return list(dict.fromkeys(out))          # gleiche Hinweise (z. B. zwei Steckdosen) nur einmal
