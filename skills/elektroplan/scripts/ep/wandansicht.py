"""Wandansicht (Küchenplan): Frontansicht je Wand mit Möbeln, Elektropunkten und Höhen.

Jede Wand wird von vorn gezeichnet (Blick auf die Wand, x nach rechts ab der linken
Wandecke, h nach oben ab OKFF). Darin: Fenster/Türen, Küchenmöbel (Unterschränke,
Arbeitsplatte, Oberschränke, Hochschränke, Dunstabzug), die Gerätedosen maßstäblich
(Ø 68 mm, Mehrfachkombinationen im 71-mm-Raster) mit Positionsnummer, steigende
Bemaßung für x (unten) und h (links), Höhenkoten der Möbel (rechts) und auf Wunsch
die Installationszonen nach DIN 18015-3. Rechts die Punkteliste mit Symbol nach
DIN EN 60617-11, x, h, Stromkreis und Bemerkung.
Koordinaten in Metern.
"""
from __future__ import annotations

import math

from .blatt import MM_PRO_PX, Format
from . import firma as _firma
from .model import Blatt, Projekt, schriftpx, text_bei, textbreite

MASSSTAEBE = [20, 25, 50]
DOSE_D = 0.068                  # Gerätedose Ø 68 mm
DOSE_RASTER = 0.071             # Mittenabstand in Kombinationsrahmen
TAB_B = 470                     # Breite der Punkteliste (px)
ZEILE_H = 34                    # Zeilenhöhe der Punkteliste (Symbolplatz)
RAND = 25
DIM_L = 78                      # Platz links für die Höhenbemaßung
DIM_R = 92                      # Platz rechts für Höhenkoten der Möbel
DIM_U = 84                      # Platz unten für die x-Bemaßung
KOPF_H = 30                     # Titel über der Wand
FARBE_WAND = "#555555"
FARBE_MOEBEL = "#8A8A8A"
FARBE_MOEBEL_TEXT = "#7A7A7A"
FARBE_ZONE = "#E4EEF8"
FARBE_ZONE_TEXT = "#7EA2C8"
FARBE_HILF = "#C4C4C4"
FARBE_MASS = "#333333"
KATEGORIE_FARBE = {"steckdose": "#000000", "schalter": "#1F5FBF", "geraet": "#B22222",
                   "licht": "#C87800", "kommunikation": "#2E7D32", "sonstiges": "#555555"}
KATEGORIE_NAME = {"steckdose": "Steckdose", "schalter": "Schalter / Taster / Dimmer",
                  "geraet": "Geräteanschluss (eigener Stromkreis)", "licht": "Leuchtenauslass",
                  "kommunikation": "Daten / TV / Telefon", "sonstiges": "Dose / Melder / Sonstiges"}

STANDARD = {"arbeitsplatte": 0.91, "plattenstaerke": 0.04, "sockel": 0.10, "oberschrank_uk": 1.45,
            "oberschrank_ok": 2.17, "hochschrank_ok": 2.17, "dunstabzug_abstand": 0.65}
UNTER = {"unterschrank", "us", "geschirrspueler", "geschirrspüler", "gsp", "spuele", "spüle",
         "spuelenschrank", "herd", "backofen_unterbau", "kochfeld", "kochfeldschrank", "auszug",
         "waschmaschine", "trockner", "eckschrank", "blende"}
HOCH = {"hochschrank", "hs", "kuehlschrank", "kühlschrank", "backofen_hoch", "geraeteschrank", "vorratsschrank"}
OBER = {"oberschrank", "os", "haengeschrank", "hängeschrank", "regal"}
GERAETE_NAMEN = {"H": "Herd/Kochfeld (3 × 230 V)", "HE": "Herd (3 × 230 V)", "HD": "Herdanschlussdose",
                 "KF": "Kochfeld (3 × 230 V)", "BO": "Backofen", "GS": "Geschirrspüler", "GSP": "Geschirrspüler",
                 "KS": "Kühlschrank", "KG": "Kühl-/Gefrierkombi", "GF": "Gefriergerät", "DA": "Dunstabzug",
                 "MW": "Mikrowelle", "DG": "Dampfgarer", "WM": "Waschmaschine", "T": "Wäschetrockner",
                 "TR": "Wäschetrockner", "DLE": "Durchlauferhitzer", "WW": "Warmwassergerät",
                 "KL": "Kleinspeicher / Untertischgerät", "KM": "Kaffeevollautomat", "WX": "Wärmeschublade"}
SCHALTER_KURZ = {"aus": "S", "zweipolig": "S2", "serie": "SR", "wechsel": "W", "kreuz": "K", "dimmer": "D",
                 "taster": "T", "taster_licht": "TL", "kontroll": "SK"}
SCHALTER_NAME = {"aus": "Ausschalter", "zweipolig": "Ausschalter 2-polig", "serie": "Serienschalter",
                 "wechsel": "Wechselschalter", "kreuz": "Kreuzschalter", "dimmer": "Dimmer", "taster": "Taster",
                 "taster_licht": "Taster beleuchtet", "kontroll": "Schalter mit Kontrolllampe"}


def _n(s) -> str:
    return str(s or "").strip()


def _z(v, std=0.0) -> float:
    if v in (None, ""):
        return std
    return float(str(v).replace(",", "."))


def _de(v: float, stellen=2) -> str:
    return f"{v:.{stellen}f}".replace(".", ",")


# --------------------------------------------------------------------------
# Datenaufbereitung
# --------------------------------------------------------------------------
def masse(daten: dict) -> dict:
    m = dict(STANDARD)
    for k, v in (daten.get("kueche") or daten.get("masse") or {}).items():
        if k in m:
            m[k] = _z(v, m[k])
    m["deckenhoehe"] = _z(daten.get("deckenhoehe"), 2.50)
    return m


def moebel_der_wand(wand: dict, m: dict) -> list[dict]:
    """Möbel mit vollständigen Maßen: art, x0, x1, uk, ok, text, schicht."""
    cursor = {"unter": 0.0, "ober": 0.0}
    out = []
    for d in wand.get("moebel") or []:
        art = _n(d.get("art")).lower() or "unterschrank"
        b = _z(d.get("breite"), 0.60)
        if art in UNTER:
            schicht = "unter"
        elif art in HOCH:
            schicht = "hoch"
        elif art in OBER:
            schicht = "ober"
        elif art in ("dunstabzug", "haube", "dunstabzugshaube"):
            schicht = "haube"
        elif art == "arbeitsplatte":
            schicht = "platte"
        else:
            schicht = "frei"
        if d.get("x") not in (None, ""):
            x0 = _z(d.get("x"))
        elif schicht in ("unter", "hoch"):
            x0 = cursor["unter"]
        elif schicht == "ober":
            x0 = cursor["ober"]
        else:
            x0 = 0.0
        x1 = x0 + b
        if schicht == "unter":
            uk, ok = _z(d.get("uk"), 0.0), _z(d.get("ok"), m["arbeitsplatte"] - m["plattenstaerke"])
            cursor["unter"] = x1
        elif schicht == "hoch":
            uk, ok = _z(d.get("uk"), 0.0), _z(d.get("ok"), m["hochschrank_ok"])
            cursor["unter"] = cursor["ober"] = max(cursor["unter"], x1)
            cursor["ober"] = max(cursor["ober"], x1)
        elif schicht == "ober":
            uk, ok = _z(d.get("uk"), m["oberschrank_uk"]), _z(d.get("ok"), m["oberschrank_ok"])
            cursor["ober"] = x1
        elif schicht == "haube":
            uk = _z(d.get("uk"), m["arbeitsplatte"] + m["dunstabzug_abstand"])
            ok = _z(d.get("ok"), m["deckenhoehe"] if _n(d.get("form")).lower() in ("", "wand", "kamin")
                    else uk + 0.10)
        elif schicht == "platte":
            ok = _z(d.get("ok"), m["arbeitsplatte"])
            uk = ok - _z(d.get("staerke"), m["plattenstaerke"])
        else:
            uk = _z(d.get("uk"))
            ok = _z(d.get("ok"), uk + _z(d.get("hoehe"), 0.5))
        out.append({**d, "art": art, "schicht": schicht, "x0": x0, "x1": x1, "uk": uk, "ok": ok})
    # Arbeitsplatte automatisch über zusammenhängende Unterschränke
    if not any(e["schicht"] == "platte" for e in out):
        spannen = sorted((e["x0"], e["x1"]) for e in out if e["schicht"] == "unter")
        zus = []
        for a, b in spannen:
            if zus and a <= zus[-1][1] + 0.02:
                zus[-1][1] = max(zus[-1][1], b)
            else:
                zus.append([a, b])
        for a, b in zus:
            out.append({"art": "arbeitsplatte", "schicht": "platte", "x0": a, "x1": b, "auto": True,
                        "uk": m["arbeitsplatte"] - m["plattenstaerke"], "ok": m["arbeitsplatte"]})
    return out


def arbeitsflaechen(moebel: list[dict]) -> list[tuple[float, float, float]]:
    """(x0, x1, OK) aller Arbeitsplatten; Höhe 0,85–1,10 m gilt als Arbeitsfläche (DIN 18015-2, 3.6)."""
    return [(e["x0"], e["x1"], e["ok"]) for e in moebel if e["schicht"] == "platte"
            and 0.85 - 1e-6 <= e["ok"] <= 1.10 + 1e-6]


def kategorie(d: dict) -> str:
    art = _n(d.get("symbol")).lower()
    if art in ("steckdose", "sd"):
        return "steckdose"
    if art in ("schalter", "taster", "dimmer"):
        return "schalter"
    if art in ("geraet", "anschluss", "geraeteanschluss", "herd"):
        return "geraet"
    if art in ("leuchte", "wandleuchte", "auslass", "unterbauleuchte", "spot"):
        return "licht"
    if art in ("tv", "sat", "antenne", "daten", "lan", "netzwerk", "telefon", "tel"):
        return "kommunikation"
    return "sonstiges"


def kurz_und_name(d: dict) -> tuple[str, str]:
    art = _n(d.get("symbol")).lower()
    text = _n(d.get("text"))
    n = int(d.get("anzahl", 1) or 1)
    if art in ("steckdose", "sd"):
        name = "Steckdose" + (f" {n}-fach" if n > 1 else "")
        return (f"{n}×SD" if n > 1 else "SD"), name + (f" – {text}" if text else "")
    if art in ("schalter", "taster", "dimmer"):
        sa = {"taster": "taster", "dimmer": "dimmer"}.get(art, _n(d.get("art")).lower() or "aus")
        kurz = SCHALTER_KURZ.get(sa, "S")
        return (f"{n}×{kurz}" if n > 1 else kurz), SCHALTER_NAME.get(sa, "Schalter") + \
            (f" {n}-fach" if n > 1 else "") + (f" – {text}" if text else "")
    if art in ("geraet", "anschluss", "geraeteanschluss", "herd"):
        code = text.upper() if text and len(text) <= 4 else (text[:3].upper() if text else "H")
        lang = GERAETE_NAMEN.get(code, text or "Gerät")
        return code, f"Geräteanschluss {lang}"
    if art in ("leuchte", "wandleuchte", "auslass", "unterbauleuchte", "spot"):
        la = _n(d.get("art")).lower()
        name = {"unterbau": "Auslass Unterbauleuchte", "wand": "Wandleuchte", "decke": "Deckenauslass",
                "sockel": "Auslass Sockelleuchte"}.get(la, "Leuchtenauslass")
        if art == "unterbauleuchte":
            name = "Auslass Unterbauleuchte"
        return "L", name + (f" – {text}" if text else "")
    if art in ("tv", "sat", "antenne"):
        return "TV", "Antennen-/TV-Dose (RuK)" + (f" – {text}" if text else "")
    if art in ("daten", "lan", "netzwerk"):
        return (f"{n}×LAN" if n > 1 else "LAN"), "Datendose (IuK)" + (f" – {text}" if text else "")
    if art in ("telefon", "tel"):
        return "TEL", "Telefondose (TAE)"
    if art == "dose":
        return "AD", "Abzweig-/Geräteverbindungsdose" + (f" – {text}" if text else "")
    if art in ("melder", "rauchmelder", "bewegungsmelder", "sensor", "thermostat"):
        code = text or {"rauchmelder": "RM", "bewegungsmelder": "BWM", "thermostat": "RTR"}.get(art, "RM")
        return code, f"Melder/Sensor {code}"
    return text or "?", text or art


def dosen(d: dict) -> list[tuple[float, float]]:
    """Mittelpunkte der Einzeldosen. x = Mitte der Kombination; h = Dosenmitte (waagerecht) bzw.
    oberste Dose (senkrecht, wie die Vorzugshöhe nach DIN 18015-3, 5.3)."""
    n = max(1, int(d.get("anzahl", 1) or 1))
    x, h = _z(d.get("x")), _z(d.get("h", d.get("hoehe")))
    if _n(d.get("richtung")).lower().startswith("s"):
        return [(x, h - i * DOSE_RASTER) for i in range(n)]
    return [(x + (i - (n - 1) / 2) * DOSE_RASTER, h) for i in range(n)]


def punkte_nummerieren(daten: dict) -> list[tuple[dict, dict, str]]:
    """[(wand, punkt, nr)] in Reihenfolge, Nummern fortlaufend (oder aus "nr")."""
    out, nr = [], 0
    for w in daten.get("waende") or []:
        for p in w.get("punkte") or []:
            nr += 1
            out.append((w, p, _n(p.get("nr")) or str(nr)))
    return out


# --------------------------------------------------------------------------
# Zeichnen
# --------------------------------------------------------------------------
class Ansicht:
    """Rechnet Wandmeter in Blattpixel um (y nach unten, h nach oben)."""

    def __init__(self, x0_px, y_boden_px, k):
        self.x0, self.yb, self.k = x0_px, y_boden_px, k

    def p(self, x, h):
        return (round(self.x0 + x * self.k, 2), round(self.yb - h * self.k, 2))


def _kasten_text(t):
    from .pruefung import _kasten
    return _kasten(t.x, t.y, t.rot, t.zeilen, t.pt, t.fett)


def _frei(box, belegt, rand=1.0):
    return not any(box[0] < b[2] + rand and b[0] < box[2] + rand and box[1] < b[3] + rand and b[1] < box[3] + rand
                   for b in belegt)


def _schraffur(bl, x0, x1, y, hoehe, abstand=7.0, oben=False, farbe=FARBE_WAND):
    x = x0
    while x < x1 - 1:
        xe = min(x + hoehe, x1)
        if oben:
            bl.linie(x, y, xe, y - (xe - x), breite=0.4, farbe=farbe)
        else:
            bl.linie(x, y + (xe - x), xe, y, breite=0.4, farbe=farbe)
        x += abstand


def _zonen(bl, a: Ansicht, wand: dict, m: dict, mit_mitte: bool, oeff: list[dict], belegt):
    b, decke = _z(wand.get("breite")), m["deckenhoehe"]
    def band(x0, h0, x1, h1):
        p0, p1 = a.p(x0, h1), a.p(x1, h0)
        bl.rechteck(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], breite=0, farbe=FARBE_ZONE, fuellung=FARBE_ZONE)
    waag = [(0.15, 0.45, "ZW-u"), (decke - 0.45, decke - 0.15, "ZW-o")]
    if mit_mitte:
        waag.append((1.00, 1.30, "ZW-m"))
    for h0, h1, _ in waag:
        band(0, h0, b, h1)
    kanten = [(0.0, +1), (b, -1)]
    for o in oeff:
        if o["art"] == "tuer" and o.get("band") in ("links", "rechts") and not o.get("zweifluegelig"):
            kanten.append((o["x1"], +1) if o["band"] == "links" else (o["x0"], -1))
        else:
            kanten += [(o["x0"], -1), (o["x1"], +1)]
    for k, s in kanten:
        xa, xb = sorted((k + s * 0.10, k + s * 0.30))
        if xb > 0 and xa < b:
            band(max(xa, 0), 0, min(xb, b), decke)
    for h0, h1, name in waag:
        hm = (h0 + h1) / 2
        for xl, ausr in ((0.015, "links"), (b - 0.015, "rechts")):
            if any(o["x0"] - 0.1 <= xl <= o["x1"] + 0.1 and o["uk"] <= hm <= o["ok"] for o in oeff):
                continue
            t = text_bei(*a.p(xl, hm), name, 5, h=ausr, v="mitte", farbe=FARBE_ZONE_TEXT)
            k = _kasten_text(t)
            if _frei(k, belegt):
                bl.texte.append(t)
                belegt.append(k)
                break


def _oeffnungen(wand: dict) -> list[dict]:
    out = []
    for d in wand.get("oeffnungen") or []:
        art = _n(d.get("art")).lower() or "fenster"
        art = "tuer" if art.startswith("t") else "fenster"
        x0 = _z(d.get("x"))
        br = _z(d.get("breite"), 0.885 if art == "tuer" else 1.0)
        if art == "tuer":
            uk, ok = 0.0, _z(d.get("hoehe"), 2.01)
        else:
            uk = _z(d.get("bruestung"), 0.90)
            ok = uk + _z(d.get("hoehe"), 1.25)
        band = _n(d.get("anschlag") or d.get("band")).lower()
        band = {"anfang": "links", "ende": "rechts", "l": "links", "r": "rechts"}.get(band, band)
        out.append({**d, "art": art, "x0": x0, "x1": x0 + br, "uk": uk, "ok": ok,
                    "band": band if band in ("links", "rechts") else None,
                    "zweifluegelig": int(d.get("fluegel", 1) or 1) > 1})
    return out


def _zeichne_oeffnung(bl, a: Ansicht, o: dict, belegt):
    p0, p1 = a.p(o["x0"], o["ok"]), a.p(o["x1"], o["uk"])
    w, h = p1[0] - p0[0], p1[1] - p0[1]
    bl.rechteck(p0[0], p0[1], w, h, breite=1.0, farbe=FARBE_WAND, fuellung="#FFFFFF")
    if o["art"] == "fenster":
        r = 0.05 * a.k
        bl.rechteck(p0[0] + r, p0[1] + r, w - 2 * r, h - 2 * r, breite=0.5, farbe=FARBE_WAND)
        txt = _n(o.get("text")) or f"Fenster\nBRH {_de(o['uk'])}"
    else:
        # Öffnungsdreieck: Spitze auf der Bandseite
        if o["band"] == "links":
            bl.polygon([(p1[0], p0[1]), (p0[0], (p0[1] + p1[1]) / 2), (p1[0], p1[1])], breite=0.5,
                       farbe=FARBE_MOEBEL, stil="DashLine", geschlossen=False)
        elif o["band"] == "rechts":
            bl.polygon([(p0[0], p0[1]), (p1[0], (p0[1] + p1[1]) / 2), (p0[0], p1[1])], breite=0.5,
                       farbe=FARBE_MOEBEL, stil="DashLine", geschlossen=False)
        txt = _n(o.get("text")) or "Tür"
    t = text_bei((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, txt, 6, h="mitte", v="mitte", farbe=FARBE_MOEBEL_TEXT)
    bl.texte.append(t)
    belegt.append(_kasten_text(t))


def _zeichne_moebel(bl, a: Ansicht, e: dict, m: dict, belegt):
    art, s = e["art"], e["schicht"]
    stil = "DashLine" if e.get("gestrichelt") else "SolidLine"
    def rect(x0, h0, x1, h1, breite=0.8, fuellung=None, farbe=FARBE_MOEBEL, st=stil):
        p0, p1 = a.p(x0, h1), a.p(x1, h0)
        bl.rechteck(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], breite=breite, farbe=farbe, stil=st,
                    fuellung=fuellung)
    label = _n(e.get("text"))
    if s == "unter":
        sockel = m["sockel"]
        rect(e["x0"], 0, e["x1"], sockel, breite=0.5)
        rect(e["x0"], sockel, e["x1"], e["ok"])
        if art in ("geschirrspueler", "geschirrspüler", "gsp"):
            rect(e["x0"] + 0.01, e["ok"] - 0.10, e["x1"] - 0.01, e["ok"] - 0.02, breite=0.5)
            label = label or "GSP"
        elif art in ("herd", "backofen_unterbau"):
            rect(e["x0"] + 0.04, sockel + 0.08, e["x1"] - 0.04, e["ok"] - 0.14, breite=0.5)
            rect(e["x0"] + 0.10, sockel + 0.20, e["x1"] - 0.10, e["ok"] - 0.26, breite=0.4)
            label = label or "Backofen"
        elif art in ("spuele", "spüle", "spuelenschrank"):
            label = label or "Spüle"
        elif art in ("waschmaschine", "trockner"):
            cx, cy = a.p((e["x0"] + e["x1"]) / 2, (sockel + e["ok"]) / 2)
            r = 0.17 * a.k
            bl.ellipse(cx - r, cy - r, 2 * r, 2 * r, breite=0.5, farbe=FARBE_MOEBEL)
            label = label or ("WM" if art == "waschmaschine" else "Trockner")
        else:
            label = label or f"US {round((e['x1'] - e['x0']) * 100)}"
        if art in ("kochfeld", "kochfeldschrank", "herd") or e.get("kochfeld"):
            p0, p1 = a.p(e["x0"] + 0.04, m["arbeitsplatte"] + 0.012), a.p(e["x1"] - 0.04, m["arbeitsplatte"])
            bl.rechteck(p0[0], p0[1], p1[0] - p0[0], max(p1[1] - p0[1], 2), breite=0.8, farbe="#333333",
                        fuellung="#333333")
            t = text_bei((p0[0] + p1[0]) / 2, p0[1] - 2, "Kochfeld", 5.5, h="mitte", v="unten",
                         farbe=FARBE_MOEBEL_TEXT)
            bl.texte.append(t)
            belegt.append(_kasten_text(t))
        if art in ("spuele", "spüle", "spuelenschrank") or e.get("spuele"):
            ap = m["arbeitsplatte"]
            xm = (e["x0"] + e["x1"]) / 2
            rect(xm - 0.25, ap - 0.20, xm + 0.25, ap, breite=0.5, st="DashLine")
            pa, pb = a.p(xm, ap), a.p(xm, ap + 0.30)
            pc = a.p(xm + 0.14, ap + 0.30)
            bl.polygon([pa, pb, pc, (pc[0], pc[1] + 0.05 * a.k)], breite=1.0, farbe=FARBE_MOEBEL, geschlossen=False)
        h_text = (m["sockel"] + e["ok"]) / 2
    elif s == "hoch":
        rect(e["x0"], 0, e["x1"], m["sockel"], breite=0.5)
        rect(e["x0"], m["sockel"], e["x1"], e["ok"])
        for n in e.get("nischen") or []:
            rect(e["x0"] + 0.03, _z(n.get("uk")), e["x1"] - 0.03, _z(n.get("ok")), breite=0.5)
            ct = a.p((e["x0"] + e["x1"]) / 2, (_z(n.get("uk")) + _z(n.get("ok"))) / 2)
            t = text_bei(*ct, _n(n.get("text")), 5.5, h="mitte", v="mitte", farbe=FARBE_MOEBEL_TEXT)
            bl.texte.append(t)
            belegt.append(_kasten_text(t))
        if not label and not e.get("nischen"):
            label = {"kuehlschrank": "Kühlschrank", "kühlschrank": "Kühlschrank",
                     "backofen_hoch": "Backofen"}.get(art, f"HS {round((e['x1'] - e['x0']) * 100)}")
        h_text = e["ok"] - 0.18 if e.get("nischen") else (m["sockel"] + e["ok"]) / 2
    elif s == "ober":
        rect(e["x0"], e["uk"], e["x1"], e["ok"])
        label = label or f"OS {round((e['x1'] - e['x0']) * 100)}"
        h_text = (e["uk"] + e["ok"]) / 2
    elif s == "platte":
        rect(e["x0"], e["uk"], e["x1"], e["ok"], breite=0.8, fuellung="#EDEDED")
        return
    elif s == "haube":
        form = _n(e.get("form")).lower()
        if form in ("", "wand", "kamin"):
            h_haube = 0.12
            xm = (e["x0"] + e["x1"]) / 2
            kb = _z(e.get("kamin_breite"), 0.30) / 2
            pts = [a.p(e["x0"], e["uk"]), a.p(e["x1"], e["uk"]), a.p(xm + kb + 0.05, e["uk"] + h_haube),
                   a.p(xm - kb - 0.05, e["uk"] + h_haube)]
            bl.polygon(pts, breite=0.8, farbe=FARBE_MOEBEL, stil=stil)
            rect(xm - kb, e["uk"] + h_haube, xm + kb, e["ok"])
            h_text = e["uk"] + h_haube + 0.25
        else:
            rect(e["x0"], e["uk"], e["x1"], e["ok"])
            h_text = (e["uk"] + e["ok"]) / 2
        label = label or "Dunstabzug"
    else:
        rect(e["x0"], e["uk"], e["x1"], e["ok"])
        h_text = (e["uk"] + e["ok"]) / 2
    if label:
        lo, hi = (e["uk"], e["ok"]) if s != "unter" else (m["sockel"], e["ok"])
        for dh in (0, 0.10, -0.10, 0.20, -0.20, 0.30, -0.30):
            hh = h_text + dh
            if not lo + 0.04 <= hh <= hi - 0.04:
                continue
            t = text_bei(*a.p((e["x0"] + e["x1"]) / 2, hh), label, 6, h="mitte", v="mitte",
                         farbe=FARBE_MOEBEL_TEXT)
            if _frei(_kasten_text(t), belegt, 2.0):
                break
        else:
            t = text_bei(*a.p((e["x0"] + e["x1"]) / 2, h_text), label, 6, h="mitte", v="mitte",
                         farbe=FARBE_MOEBEL_TEXT)
        bl.texte.append(t)
        belegt.append(_kasten_text(t))


def _ordinate_h(bl, a: Ansicht, werte: list[float], x_linie: float):
    """Steigende Bemaßung der Höhen links neben der Wand (Ursprung OKFF)."""
    if not werte:
        return
    top = max(werte)
    bl.linie(x_linie, a.yb, x_linie, a.p(0, top)[1], breite=0.6, farbe=FARBE_MASS)
    bl.ellipse(x_linie - 3, a.yb - 3, 6, 6, breite=0.6, farbe=FARBE_MASS, fuellung="#FFFFFF")
    bl.text(x_linie - 6, a.yb, "±0,00", 5.5, h="rechts", v="mitte", farbe=FARBE_MASS)
    letzte = a.yb - 9
    for h in sorted(werte):
        y = a.p(0, h)[1]
        bl.linie(x_linie - 4, y, x_linie + 4, y, breite=0.6, farbe=FARBE_MASS)
        yt = min(y, letzte - 9)
        if abs(yt - y) > 0.5:
            bl.linie(x_linie - 4, y, x_linie - 10, yt, breite=0.4, farbe=FARBE_MASS)
        bl.text(x_linie - 11, yt, _de(h), 5.5, h="rechts", v="mitte", farbe=FARBE_MASS)
        letzte = yt


def _ordinate_x(bl, a: Ansicht, werte: list[float], y_linie: float, breite_m: float):
    """Steigende Bemaßung entlang der Wand unter dem Fußboden (Ursprung linke Wandecke)."""
    xe = a.p(breite_m, 0)[0]
    bl.linie(a.x0, y_linie, xe, y_linie, breite=0.6, farbe=FARBE_MASS)
    bl.ellipse(a.x0 - 3, y_linie - 3, 6, 6, breite=0.6, farbe=FARBE_MASS, fuellung="#FFFFFF")
    bl.text(a.x0, y_linie + 6, "0", 5.5, h="rechts", v="mitte", rot=270, farbe=FARBE_MASS)
    letzte = a.x0 + 2
    max_w = textbreite("0", 5.5)
    for x in sorted(werte):
        px = a.p(x, 0)[0]
        bl.linie(px, y_linie - 4, px, y_linie + 4, breite=0.6, farbe=FARBE_MASS)
        xt = max(px, letzte + 9)
        if abs(xt - px) > 0.5:
            bl.linie(px, y_linie + 4, xt, y_linie + 10, breite=0.4, farbe=FARBE_MASS)
        txt = _de(x)
        bl.text(xt, y_linie + 11, txt, 5.5, h="rechts", v="mitte", rot=270, farbe=FARBE_MASS)
        max_w = max(max_w, textbreite(txt, 5.5))
        letzte = xt
    # Gesamtmaß der Wand
    yg = y_linie + 11 + max_w + 14
    bl.linie(a.x0, yg, xe, yg, breite=0.6, farbe=FARBE_MASS)
    for px in (a.x0, xe):
        bl.linie(px, yg - 6, px, yg + 6, breite=0.4, farbe=FARBE_MASS)
        bl.linie(px - 3, yg + 3, px + 3, yg - 3, breite=1.0, farbe=FARBE_MASS)
    bl.text((a.x0 + xe) / 2, yg - 2, _de(breite_m), 6, h="mitte", v="unten", farbe=FARBE_MASS)


def _koten(bl, a: Ansicht, koten: list[tuple[float, str]], x_px: float):
    """Höhenkoten der Möbel rechts neben der Wand (Dreieck + Text)."""
    letzte = None
    for h, name in sorted(koten, key=lambda k: -k[0]):
        y = a.p(0, h)[1]
        yt = y if letzte is None else max(y, letzte + 9)
        bl.polygon([(x_px, y), (x_px + 4, y - 5), (x_px - 4, y - 5)], breite=0.5, farbe=FARBE_MASS,
                   fuellung=FARBE_MASS)
        bl.linie(x_px - 6, y, x_px + 6, y, breite=0.5, farbe=FARBE_MASS)
        if abs(yt - y) > 0.5:
            bl.linie(x_px + 6, y, x_px + 10, yt, breite=0.4, farbe=FARBE_MASS)
        bl.text(x_px + 11, yt, f"{_de(h)} {name}", 5.5, v="mitte", farbe=FARBE_MASS)
        letzte = yt


def _block_masse(wand: dict, m: dict, k: float) -> tuple[float, float]:
    return (DIM_L + _z(wand.get("breite")) * k + DIM_R, KOPF_H + m["deckenhoehe"] * k + 14 + DIM_U)


def _zeichne_wand(bl, wand: dict, punkte: list[tuple[dict, str]], m: dict, k: float, x_px: float, y_px: float,
                  massstab: int, zonen: bool, hilfslinien: bool):
    b = _z(wand.get("breite"))
    if b <= 0:
        raise ValueError(f"Wand {wand.get('name')!r}: 'breite' (m) angeben")
    decke = m["deckenhoehe"]
    a = Ansicht(x_px + DIM_L, y_px + KOPF_H + decke * k, k)
    belegt: list[tuple] = []
    r = max(DOSE_D / 2 * k, 4.5)
    for p, nr in punkte:
        for (x, h) in dosen(p):
            cx, cy = a.p(x, h)
            belegt.append((cx - r, cy - r, cx + r, cy + r))
    moebel = moebel_der_wand(wand, m)
    oeff = _oeffnungen(wand)
    mit_mitte = bool(arbeitsflaechen(moebel)) or bool(wand.get("arbeitsflaeche"))
    # Titel
    titel = _n(wand.get("name")) or "Wand"
    if _n(wand.get("bezeichnung")):
        titel += f" – {_n(wand.get('bezeichnung'))}"
    zusatz = f"Ansicht 1:{massstab}"
    if textbreite(titel, 9, True) + textbreite(zusatz, 6) + 12 <= b * k + DIM_R - 10:
        bl.text(a.x0, y_px + 4, titel, 9, fett=True)
        bl.text(a.x0 + max(b * k, textbreite(titel, 9, True) + 12 + textbreite(zusatz, 6)), y_px + 8, zusatz, 6,
                h="rechts", farbe=FARBE_MASS)
    else:
        bl.text(a.x0, y_px + 4, f"{titel} · 1:{massstab}", 9, fett=True)
    # Zonen, Wand, Boden, Decke
    if zonen:
        _zonen(bl, a, wand, m, mit_mitte, oeff, belegt)
    p0, p1 = a.p(0, decke), a.p(b, 0)
    bl.rechteck(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], breite=1.0, farbe=FARBE_WAND)
    bl.linie(p0[0] - 8, p1[1], p1[0] + 8, p1[1], breite=2.0, farbe="#000000")
    _schraffur(bl, p0[0] - 8, p1[0] + 8, p1[1], 7)
    bl.linie(p0[0] - 8, p0[1], p1[0] + 8, p0[1], breite=1.2, farbe=FARBE_WAND)
    _schraffur(bl, p0[0] - 8, p1[0] + 8, p0[1], 6, oben=True, farbe="#9A9A9A")
    for o in oeff:
        _zeichne_oeffnung(bl, a, o, belegt)
    for e in sorted(moebel, key=lambda e: {"platte": 1, "haube": 2}.get(e["schicht"], 0)):
        _zeichne_moebel(bl, a, e, m, belegt)
    # Linien (LED-Band, Kanal …)
    for li in wand.get("linien") or []:
        x0, h = _z(li.get("x")), _z(li.get("h"))
        x1 = x0 + _z(li.get("breite"), 1.0)
        art = _n(li.get("art")).lower()
        farbe = {"led": "#C87800", "kanal": "#8B0000"}.get(art, "#333333")
        bl.linie(*a.p(x0, h), *a.p(x1, h), breite=2.2, farbe=farbe, stil="DashLine")
        if _n(li.get("text")):
            t = text_bei(a.p(x1, h)[0] + 3, a.p(x1, h)[1], _n(li.get("text")), 5.5, v="mitte", farbe=farbe)
            bl.texte.append(t)
            belegt.append(_kasten_text(t))
    # Punkte: Dosen maßstäblich, Hilfslinien, Nummern
    xs, hs = set(), set()
    for p, nr in punkte:
        farbe = KATEGORIE_FARBE[kategorie(p)]
        ds = dosen(p)
        x, h = _z(p.get("x")), _z(p.get("h", p.get("hoehe")))
        xs.add(round(x, 3))
        hs.add(round(h, 3))
        if hilfslinien:
            unten = min(dh for _, dh in ds)
            px, py = a.p(x, unten)
            bl.linie(px, py + r, px, a.yb, breite=0.4, farbe=FARBE_HILF, stil="DotLine")
            lx, ly = a.p(min(dx for dx, _ in ds), h)
            bl.linie(a.x0, ly, lx - r, ly, breite=0.4, farbe=FARBE_HILF, stil="DotLine")
        for (dx, dh) in ds:
            cx, cy = a.p(dx, dh)
            bl.ellipse(cx - r, cy - r, 2 * r, 2 * r, breite=1.1, farbe=farbe, fuellung="#FFFFFF")
            bl.linie(cx - 1.5, cy, cx + 1.5, cy, breite=0.4, farbe=farbe)
            bl.linie(cx, cy - 1.5, cx, cy + 1.5, breite=0.4, farbe=farbe)
        # Nummer + Kurzzeichen: freie Stelle um die Kombination suchen
        kurz, _ = kurz_und_name(p)
        gx0 = min(a.p(dx, dh)[0] for dx, dh in ds) - r
        gx1 = max(a.p(dx, dh)[0] for dx, dh in ds) + r
        gy0 = min(a.p(dx, dh)[1] for dx, dh in ds) - r
        gy1 = max(a.p(dx, dh)[1] for dx, dh in ds) + r
        rk = 6.5
        tw = textbreite(kurz, 5.5)
        kandidaten = []
        for abst in (4, 14, 26):
            kandidaten += [("ro", gx1 + abst, gy0 - abst), ("lo", gx0 - abst, gy0 - abst),
                           ("ru", gx1 + abst, gy1 + abst), ("lu", gx0 - abst, gy1 + abst)]
        wahl = None
        for lage, ax, ay in kandidaten:
            if lage.startswith("r"):
                bx0, bx1 = ax, ax + 2 * rk + 2 + tw
            else:
                bx0, bx1 = ax - 2 * rk - 2 - tw, ax
            by0, by1 = (ay - 2 * rk, ay) if lage.endswith("o") else (ay, ay + 2 * rk)
            box = (bx0, by0, bx1, by1)
            if _frei(box, belegt, 1.5):
                wahl = (lage, box)
                break
        if wahl is None:
            lage, ax, ay = kandidaten[0]
            wahl = (lage, (ax, ay - 2 * rk, ax + 2 * rk + 2 + tw, ay))
        lage, (bx0, by0, bx1, by1) = wahl
        if lage.startswith("r"):
            kx = bx0 + rk
            tx, th = kx + rk + 2, "links"
        else:
            kx = bx1 - rk
            tx, th = kx - rk - 2, "rechts"
        ky = (by0 + by1) / 2
        # Führungslinie von der Dosengruppe zum Kreis
        ex = gx1 if lage.startswith("r") else gx0
        ey = gy0 if lage.endswith("o") else gy1
        if math.hypot(kx - ex, ky - ey) > rk + 3:
            vx, vy = kx - ex, ky - ey
            n = math.hypot(vx, vy)
            bl.linie(ex, ey, kx - vx / n * rk, ky - vy / n * rk, breite=0.4, farbe=farbe)
        bl.ellipse(kx - rk, ky - rk, 2 * rk, 2 * rk, breite=0.7, farbe=farbe, fuellung="#FFFFFF")
        bl.text(kx, ky, nr, 6 if len(nr) < 3 else 5, h="mitte", v="mitte", fett=True, farbe=farbe)
        bl.text(tx, ky, kurz, 5.5, h=th, v="mitte", farbe=farbe)
        belegt.append((bx0, by0, bx1, by1))
    # Bemaßung
    _ordinate_h(bl, a, sorted(hs), a.x0 - 22)
    _ordinate_x(bl, a, sorted(xs), a.yb + 18, b)
    koten = [(decke, "Decke")]
    platten = [e for e in moebel if e["schicht"] == "platte"]
    if platten:
        koten.append((max(e["ok"] for e in platten), "AP"))
    ober = [e for e in moebel if e["schicht"] == "ober"]
    if ober:
        koten.append((min(e["uk"] for e in ober), "UK OS"))
        koten.append((max(e["ok"] for e in ober), "OK OS"))
    hoch = [e for e in moebel if e["schicht"] == "hoch"]
    if hoch and not any(abs(max(e["ok"] for e in hoch) - h) < 0.005 for h, _ in koten):
        koten.append((max(e["ok"] for e in hoch), "OK HS"))
    for e in moebel:
        if e["schicht"] == "haube":
            koten.append((e["uk"], "UK DA"))
    for o in oeff:
        if o["art"] == "fenster":
            koten.append((o["uk"], "BRH"))
    _koten(bl, a, koten, a.p(b, 0)[0] + 12)
    return a, moebel


def _punkteliste(bl, x0, y0, breite, zeilen):
    """zeilen: [(nr, punkt, wandname)]"""
    from .installationsplan import _ankerversatz, _symbol_fuer
    bl.text(x0, y0, "Elektropunkte", 9, fett=True)
    spalten = [("Nr.", 26), ("Symbol", 44), ("Bezeichnung", 170), ("x", 38), ("h", 38), ("SK", 40),
               ("Bemerkung", breite - 356)]
    y = y0 + 22
    xx = x0
    for name, w in spalten:
        bl.text(xx + 2, y, name, 6, fett=True)
        xx += w
    y += 14
    bl.linie(x0, y, x0 + breite, y, breite=0.8)
    for nr, p, wname in zeilen:
        kat = kategorie(p)
        farbe = KATEGORIE_FARBE[kat]
        xx = x0
        mitte = y + ZEILE_H / 2
        bl.ellipse(xx + 4, mitte - 7, 14, 14, breite=0.7, farbe=farbe)
        bl.text(xx + 11, mitte, nr, 6 if len(nr) < 3 else 5, h="mitte", v="mitte", fett=True, farbe=farbe)
        xx += spalten[0][1]
        try:
            d_sym = dict(p)
            if _n(p.get("symbol")).lower() in ("auslass", "unterbauleuchte"):
                d_sym = {"symbol": "leuchte", "art": "wand"}
            elif _n(p.get("symbol")).lower() in ("leuchte",) and _n(p.get("art")).lower() not in \
                    ("decke", "wand", "spot", "lang", "not", "strahler"):
                d_sym = {"symbol": "leuchte", "art": "wand"}
            elif _n(p.get("symbol")).lower() in ("geraet", "anschluss", "geraeteanschluss", "herd"):
                d_sym = {"symbol": "geraet", "text": kurz_und_name(p)[0]}
            elif _n(p.get("symbol")).lower() == "thermostat":
                d_sym = {"symbol": "melder", "text": "RTR"}
            sym, _ = _symbol_fuer(d_sym)
            bl.setze(sym, xx + 18, mitte - _ankerversatz(sym), 0)
        except ValueError:
            pass
        xx += spalten[1][1]
        _, name = kurz_und_name(p)
        zeile_text = name if len(name) <= 42 else name[:40] + "…"
        bl.text(xx + 2, mitte - (5 if wname else 0), zeile_text, 6, v="mitte")
        if wname:
            bl.text(xx + 2, mitte + 6, wname, 5, v="mitte", farbe=FARBE_MOEBEL_TEXT)
        xx += spalten[2][1]
        hwert = _z(p.get("h", p.get("hoehe")))
        senk = _n(p.get("richtung")).lower().startswith("s") and int(p.get("anzahl", 1) or 1) > 1
        for wert in (_de(_z(p.get("x"))), _de(hwert) + ("*" if senk else "")):
            bl.text(xx + spalten[3][1] - 4, mitte, wert, 6, h="rechts", v="mitte")
            xx += spalten[3][1]
        bl.text(xx + 2, mitte, _n(p.get("stromkreis")), 6, v="mitte", fett=True)
        xx += spalten[5][1]
        bem = _n(p.get("bemerkung"))
        if bem:
            max_z = int(spalten[6][1] / (schriftpx(5.5) * 0.5))
            zeilen_b, akt = [], ""
            for wort in bem.split():
                if len(akt) + len(wort) + 1 > max_z and akt:
                    zeilen_b.append(akt)
                    akt = wort
                else:
                    akt = f"{akt} {wort}".strip()
            zeilen_b.append(akt)
            bl.text(xx + 2, mitte, "\n".join(zeilen_b[:3]), 5.5, v="mitte")
        y += ZEILE_H
        bl.linie(x0, y, x0 + breite, y, breite=0.3, farbe="#BBBBBB")
    return y


def _legende_hinweise(bl, x0, y0, breite, zonen, m):
    y = y0 + 10
    bl.text(x0, y, "Farben", 7, fett=True)
    y += 20
    sp = breite / 2
    for i, (kat, name) in enumerate(KATEGORIE_NAME.items()):
        xx = x0 + (i % 2) * sp
        yy = y + (i // 2) * 14
        bl.ellipse(xx + 2, yy - 4, 9, 9, breite=1.0, farbe=KATEGORIE_FARBE[kat], fuellung="#FFFFFF")
        bl.text(xx + 16, yy + 0.5, name, 5.5, v="mitte")
    y += 3 * 14 + 4
    if zonen:
        bl.rechteck(x0 + 2, y - 4, 22, 9, breite=0, farbe=FARBE_ZONE, fuellung=FARBE_ZONE)
        bl.text(x0 + 30, y + 0.5, "Installationszonen DIN 18015-3 (ZW-u/-m/-o waagerecht, ZS senkrecht)", 5.5,
                v="mitte")
        y += 14
    hinweise = [
        "Maße in m. x = Dosenmitte ab linker Wandecke (fertige Wand), h = Dosenmitte über OKFF.",
        "Mehrfachkombination: x = Mitte, h = Dosenmitte; * = senkrecht, h = oberste Dose.",
        "Dosen maßstäblich Ø 68 mm, Raster 71 mm. Höhen über Meterriss prüfen (Meterriss = OKFF + 1,00 m).",
        f"Möbelmaße (AP {_de(m['arbeitsplatte'])}, UK OS {_de(m['oberschrank_uk'])}) aus der Küchenplanung "
        "übernehmen und vor dem Schlitzen mit dem Küchenbauer abstimmen.",
        "Geräteanschlüsse nach Herstellerangabe (Einbauanleitung) – Lage hinter/neben dem Gerät.",
    ]
    for h in hinweise:
        bl.text(x0, y, h, 5.5)
        y += 10
    return y


# --------------------------------------------------------------------------
def baue(daten: dict, fmt: Format) -> Projekt:
    proj = daten.get("projekt", {})
    titel = _n(daten.get("titel")) or f"Wandansichten {_n(daten.get('raum')) or 'Küche'}"
    waende = daten.get("waende") or []
    if not waende:
        raise ValueError('Wandansicht: "waende" mit mindestens einer Wand angeben')
    m = masse(daten)
    zonen = daten.get("zonen", True) is not False
    hilfslinien = daten.get("hilfslinien", True) is not False
    fx, fy, fw, fh = fmt.zeichenflaeche(False)
    vw = fw - TAB_B - 3 * RAND
    vh = fh - 2 * RAND
    zeilen_max = int((fh - 2 * RAND - 40 - 180) // ZEILE_H)
    nummern = punkte_nummerieren(daten)

    def passt(mst):
        k = 1000 / mst / MM_PRO_PX
        return all(_block_masse(w, m, k)[0] <= vw and _block_masse(w, m, k)[1] <= vh for w in waende)
    if daten.get("massstab"):
        massstab = int(daten["massstab"])
    else:
        massstab = next((s for s in MASSSTAEBE if passt(s)), MASSSTAEBE[-1])
    k = 1000 / massstab / MM_PRO_PX

    # Wände auf Blätter verteilen (Reihen von links nach rechts, Platz für die Punkteliste)
    blaetter_waende: list[list[tuple[dict, float, float]]] = [[]]
    cx, cy, zeilen_h, anzahl = 0.0, 0.0, 0.0, 0
    for w in waende:
        bw, bh = _block_masse(w, m, k)
        np_ = len(w.get("punkte") or [])
        if blaetter_waende[-1] and cx + bw > vw:
            cx, cy = 0.0, cy + zeilen_h + 10
            zeilen_h = 0.0
        if blaetter_waende[-1] and (cy + bh > vh or anzahl + np_ > zeilen_max):
            blaetter_waende.append([])
            cx, cy, zeilen_h, anzahl = 0.0, 0.0, 0.0, 0
        blaetter_waende[-1].append((w, cx, cy))
        cx += bw + 10
        zeilen_h = max(zeilen_h, bh)
        anzahl += np_

    felder = dict(kunde=_n(proj.get("kunde")), objekt=_n(proj.get("objekt")),
                  auftrag=_n(proj.get("auftrag")), datum=_n(proj.get("datum")),
                  bearbeiter=_n(proj.get("bearbeiter")) or _firma.bearbeiter(),
                  indexrev=_n(proj.get("revision")) or "A",
                  anlage=_n(daten.get("anlage")) or f"{_n(daten.get('raum')) or 'Küche'} · Maßstab 1:{massstab}",
                  plantyp="Wandansicht · Höhen über OKFF · Symbole DIN EN 60617-11")
    projekt = Projekt(titel)
    for i, liste in enumerate(blaetter_waende, 1):
        bl = Blatt(fmt, titel if len(blaetter_waende) == 1 else f"{titel} ({i}/{len(blaetter_waende)})",
                   raster_anzeigen=False)
        # Blöcke im Ansichtsbereich zentrieren
        breite_belegt = max((cx + _block_masse(w, m, k)[0] for w, cx, cy in liste), default=0)
        hoehe_belegt = max((cy + _block_masse(w, m, k)[1] for w, cx, cy in liste), default=0)
        ox = fx + RAND + max(0.0, (vw - breite_belegt) / 2)
        oy = fy + RAND + max(0.0, (vh - hoehe_belegt) / 2)
        zeilen = []
        for w, cx, cy in liste:
            pkt = [(p, nr) for ww, p, nr in nummern if ww is w]
            _zeichne_wand(bl, w, pkt, m, k, ox + cx, oy + cy, massstab, zonen, hilfslinien)
            wname = _n(w.get("name")) if len(waende) > 1 else ""
            zeilen += [(nr, p, wname) for p, nr in pkt]
        tx = fx + fw - TAB_B - RAND
        y_ende = _punkteliste(bl, tx, fy + RAND, TAB_B, zeilen)
        _legende_hinweise(bl, tx, max(y_ende + 10, fy + fh - RAND - 175), TAB_B, zonen, m)
        bl.felder = dict(felder)
        projekt.blaetter.append(bl)
    return projekt


# --------------------------------------------------------------------------
# Normhinweise (nur Hinweise, die Entscheidung bleibt bei der Elektrofachkraft)
# --------------------------------------------------------------------------
def normhinweise(daten: dict) -> list[str]:
    from .normpruefung import (BEDIENHOEHE_BF, GERAETE_KUECHE, SCHALTER_MAX, TOL, ZS, ZW_M, ZW_U,
                               ausstattungswert, tabelle, _ist_geraet)
    m = masse(daten)
    decke = m["deckenhoehe"]
    barrierefrei = bool(daten.get("barrierefrei"))
    wert = ausstattungswert(daten)
    zaehl_einsatz = _n(daten.get("zaehlweise")).lower().startswith("eins")
    raum = (_n(daten.get("raum")) + " " + _n(daten.get("nutzung"))).lower()
    ist_kueche = _n(daten.get("plan")).lower() in ("kuechenplan", "küchenplan") or \
        any(w in raum for w in ("küche", "kueche", "kochnische")) or _n(daten.get("nutzung")).lower() == "kueche"
    out = []
    alle = []
    nummern = punkte_nummerieren(daten)
    for w in daten.get("waende") or []:
        wname = _n(w.get("name")) or "Wand"
        b = _z(w.get("breite"))
        moebel = moebel_der_wand(w, m)
        oeff = _oeffnungen(w)
        aflaechen = arbeitsflaechen(moebel)
        mit_mitte = bool(aflaechen) or bool(w.get("arbeitsflaeche"))
        kanten = [0.0, b]
        for o in oeff:
            if o["art"] == "tuer" and o["band"] and not o["zweifluegelig"]:
                kanten.append(o["x1"] if o["band"] == "links" else o["x0"])
            else:
                kanten += [o["x0"], o["x1"]]
        zonen_waag = [ZW_U, (decke - 0.45, decke - 0.15)] + ([ZW_M] if mit_mitte else [])
        ausserhalb, verdeckt, ueber = [], [], []
        pkt = [(p, nr) for ww, p, nr in nummern if ww is w]
        for p, nr in pkt:
            kat = kategorie(p)
            x, h = _z(p.get("x")), _z(p.get("h", p.get("hoehe")))
            alle.append((w, p, nr, kat))
            if kat in ("steckdose", "schalter", "kommunikation", "geraet"):
                in_waag = any(lo - TOL <= dh <= hi + TOL for _, dh in dosen(p) for lo, hi in zonen_waag)
                in_senk = any(ZS[0] - TOL <= abs(x - kk) <= ZS[1] + TOL for kk in kanten)
                if not (in_waag or in_senk):
                    ausserhalb.append(nr)
            if kat == "schalter":
                if barrierefrei and abs(h - BEDIENHOEHE_BF) > TOL:
                    out.append(f"{wname} Pkt. {nr}: Schalter h = {_de(h)} m – barrierefrei nach DIN 18040-2 "
                               "(4.5.2) Bedienhöhe grundsätzlich 0,85 m")
                elif not barrierefrei and h > SCHALTER_MAX + TOL:
                    out.append(f"{wname} Pkt. {nr}: Schalter h = {_de(h)} m – DIN 18015-3 (5.3): Schaltermitte "
                               "höchstens 1,05 m")
                for o in oeff:
                    if o["art"] != "tuer":
                        continue
                    for kante, ist_band in ((o["x0"], o["band"] == "links"), (o["x1"], o["band"] == "rechts")):
                        dist = abs(x - kante)
                        if (x < o["x0"] and kante == o["x0"]) or (x > o["x1"] and kante == o["x1"]):
                            if dist < 0.6 and ist_band and not o["zweifluegelig"]:
                                out.append(f"{wname} Pkt. {nr}: Schalter auf der Bandseite der Tür – DIN 18015-3 "
                                           "(4.2.3): Zone an einflügeligen Türen nur an der Schlossseite")
                            elif dist < 0.6 and not (ZS[0] - TOL <= dist <= ZS[1] + TOL):
                                out.append(f"{wname} Pkt. {nr}: Schalter {_de(dist * 100, 0)} cm neben der Tür – "
                                           "DIN 18015-3: Streifen 10–30 cm neben der Rohbaukante")
            if kat == "steckdose" and not _n(p.get("text")):
                for e in moebel:
                    if e["schicht"] in ("unter", "hoch", "ober") and e["x0"] + 0.02 < x < e["x1"] - 0.02 \
                            and e["uk"] + 0.02 < h < e["ok"] - 0.02:
                        verdeckt.append((nr, _n(e.get("text")) or e["art"]))
                        break
            if kat in ("steckdose", "schalter"):
                for e in moebel:
                    spuele = e["art"] in ("spuele", "spüle", "spuelenschrank") or e.get("spuele")
                    kochfeld = e["art"] in ("kochfeld", "kochfeldschrank", "herd") or e.get("kochfeld")
                    if (spuele or kochfeld) and e["x0"] - 0.05 <= x <= e["x1"] + 0.05 and \
                            m["arbeitsplatte"] < h < m["arbeitsplatte"] + 0.60:
                        ueber.append((nr, "Spüle" if spuele else "Kochfeld"))
                        break
        if ausserhalb:
            out.append(f"{wname}: Pkt. {', '.join(ausserhalb)} außerhalb der Installationszonen (DIN 18015-3) – "
                       "Zuleitung als senkrechte Stichleitung aus einer Zone; bei individuell geplanter Küche "
                       "zulässig (5.3 Anm. 2), Lage dokumentieren")
        for nr, wo in verdeckt:
            out.append(f"{wname} Pkt. {nr}: Steckdose liegt hinter dem Möbel ({wo}) – als Geräteanschluss gedacht? "
                       "Dann \"text\" angeben (z. B. GS, KS)")
        for nr, wo in ueber:
            out.append(f"Praxis {wname} Pkt. {nr}: direkt über {wo} – Spritzwasser/Hitze, seitlich versetzen "
                       "(keine Normvorgabe, Herstellerangaben beachten)")
        # Steckdosen über der Arbeitsfläche
        je = 2 if wert == "1" else 3
        for a0, a1, ok in aflaechen:
            os_uk = min([e["uk"] for e in moebel if e["schicht"] == "ober" and e["x0"] < a1 and e["x1"] > a0]
                        or [ok + 0.65])
            n_ist = 0
            for p, nr in pkt:
                if kategorie(p) != "steckdose":
                    continue
                x, h = _z(p.get("x")), _z(p.get("h", p.get("hoehe")))
                if a0 - 1e-6 <= x <= a1 + 1e-6 and ok < h < max(os_uk, ok + 0.35):
                    n_ist += int(p.get("anzahl", 1) or 1) if zaehl_einsatz else 1
            laenge = a1 - a0
            soll = math.ceil(laenge / 1.2 - 1e-9) * je
            if n_ist < soll:
                was = "Steckdosen" if zaehl_einsatz else "Steckdosen-Auslässen"
                out.append(f"{wname}: Arbeitsfläche {_de(laenge)} m mit {n_ist} {was} – "
                           f"{'DIN 18015-2' if wert == '1' else 'RAL-RG 678'} verlangt {je} je angefangene 1,20 m = {soll}"
                           + ("" if zaehl_einsatz else " (Kombination = 1 Auslass; \"zaehlweise\": \"einsatz\" zählt "
                              "jede Steckdose)"))
            for p, nr in pkt:
                if kategorie(p) != "steckdose":
                    continue
                x, h = _z(p.get("x")), _z(p.get("h", p.get("hoehe")))
                if a0 <= x <= a1 and ok - 0.02 < h < ok + 0.08:
                    out.append(f"{wname} Pkt. {nr}: Steckdose nur {_de((h - ok) * 100, 0)} cm über der Arbeitsplatte – "
                               "Vorzugshöhe über Arbeitsflächen 1,15 m (DIN 18015-3, 5.3), Rückwand/Aufkantung beachten")
    # Ausstattung der Küche (alle Wände zusammen)
    if ist_kueche and alle:
        t = tabelle()
        typ = next((x for x in (t or {}).get("raeume", []) if x["typ"] == "kueche"), None)
        if typ:
            werte = typ["werte"].get(wert) or typ["werte"]["1"]
            pkte = [p for _, p, _, _ in alle]
            fehlt = []
            for geraet, muster in GERAETE_KUECHE.items():
                if not any(_ist_geraet(p, muster) for p in pkte):
                    fehlt.append(f"Anschluss {geraet}")
            if werte.get("sd_kuehl") and not any(_ist_geraet(p, (r"^(ks|kg|gf|kü|kue)$", r"kühl|kuehl|gefrier"))
                                                  for p in pkte):
                fehlt.append("Steckdose Kühl-/Gefriergerät")
            if werte.get("sd_dunstabzug") and not any(_ist_geraet(p, (r"^(da|dah|dh)$", r"dunst|haube|abzug"))
                                                       for p in pkte):
                fehlt.append("Steckdose/Anschluss Dunstabzug")
            if werte.get("iuk") and not any(_n(p.get("symbol")).lower() in ("daten", "lan", "netzwerk", "telefon")
                                            for p in pkte):
                fehlt.append("Telefon-/Datenanschluss (IuK) mit Steckdose")
            sonder = (r"^$", r"kühl|kuehl|gefrier|dunst|haube|abzug")
            n_sd = sum((int(p.get("anzahl", 1) or 1) if zaehl_einsatz else 1)
                       for p in pkte if kategorie(p) == "steckdose" and not _ist_geraet(p, sonder))
            soll_allg = werte.get("steckdosen", 3)
            if isinstance(soll_allg, list):
                soll_allg = soll_allg[0]["anzahl"]
            af_soll = 0
            for w in daten.get("waende") or []:
                for a0, a1, _ in arbeitsflaechen(moebel_der_wand(w, m)):
                    af_soll += math.ceil((a1 - a0) / 1.2 - 1e-9) * (werte.get("sd_arbeitsflaeche") or 0)
            soll_sd = soll_allg + af_soll + (werte.get("sd_iuk_ruk") or 0)
            if n_sd < soll_sd:
                fehlt.append(f"{n_sd} von {soll_sd} Steckdosen ({soll_allg} allgemein + {af_soll} Arbeitsfläche + "
                             f"{werte.get('sd_iuk_ruk') or 0} IuK/RuK; Kühl/Dunstabzug extra)")
            if fehlt:
                quelle = "DIN 18015-2 Tab. 2" if wert == "1" else f"RAL-RG 678 Ausstattungswert {wert}"
                out.append(f"Küche: {', '.join(fehlt)} nach {quelle}")
    return out
