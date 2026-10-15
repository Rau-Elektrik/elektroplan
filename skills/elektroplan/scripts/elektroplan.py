"""Elektroplan erzeugen: QElectroTech-Datei (.qet) + PDF + Vorschaubilder.

Aufruf:
  python elektroplan.py PLAN.json [--ziel ORDNER] [--name DATEINAME] [--format "A3 quer"]
                       [--vorschau ORDNER | --keine-vorschau]
  python elektroplan.py STROMKREISLISTE.xlsx ...   (Verteilerplan aus der Excel-Vorlage)

PLAN.json enthält "plan": "verteilerplan" | "stromlaufplan" | "installationsplan" | "wandansicht"
  ("kuechenplan" = Wandansicht der Küche mit Möbeln, Elektropunkten und Höhen) | "deckenspiegel"
  (Leuchten nach DIN EN 12464-1 berechnen und setzen, Blatt 2 = Lichtberechnung).
Verteilung (mit "schutzorgane"): --darstellung einpolig | allpolig | beide,
  --stromkreisliste füllt zusätzlich die Excel-Vorlage „Verteilerdokumentation Stromkreisliste“ aus.
Installationsplan/Deckenspiegel: --cadcraft erzeugt zusätzlich DXF + DWG + PDF über CADCraft
  (Grundriss als maßgenaue Vektorgeometrie), --nur-cadcraft nur diese Ausgabe.
Format siehe referenz/plan_format.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ep.blatt import format_von  # noqa: E402
from ep.pdf_writer import schreibe_pdf, vorschau_png  # noqa: E402
from ep.pruefung import pruefe  # noqa: E402
from ep.qet_writer import schreibe_qet  # noqa: E402

STANDARDFORMAT = {"verteilerplan": "A3 quer", "stromlaufplan": "A4 quer",
                  "installationsplan": "A3 quer", "wandansicht": "A3 quer", "kuechenplan": "A3 quer",
                  "deckenspiegel": "A3 quer"}


def lade(pfad: Path) -> dict:
    if pfad.suffix.lower() in (".xlsx", ".xlsm", ".xltx"):
        from ep.stromkreisliste import lese_stromkreisliste
        return lese_stromkreisliste(pfad)
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    daten.setdefault("_basis", str(pfad.resolve().parent))   # für relative Bildpfade
    return daten


def baue(daten: dict, fmt_name: str | None = None, darstellung: str | None = None):
    art = str(daten.get("plan", "")).lower().strip()
    fmt = format_von(fmt_name or daten.get("format") or STANDARDFORMAT.get(art, "A3 quer"))
    # Verteilung (Stromkreisliste): einpolig, allpolig oder beide Darstellungen
    hat_liste = bool(daten.get("schutzorgane"))
    if art == "verteilerplan" or (art == "stromlaufplan" and hat_liste):
        d = (darstellung or daten.get("darstellung")
             or ("allpolig" if art == "stromlaufplan" else "einpolig")).lower()
        from ep import verteiler_allpolig, verteilerplan
        if d == "einpolig":
            return verteilerplan.baue(daten, fmt)
        if d == "allpolig":
            return verteiler_allpolig.baue(daten, fmt)
        if d == "beide":
            p1 = verteilerplan.baue(daten, fmt)
            p2 = verteiler_allpolig.baue(dict(daten, _blatt_offset=len(p1.blaetter)), fmt)
            p1.blaetter += p2.blaetter
            return p1
        raise SystemExit(f'Unbekannte Darstellung {d!r} – "einpolig", "allpolig" oder "beide"')
    if art == "stromlaufplan":
        from ep import stromlaufplan as m
    elif art == "installationsplan":
        from ep import installationsplan as m
    elif art in ("wandansicht", "kuechenplan", "küchenplan"):
        from ep import wandansicht as m
    elif art in ("deckenspiegel", "lichtplanung", "lichtplan"):
        from ep import deckenspiegel as m
    else:
        raise SystemExit(f'Unbekannte Planart {art!r} – erwartet "verteilerplan", '
                         f'"stromlaufplan", "installationsplan", "wandansicht"/"kuechenplan" oder "deckenspiegel"')
    return m.baue(daten, fmt)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("eingabe", type=Path)
    ap.add_argument("--ziel", type=Path, help="Ausgabeordner (Standard: neben der Eingabe)")
    ap.add_argument("--name", help="Dateiname ohne Endung")
    ap.add_argument("--format", help='Blattformat: "A3 quer", "A4 quer", "A4 hoch"')
    ap.add_argument("--vorschau", type=Path, help="Ordner für PNG-Vorschaubilder")
    ap.add_argument("--keine-vorschau", action="store_true")
    ap.add_argument("--stromkreisliste", action="store_true",
                    help="nur Verteilung: Excel-Stromkreisliste aus der eigenen Vorlage ausfüllen (NAME.xlsx)")
    ap.add_argument("--darstellung", choices=["einpolig", "allpolig", "beide"],
                    help="nur Verteilung: einpoliger Übersichtsschaltplan, allpoliger "
                         "Stromlaufplan oder beide in einer Datei")
    ap.add_argument("--cadcraft", action="store_true",
                    help="Installationsplan/Deckenspiegel zusätzlich als CADCraft-Zeichnung "
                         "(NAME CAD.dxf/.dwg/.pdf, Grundriss maßgenau aus Vektor-PDF oder Räumen)")
    ap.add_argument("--nur-cadcraft", action="store_true", help="nur die CADCraft-Ausgabe")
    a = ap.parse_args(argv)

    from ep import firma
    if not firma.eingerichtet():
        print("HINWEIS (Einrichtung): Keine Firmendaten gefunden – das Schriftfeld zeigt einen Platzhalter. "
              "Einrichten mit: python einrichtung.py")
    daten = lade(a.eingabe)
    if a.cadcraft or a.nur_cadcraft:
        art = str(daten.get("plan", "")).lower().strip()
        if art not in ("installationsplan", "deckenspiegel", "lichtplanung", "lichtplan"):
            raise SystemExit("--cadcraft gibt es nur für Installationsplan und Deckenspiegel")
        from ep.programme import cadcraft_cli
        if not cadcraft_cli():
            raise SystemExit("CADCraft fehlt. Installieren mit: python einrichtung.py installieren cadcraft "
                             "(oder von https://github.com/storytold/cadcraft/releases)")
    if a.nur_cadcraft:
        return cad_ausgabe(daten, a)
    projekt = baue(daten, a.format, a.darstellung)
    ziel = a.ziel or a.eingabe.parent
    ziel.mkdir(parents=True, exist_ok=True)
    name = a.name or daten.get("dateiname") or a.eingabe.stem
    qet, pdf = ziel / f"{name}.qet", ziel / f"{name}.pdf"
    schreibe_qet(projekt, qet)
    schreibe_pdf(projekt, pdf)
    print(f"QElectroTech: {qet}")
    print(f"PDF:          {pdf}  ({len(projekt.blaetter)} Blatt)")
    for w in pruefe(projekt):
        print(f"HINWEIS (Layout): {w}")
    for w in daten.get("_hinweise_allpolig", []):
        print(f"HINWEIS (Annahme): {w}")
    if daten.get("schutzorgane"):
        from ep.verteilerplan import plausibilitaet
        for w in plausibilitaet(daten):
            print(f"HINWEIS (fachlich): {w}")
    from ep.normpruefung import pruefe as normpruefung
    for w in normpruefung(daten):
        print(f"HINWEIS (Norm): {w}")
    from ep.deckenspiegel import hinweise as lichthinweise
    for w in lichthinweise(daten):
        print(f"HINWEIS (Licht): {w}")
    if daten.get("_leuchten_export"):
        exp = ziel / f"{name} Leuchten.json"
        exp.write_text(json.dumps(daten["_leuchten_export"], ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Leuchten:     {exp}  (zum Übernehmen in den Installationsplan)")
    if daten.get("schutzorgane") and (a.stromkreisliste or daten.get("stromkreisliste"))             and a.eingabe.suffix.lower() not in (".xlsx", ".xlsm", ".xltx"):
        from ep.stromkreisliste import schreibe_stromkreisliste
        xlsx, hinw = schreibe_stromkreisliste(daten, ziel / f"{name} Stromkreisliste.xlsx")
        if xlsx:
            print(f"Excel:        {xlsx}")
        for w in hinw:
            print(f"HINWEIS (Annahme): {w}")
    if not a.keine_vorschau:
        vz = a.vorschau or ziel
        vz.mkdir(parents=True, exist_ok=True)
        for p in vorschau_png(pdf, vz):
            print(f"Vorschau:     {p}")
    if a.cadcraft:
        cad_ausgabe(daten, a)


def cad_ausgabe(daten: dict, a):
    """CADCraft-Zeichnung: Skripte, DXF, DWG, PDF (+ Vorschau-PNG)."""
    from ep.cadplan import erzeuge
    ziel = a.ziel or a.eingabe.parent
    name = (a.name or daten.get("dateiname") or a.eingabe.stem)
    if a.cadcraft and not name.endswith(" CAD"):
        name += " CAD"           # neben der QET-PDF nicht überschreiben
    erg = erzeuge(daten, ziel, name, basis=Path(daten.get("_basis", ".")),
                  vorschau=None if a.keine_vorschau else (a.vorschau or ziel))
    print(f"CADCraft DXF: {erg['dxf']}")
    print(f"CADCraft DWG: {erg['dwg']}")
    print(f"CADCraft PDF: {erg['pdf']}  (A3, Maßstab 1:{erg['massstab']:g})")
    print(f"Skripte:      {erg['skripte'][0].name}, {erg['skripte'][1].name}")
    print(f"Geräte:       {erg['geraete']}, davon {erg['eingerastet']} an der Wand eingerastet")
    if erg.get("vorschau"):
        print(f"Vorschau:     {erg['vorschau']}")
    for h in erg["hinweise"]:
        print(f"HINWEIS {h}" if h.startswith("(") else f"HINWEIS (CAD): {h}")
    if a.nur_cadcraft:
        from ep.normpruefung import pruefe as normpruefung
        for w in normpruefung(daten):
            print(f"HINWEIS (Norm): {w}")
    return 0


if __name__ == "__main__":
    main()
