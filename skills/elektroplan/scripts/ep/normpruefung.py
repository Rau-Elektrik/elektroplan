"""Normprüfung – nur Hinweise, keine Bemessung. Die Entscheidung bleibt bei der Elektrofachkraft.

Verteilung (schutzorgane):
  - Spannungsfall je Stromkreis aus Länge, Querschnitt und Nennstrom (DIN VDE 0100-520,
    Empfehlung DIN 18015-1: höchstens 3 % vom Zähler bis zum Verbraucher)
  - Anzahl Steckdosen-/Beleuchtungsstromkreise zur Wohnfläche (DIN 18015-2), wenn "wohnflaeche" angegeben
Installationsplan:
  - Ausstattung je Raum gegen referenz/ausstattung_din18015.json (DIN 18015-2)
  - Montagehöhen in den Installationszonen (DIN 18015-3)
  - Schalter im Streifen 10–30 cm neben der Tür (DIN 18015-3)
  - Steckdosen/Schalter in Bereich 1/2 von Dusche oder Wanne (DIN VDE 0100-701), wenn "sanitaer" angegeben
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

ZONEN = [(0.15, 0.45, "untere Zone"), (0.90, 1.30, "mittlere Zone")]
WANDGERAETE_HOEHE = {"steckdose", "sd", "schalter", "taster", "dimmer", "tv", "sat", "antenne", "daten",
                     "lan", "netzwerk", "telefon", "tel"}
SCHALTER = {"schalter", "taster", "dimmer"}


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


def _stufe(stufen: list, wert: float, schluessel: str) -> int:
    for s in stufen:
        if s.get(schluessel) is None or wert <= s[schluessel] + 1e-9:
            return int(s["anzahl"])
    return int(stufen[-1]["anzahl"])


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
                       f"{_de(laenge, 0)} m {_norm(e.get('adern'))} mm² – Empfehlung höchstens {_de(grenze)} % "
                       "(DIN 18015-1 / VDE 0100-520, Hauptleitung kommt noch dazu); Querschnitt oder Länge prüfen")
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
        ist += 1
    if ist < soll:
        return [f"{ist} Steckdosen-/Beleuchtungsstromkreise für {_de(flaeche, 0)} m² Wohnfläche – "
                f"DIN 18015-2 sieht mindestens {soll} vor{_vorbehalt(t)}"]
    return []


# ------------------------------------------------------------------ Installationsplan

def _vorbehalt(t: dict) -> str:
    return "" if t.get("geprueft") else " (Tabelle noch nicht mit Normtext abgeglichen)"


def _raumtyp(name: str, nutzung: str, t: dict) -> dict | None:
    n = (nutzung or name or "").lower()
    bester, laenge = None, 0
    for typ in t["raeume"]:
        if nutzung and nutzung.lower() == typ["typ"]:
            return typ
        for w in typ["erkennen"]:
            if w in n and len(w) > laenge:
                bester, laenge = typ, len(w)
    return bester


def _raeume(daten: dict):
    """Räume mit gleichem Namen zusammenfassen: {name: {flaeche, laenge, rects, nutzung}}"""
    gr = daten.get("grundriss") or {}
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
        e = out.setdefault(name, {"flaeche": 0.0, "laenge": 0.0, "rects": [], "nutzung": "", "vorgabe": None})
        e["flaeche"] += b * tt
        e["laenge"] = max(e["laenge"], b, tt)
        e["rects"].append((x, y, b, tt))
        e["nutzung"] = e["nutzung"] or _norm(r.get("nutzung"))
        if _f(r.get("flaeche")):
            e["vorgabe"] = _f(r.get("flaeche"))
        letzter = name
    for e in out.values():
        if e["vorgabe"]:
            e["flaeche"] = e["vorgabe"]
    return out


def _raum_von(d: dict, raeume: dict) -> str | None:
    if _norm(d.get("raum")):
        return _norm(d.get("raum"))
    x, y = _f(d.get("x"), 0), _f(d.get("y"), 0)
    for name, e in raeume.items():
        for rx, ry, b, t in e["rects"]:
            if rx - 0.35 <= x <= rx + b + 0.35 and ry - 0.35 <= y <= ry + t + 0.35:
                return name
    return None


def ausstattung(daten: dict) -> list[str]:
    t = tabelle()
    raeume = _raeume(daten)
    if not t or not raeume:
        return []
    sd = {n: 0 for n in raeume}
    licht = {n: 0 for n in raeume}
    for d in daten.get("geraete") or []:
        name = _raum_von(d, raeume)
        if name not in raeume:
            continue
        art = _norm(d.get("symbol")).lower()
        if art in ("steckdose", "sd"):
            sd[name] += 1
        elif art in ("leuchte", "wandleuchte", "spot", "einbauleuchte"):
            licht[name] += 1
    for li in daten.get("linien") or []:
        if _norm(li.get("art")).lower() in ("langfeld", "lichtschiene", "lichtlinie", "ledprofil") and li.get("punkte"):
            x, y = li["punkte"][0]
            name = _raum_von({"x": x, "y": y}, raeume)
            if name in raeume:
                licht[name] += 1
    out = []
    for name, e in raeume.items():
        typ = _raumtyp(name, e["nutzung"], t)
        if not typ:
            continue
        mass, schl = (e["laenge"], "bis_laenge_m") if "bis_laenge_m" in typ["steckdosen"][0] else (e["flaeche"], "bis_m2")
        soll_sd = _stufe(typ["steckdosen"], mass, schl)
        schl_l = "bis_laenge_m" if "bis_laenge_m" in typ["beleuchtung"][0] else "bis_m2"
        soll_l = _stufe(typ["beleuchtung"], e["laenge"] if schl_l == "bis_laenge_m" else e["flaeche"], schl_l)
        fehlt = []
        if sd[name] < soll_sd:
            fehlt.append(f"{sd[name]} von {soll_sd} Steckdosen")
        if licht[name] < soll_l:
            fehlt.append(f"{licht[name]} von {soll_l} Beleuchtungsanschlüssen")
        if fehlt:
            out.append(f"{name} ({typ['name']}, {_de(e['flaeche'])} m²): " + ", ".join(fehlt) +
                       f" nach DIN 18015-2{_vorbehalt(t)}")
    return out


def _wand_und_lage(d: dict, rect) -> tuple[str, float] | None:
    """Wand (n/o/s/w) und Lage entlang der Wand (m ab linker bzw. oberer Raumecke)."""
    rx, ry, b, t = rect
    x, y = _f(d.get("x"), 0), _f(d.get("y"), 0)
    if not _norm(d.get("raum")):          # absolute Koordinaten
        x, y = x - rx, y - ry
    w = _norm(d.get("wand")).lower()[:1].replace("e", "o")
    if w not in ("n", "o", "s", "w"):
        abst = {"n": abs(y), "s": abs(t - y), "w": abs(x), "o": abs(b - x)}
        w = min(abst, key=abst.get)
    return w, (x if w in "ns" else y)


def installationszonen(daten: dict) -> list[str]:
    out = []
    decke = _f((daten.get("grundriss") or {}).get("deckenhoehe") or daten.get("deckenhoehe"), 2.50)
    zonen = ZONEN + [(decke - 0.45, decke - 0.15, "obere Zone")]
    for d in daten.get("geraete") or []:
        art = _norm(d.get("symbol")).lower()
        h = _f(d.get("hoehe"))
        if art not in WANDGERAETE_HOEHE or h is None:
            continue
        if not any(lo - 1e-9 <= h <= hi + 1e-9 for lo, hi, _ in zonen):
            wo = _norm(d.get("raum")) or "?"
            out.append(f"{wo}: {art} bei h = {_de(h, 2)} m liegt außerhalb der Installationszonen nach "
                       "DIN 18015-3 (unten 0,15–0,45 m, mitte 0,90–1,30 m) – Leitung senkrecht aus einer Zone zuführen")
    # Schalter neben Türen
    gr = daten.get("grundriss") or {}
    raeume = _raeume(daten)
    tueren: dict[str, list] = {}
    for tdef in gr.get("tueren") or []:
        tueren.setdefault(_norm(tdef.get("raum")), []).append(tdef)
    for d in daten.get("geraete") or []:
        art = _norm(d.get("symbol")).lower()
        name = _raum_von(d, raeume)
        if art not in SCHALTER or name not in raeume or name not in tueren:
            continue
        w, lage = _wand_und_lage(d, raeume[name]["rects"][0])
        naechste = None
        for tdef in tueren[name]:
            if _norm(tdef.get("seite")).lower()[:1].replace("e", "o") != w:
                continue
            a0 = _f(tdef.get("pos"), 0)
            a1 = a0 + _f(tdef.get("breite"), 0.885)
            dist = a0 - lage if lage < a0 else (lage - a1 if lage > a1 else 0.0)
            naechste = dist if naechste is None else min(naechste, dist)
        if naechste is not None and naechste < 0.6 and not (0.07 <= naechste <= 0.33):
            out.append(f"{name}: Schalter {_de(naechste * 100, 0)} cm neben der Tür – DIN 18015-3 sieht den "
                       "Streifen 10–30 cm neben der Zarge vor")
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
            x, y = _f(d.get("x"), 0), _f(d.get("y"), 0)
            if _norm(d.get("raum")):
                x, y = rx + x, ry + y
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
        out += spannungsfall(daten) + stromkreisanzahl(daten)
    if art == "installationsplan":
        out += ausstattung(daten) + installationszonen(daten) + sanitaer(daten)
    return list(dict.fromkeys(out))          # gleiche Hinweise (z. B. zwei Steckdosen) nur einmal
