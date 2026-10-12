"""Symbolkatalog als PDF/QET erzeugen (alle Symbole mit Namen und JSON-Bezeichnung).

Aufruf: python symbolkatalog.py --ziel ORDNER
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ep.blatt import format_von  # noqa: E402
from ep.model import Blatt, Projekt  # noqa: E402
from ep.pdf_writer import schreibe_pdf, vorschau_png  # noqa: E402
from ep.qet_writer import schreibe_qet  # noqa: E402
from ep.symbole import symbol  # noqa: E402

GRUPPEN = [
    ("Verteilerplan (einpolig)", [
        ("ls", {}, "LS"), ("fi", {}, "FI"), ("fils", {}, "FI/LS"), ("hauptschalter", {}, "Hauptschalter"),
        ("trenner", {}, "Trennschalter"), ("sicherung", {}, "Sicherung"), ("spd", {}, "Überspannungsschutz"),
        ("zaehler", {}, "Zähler"), ("kasten", {"text": "SST"}, "geraet: Stromstoßschalter"),
        ("kasten", {"text": "TLZ"}, "geraet: Treppenlicht"), ("erde", {}, "Erde/PE"), ("abgang", {}, "Abgang"),
    ]),
    ("Stromlaufplan (allpolig)", [
        ("schliesser", {"oben": "13", "unten": "14"}, "schliesser"), ("oeffner", {"oben": "11", "unten": "12"}, "oeffner"),
        ("schliesser", {"antrieb": "hand"}, "schalter"), ("schliesser", {"antrieb": "druck"}, "taster"),
        ("wechsler", {"antrieb": "hand", "oben": True, "nc_rechts": True}, "Wechselschalter"),
        ("kreuzschalter", {}, "Kreuzschalter"), ("serienschalter", {}, "Serienschalter"),
        ("ls3", {}, "LS 3-polig"), ("spule", {}, "spule"), ("spule", {"art": "rv"}, "spule rv (TLZ)"),
        ("spule", {"art": "sst"}, "spule sst"), ("spule", {"art": "av"}, "spule av"),
        ("leuchte", {}, "leuchte"), ("steckdose", {}, "Steckdose"), ("motor", {}, "motor"),
        ("drehstrom", {"text": "Herd"}, "herd"), ("kasten_n", {"text": "BWM"}, "Bewegungsmelder"),
    ]),
    ("Installationsplan (DIN EN 60617-11)", [
        ("i_steckdose", {}, "steckdose"), ("i_steckdose", {"anzahl": 2}, "steckdose anzahl 2"),
        ("i_steckdose", {"anzahl": 3}, "steckdose anzahl 3"), ("i_fernmelde", {"text": "TV"}, "tv"),
        ("i_fernmelde", {"text": "LAN"}, "daten"), ("i_schalter", {"art": "aus"}, "schalter aus"),
        ("i_schalter", {"art": "zweipolig"}, "schalter zweipolig"), ("i_schalter", {"art": "serie"}, "schalter serie"),
        ("i_schalter", {"art": "wechsel"}, "schalter wechsel"), ("i_schalter", {"art": "kreuz"}, "schalter kreuz"),
        ("i_schalter", {"art": "dimmer"}, "dimmer"), ("i_schalter", {"art": "taster"}, "taster"),
        ("i_schalter", {"art": "kontroll"}, "schalter kontroll"), ("i_leuchte", {"art": "decke"}, "leuchte"),
        ("i_leuchte", {"art": "wand"}, "wandleuchte"), ("i_leuchte", {"art": "spot"}, "spot"),
        ("i_leuchte", {"art": "lang"}, "leuchte lang"), ("i_leuchte", {"art": "not"}, "leuchte not"),
        ("i_dose", {"art": "abzweig"}, "dose abzweig"), ("i_dose", {"art": "anschluss"}, "dose anschluss"),
        ("i_geraet", {"text": "H"}, "geraet H"), ("i_verteiler", {}, "verteiler"),
        ("i_melder", {"text": "RM"}, "rauchmelder"), ("i_klingel", {}, "klingel"),
    ]),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ziel", type=Path, required=True)
    a = ap.parse_args(argv)
    fmt = format_von("A3 quer")
    bl = Blatt(fmt, "Symbolkatalog Elektroplan", dict(
        anlage="Symbolsatz nach DIN EN 60617 · Skill elektroplan",
        plantyp="Unter jedem Symbol: Name und Bezeichnung im Plan-JSON", bearbeiter="",
        datum="08.10.2026", indexrev="A"),
        raster_anzeigen=False)
    fx, fy, fw, fh = fmt.zeichenflaeche(False)
    y = fy + 30
    for titel, liste in GRUPPEN:
        bl.text(fx + 20, y, titel, 9, fett=True)
        y += 70
        x = fx + 60
        for typ, params, json_name in liste:
            s = symbol(typ, **params)
            x0, y0, x1, y1 = s.grenzen()
            bl.setze(s, x - (x0 + x1) / 2, y - (y0 + y1) / 2)
            bl.text(x, y + 40, s.name, 5.5, h="mitte")
            bl.text(x, y + 49, json_name, 5.5, h="mitte", farbe="#B87333")
            x += 115
            if x > fx + fw - 50:
                x = fx + 60
                y += 120
        y += 105
    p = Projekt("Symbolkatalog", [bl])
    a.ziel.mkdir(parents=True, exist_ok=True)
    schreibe_pdf(p, a.ziel / "Symbolkatalog.pdf")
    schreibe_qet(p, a.ziel / "Symbolkatalog.qet")
    print(vorschau_png(a.ziel / "Symbolkatalog.pdf", a.ziel, dpi=110))


if __name__ == "__main__":
    main()
