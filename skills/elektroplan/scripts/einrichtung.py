"""Einrichtung des Skills elektroplan: Firmen-Stammdaten, Logo, Excel-Vorlage, Testblatt.

Die Daten landen im Konfigurationsordner ~/.elektroplan (oder ELEKTROPLAN_HOME), nie im Skill.

Aufruf:
  python einrichtung.py                       interaktiv im Terminal (fragt alles ab)
  python einrichtung.py status                was ist eingerichtet, was fehlt (für Claude)
  python einrichtung.py pruefen               Python-Pakete und QElectroTech prüfen
  python einrichtung.py setzen --name "…" [--inhaber "…" --strasse "…" --ort "…" --telefon "…"
                         --mail "…" --web "…" --titel "…" --installateurverzeichnis "…"
                         --hwk-nr "…" --bearbeiter "…" --akzentfarbe "#1F5FAD" --ablage "…"]
                         [--logo PFAD]        Stammdaten setzen/ändern (nur angegebene Felder)
  python einrichtung.py logo PFAD             Logo übernehmen (PNG, JPG, WebP, BMP oder PDF)
  python einrichtung.py vorlage               Excel-Vorlage Stromkreisliste neu erzeugen
  python einrichtung.py test [--ziel ORDNER]  Testplan mit eigenem Schriftfeld als PDF + PNG
  python einrichtung.py paket [--ziel ORDNER] persönliches Skill-ZIP mit eigenen Firmendaten
                                              (zum Hochladen in claude.ai › Einstellungen › Skills)
  python einrichtung.py zuruecksetzen         Firmendaten löschen (fragt nach)
"""
from __future__ import annotations

import argparse
import importlib
import json
import platform
import shutil
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

from ep import firma  # noqa: E402

PAKETE = {"reportlab": "reportlab", "fitz": "PyMuPDF", "PIL": "Pillow", "openpyxl": "openpyxl"}
LOGO_ENDUNGEN = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".pdf"}


# ----------------------------------------------------------------------------- Prüfen
def fehlende_pakete() -> list[str]:
    fehlt = []
    for modul, paket in PAKETE.items():
        try:
            importlib.import_module(modul)
        except ImportError:
            fehlt.append(paket)
    return fehlt


def qelectrotech_pfad() -> Path | None:
    kandidaten = []
    if platform.system() == "Windows":
        for basis in (Path("C:/Program Files"), Path("C:/Program Files (x86)")):
            kandidaten += [basis / "QElectroTech" / "bin" / "qelectrotech.exe",
                           basis / "QElectroTech" / "qelectrotech.exe"]
    elif platform.system() == "Darwin":
        kandidaten.append(Path("/Applications/QElectroTech.app"))
    gefunden = shutil.which("qelectrotech")
    if gefunden:
        kandidaten.insert(0, Path(gefunden))
    return next((k for k in kandidaten if k.exists()), None)


def cmd_pruefen(_a=None) -> int:
    ok = True
    v = sys.version_info
    print(f"Python:        {v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 9) else "  ← mindestens 3.9 nötig"))
    ok &= v >= (3, 9)
    fehlt = fehlende_pakete()
    if fehlt:
        ok = False
        print(f"Pakete:        FEHLEN: {', '.join(fehlt)}")
        print(f"               Installieren: {Path(sys.executable).name} -m pip install {' '.join(fehlt)}")
    else:
        print("Pakete:        ok (reportlab, PyMuPDF, Pillow, openpyxl)")
    q = qelectrotech_pfad()
    print(f"QElectroTech:  {q if q else 'nicht gefunden (optional – nur zum Bearbeiten der .qet nötig, qelectrotech.org)'}")
    print(f"Konfiguration: {firma.konfig_ordner()}")
    return 0 if ok else 1


# ----------------------------------------------------------------------------- Status
def status() -> dict:
    d = firma.lade()
    pflicht_fehlt = [k for k, (_, pflicht, _) in firma.FELDER.items() if pflicht and not d.get(k)]
    empfohlen = ["inhaber", "strasse", "ort", "telefon"]
    return {
        "eingerichtet": firma.eingerichtet(),
        "konfig_ordner": str(firma.konfig_ordner()),
        "firma": {k: v for k, v in d.items() if not k.startswith("_")} if firma.eingerichtet() else {},
        "pflicht_fehlt": pflicht_fehlt,
        "empfohlen_fehlt": [k for k in empfohlen if not d.get(k)] if firma.eingerichtet() else empfohlen,
        "logo": str(firma.logo_pfad()) if firma.logo_pfad() else None,
        "excel_vorlage": str(firma.stromkreisliste_vorlage()) if firma.stromkreisliste_vorlage() else None,
        "pakete_fehlen": fehlende_pakete(),
        "qelectrotech": str(qelectrotech_pfad()) if qelectrotech_pfad() else None,
    }


def cmd_status(_a=None) -> int:
    print(json.dumps(status(), ensure_ascii=False, indent=2))
    return 0


# ----------------------------------------------------------------------------- Logo
def logo_uebernehmen(quelle: Path) -> Path:
    """Logo prüfen, Ränder beschneiden, als PNG in den Konfigurationsordner legen."""
    from PIL import Image, ImageChops
    quelle = Path(quelle).expanduser()
    if not quelle.exists():
        raise SystemExit(f"Logo nicht gefunden: {quelle}")
    if quelle.suffix.lower() not in LOGO_ENDUNGEN:
        raise SystemExit(f"Logo-Format {quelle.suffix} wird nicht unterstützt – bitte PNG, JPG oder PDF "
                         "(SVG vorher als PNG exportieren).")
    if quelle.suffix.lower() == ".pdf":
        import fitz
        with fitz.open(quelle) as doc:
            pix = doc[0].get_pixmap(dpi=300, alpha=True)
            import io
            bild = Image.open(io.BytesIO(pix.tobytes("png")))
    else:
        bild = Image.open(quelle)
    bild = bild.convert("RGBA")
    # weißen bzw. transparenten Rand abschneiden
    weiss = Image.new("RGBA", bild.size, (255, 255, 255, 255))
    hinten = Image.alpha_composite(weiss, bild).convert("RGB")
    box = ImageChops.difference(hinten, Image.new("RGB", bild.size, (255, 255, 255))).getbbox()
    if box:
        bild = bild.crop(box)
    if max(bild.size) > 1600:
        f = 1600 / max(bild.size)
        bild = bild.resize((round(bild.width * f), round(bild.height * f)), Image.LANCZOS)
    ziel = firma.konfig_ordner() / "logo.png"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "PNG", optimize=True)
    d = firma.lade()
    d["logo"] = "logo.png"
    firma.speichere(d)
    print(f"Logo:          {ziel}  ({bild.width} × {bild.height} px)")
    if bild.width / max(1, bild.height) > 6 or bild.height / max(1, bild.width) > 2:
        print("HINWEIS: ungewöhnliches Seitenverhältnis – im Schriftfeld wird das Logo dann sehr klein. "
              "Ein kompakteres Logo (eher quer, ca. 2:1) sieht besser aus.")
    return ziel


def cmd_logo(a) -> int:
    logo_uebernehmen(a.pfad)
    return 0


# ----------------------------------------------------------------------------- Vorlage / Test
def vorlage_erzeugen() -> Path | None:
    try:
        from ep.excel_vorlage import erzeuge
    except ImportError as e:
        print(f"Excel-Vorlage: übersprungen ({e})")
        return None
    pfad = erzeuge(firma.vorlagen_ordner())
    print(f"Excel-Vorlage: {pfad}")
    return pfad


def cmd_vorlage(_a=None) -> int:
    return 0 if vorlage_erzeugen() else 1


def testblatt(ziel: Path | None = None) -> list[Path]:
    from elektroplan import baue
    from ep.pdf_writer import schreibe_pdf, vorschau_png
    from ep.qet_writer import schreibe_qet
    beispiel = HIER.parent / "referenz" / "beispiele" / "verteilerplan_wohnung.json"
    daten = json.loads(beispiel.read_text(encoding="utf-8"))
    daten.setdefault("projekt", {})["bearbeiter"] = firma.bearbeiter()
    ziel = Path(ziel or firma.konfig_ordner() / "testblatt")
    ziel.mkdir(parents=True, exist_ok=True)
    projekt = baue(daten)
    pdf = ziel / "Testblatt Verteilerplan.pdf"
    schreibe_qet(projekt, ziel / "Testblatt Verteilerplan.qet")
    schreibe_pdf(projekt, pdf)
    pngs = vorschau_png(pdf, ziel)
    print(f"Testblatt:     {pdf}")
    for p in pngs:
        print(f"Vorschau:      {p}")
    return [pdf, *pngs]


def cmd_test(a) -> int:
    testblatt(a.ziel)
    return 0


# ----------------------------------------------------------------------------- Setzen
def cmd_setzen(a) -> int:
    d = firma.lade() if firma.konfig_datei().exists() else {}
    geaendert = []
    for feld in firma.FELDER:
        wert = getattr(a, feld, None)
        if wert is not None:
            d[feld] = wert.strip()
            geaendert.append(feld)
    if not str(d.get("name") or "").strip():
        raise SystemExit("Der Firmenname (--name) fehlt – ohne ihn bleibt der Skill uneingerichtet.")
    farbe = str(d.get("akzentfarbe") or "")
    if farbe and not (len(farbe.lstrip("#")) == 6 and all(c in "0123456789abcdefABCDEF" for c in farbe.lstrip("#"))):
        raise SystemExit(f"Akzentfarbe {farbe!r} ist kein Hex-Wert wie #1F5FAD")
    pfad = firma.speichere(d)
    print(f"Gespeichert:   {pfad}  ({', '.join(geaendert) or 'keine Änderung'})")
    if a.logo:
        logo_uebernehmen(a.logo)
    if not a.ohne_vorlage:
        vorlage_erzeugen()
    return 0


# ----------------------------------------------------------------------------- Interaktiv
def _frage(text: str, vorgabe: str = "", beispiel: str = "") -> str:
    hinweis = f" [{vorgabe}]" if vorgabe else (f" (z. B. {beispiel})" if beispiel else "")
    try:
        antwort = input(f"  {text}{hinweis}: ").strip()
    except EOFError:                              # keine Tastatur (z. B. aus Claude heraus gestartet)
        raise SystemExit("\nKeine Eingabe möglich – im Terminal starten oder in Claude "
                         "„elektroplan einrichten“ sagen (nutzt „einrichtung.py setzen“).")
    return antwort or vorgabe


def cmd_interaktiv(_a=None) -> int:
    print("=" * 66)
    print(" Einrichtung Skill „elektroplan“ – deine Firmendaten fürs Schriftfeld")
    print("=" * 66)
    print(f" Gespeichert wird in {firma.konfig_ordner()} (nicht im Skill-Ordner).")
    print(" Leer lassen = Feld weglassen bzw. bisherigen Wert behalten.\n")
    if cmd_pruefen() != 0:
        print("\nBitte zuerst die fehlenden Pakete installieren (Befehl oben) und dann erneut starten.")
        return 1
    print()
    d = firma.lade() if firma.konfig_datei().exists() else {}
    for feld, (text, pflicht, beispiel) in firma.FELDER.items():
        if feld == "bearbeiter":
            beispiel = firma.bearbeiter() or beispiel
        while True:
            wert = _frage(text + (" *" if pflicht else ""), str(d.get(feld) or ""), beispiel)
            if wert or not pflicht:
                break
            print("    Pflichtfeld.")
        if wert:
            d[feld] = wert
    firma.speichere(d)
    print()
    while True:
        logo = _frage("Pfad zum Firmenlogo (PNG/JPG/PDF, leer = ohne Logo)",
                      str(firma.logo_pfad() or "")).strip('"')
        if not logo or Path(logo).expanduser() == firma.logo_pfad():
            break
        try:
            logo_uebernehmen(Path(logo))
            break
        except SystemExit as e:
            print(f"    {e}")
    print()
    vorlage_erzeugen()
    try:
        testblatt()
    except Exception as e:                        # Testblatt ist nur Komfort
        print(f"Testblatt:     nicht erzeugt ({e})")
    print("\nFertig. Prüfe das Testblatt – Ändern jederzeit mit „python einrichtung.py“ "
          "oder in Claude: „Firmendaten für elektroplan ändern“.")
    return 0


def cmd_paket(a) -> int:
    """Skill + eigene Firmendaten als ZIP für claude.ai (dort gibt es kein ~/.elektroplan)."""
    import zipfile
    if not firma.eingerichtet():
        raise SystemExit("Erst einrichten (python einrichtung.py), dann das Paket bauen.")
    skill = HIER.parent
    ziel_ordner = Path(a.ziel or Path.home() / "Downloads")
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    zip_pfad = ziel_ordner / "elektroplan-persoenlich.zip"
    quelle_konfig = firma.konfig_ordner()
    with zipfile.ZipFile(zip_pfad, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(skill.rglob("*")):
            rel = p.relative_to(skill)
            if p.is_dir() or "__pycache__" in rel.parts or rel.parts[0] == "firma":
                continue
            z.write(p, Path("elektroplan") / rel)
        for p in sorted(quelle_konfig.rglob("*")):
            rel = p.relative_to(quelle_konfig)
            if p.is_dir() or rel.parts[0] == "testblatt":
                continue
            z.write(p, Path("elektroplan") / "firma" / rel)
    print(f"Paket:         {zip_pfad}")
    print("               Enthält deine Firmendaten – nur selbst hochladen, nicht weitergeben.")
    return 0


def cmd_zuruecksetzen(a) -> int:
    ordner = firma.konfig_ordner()
    if not ordner.exists():
        print("Nichts eingerichtet.")
        return 0
    if not a.ja and _frage(f"Ordner {ordner} wirklich löschen? (ja/nein)", "nein").lower() != "ja":
        print("Abgebrochen.")
        return 1
    shutil.rmtree(ordner)
    print(f"Gelöscht: {ordner}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="befehl")
    sub.add_parser("status")
    sub.add_parser("pruefen")
    s = sub.add_parser("setzen")
    for feld, (text, _, _) in firma.FELDER.items():
        s.add_argument("--" + feld.replace("_", "-"), dest=feld, help=text)
    s.add_argument("--logo", type=Path)
    s.add_argument("--ohne-vorlage", action="store_true", help="Excel-Vorlage nicht neu erzeugen")
    lg = sub.add_parser("logo")
    lg.add_argument("pfad", type=Path)
    sub.add_parser("vorlage")
    t = sub.add_parser("test")
    t.add_argument("--ziel", type=Path)
    pk = sub.add_parser("paket")
    pk.add_argument("--ziel", type=Path)
    z = sub.add_parser("zuruecksetzen")
    z.add_argument("--ja", action="store_true")
    a = ap.parse_args(argv)
    befehle = {"status": cmd_status, "pruefen": cmd_pruefen, "setzen": cmd_setzen, "logo": cmd_logo,
               "vorlage": cmd_vorlage, "test": cmd_test, "paket": cmd_paket,
               "zuruecksetzen": cmd_zuruecksetzen}
    return befehle.get(a.befehl, cmd_interaktiv)(a)


if __name__ == "__main__":
    sys.exit(main())
