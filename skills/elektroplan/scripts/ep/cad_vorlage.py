"""Zum Selberzeichnen in CADCraft: Symbol-Palette und Elektro-Vorlage.

Palette  – alle Installationssymbole als Blöcke EP_* im Planmaßstab, jedes Wandsymbol in
           vier Richtungen (Wand oben / unten / links / rechts), Beschriftung immer waagrecht.
           In CADCraft als zweiten Reiter öffnen, Symbol mit Basispunkt kopieren
           (Strg+Umschalt+C, Einfügepunkt anklicken) und im Plan einfügen (Strg+V).
Vorlage  – Startzeichnung mit Layern ELT_*, Textstilen, Bemaßungsstilen und allen Blöcken,
           auf Wunsch mit dem Architektengrundriss (Vektor-PDF) maßgenau 1:1 in mm.

Aufruf:
  python -X utf8 cad_vorlage.py palette AUSGABE.dxf [--massstab 50]
  python -X utf8 cad_vorlage.py vorlage AUSGABE.dxf [--massstab 50] [--grundriss PLAN.pdf [--seite 1]]
Neben der DXF entstehen DWG und PDF (Palette) bzw. DWG (Vorlage).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ep.cad_symbole import STANDARD, blockdefinition, cad_symbol, grundbefehle   # noqa: E402
    from ep.cadplan import Geraet, _beschriftungen, bemassungsstile, patche_attribute  # noqa: E402
    from ep.grundriss_dxf import Grundriss, befehl, cadcraft                           # noqa: E402
    from ep.symbole import symbol                                                      # noqa: E402
else:
    from .cad_symbole import STANDARD, blockdefinition, cad_symbol, grundbefehle
    from .cadplan import Geraet, _beschriftungen, bemassungsstile, patche_attribute
    from .grundriss_dxf import Grundriss, befehl, cadcraft
    from .symbole import symbol

# Richtung → Drehung des Blocks (0 = Symbol hängt von der Wand oben in den Raum)
RICHTUNGEN = [("Wand oben", 0), ("Wand unten", 180), ("Wand links", 90), ("Wand rechts", 270)]
HOEHE = {"steckdose": 0.30, "fernmelde": 0.30, "geraet": 0.30, "schalter": 1.05,
         "leuchte": 2.00, "klingel": 1.05}


class _OhneWand:
    """Grundlage ohne Wände – die Beschriftung darf überall hin."""
    def in_wand(self, x, y):
        return False


def _symbole():
    return [cad_symbol(symbol(f, **p), w) for f, p, w in STANDARD]


def _kopf(m: float) -> list[str]:
    syms = _symbole()
    c = [befehl("new", metric=True), befehl("units", insunits=4)] + grundbefehle() + bemassungsstile(m)
    for i, cs in enumerate(syms):
        c += blockdefinition(cs, i)
    return c, syms


def palette(ziel: Path, m: float = 50.0) -> Path:
    c, syms = _kopf(m)
    c += [befehl("layer.new", name="ELT_PALETTE", color=8, lineweight=0.13),
          befehl("layer.set", name="ELT_PALETTE", plot=True)]
    sp_x = [0.0, 44.0, 88.0, 132.0]                # Spalten in Papier-mm
    zeile = 22.0                                   # Zeilenabstand in Papier-mm
    x0 = 70.0                                      # links Platz für den Symbolnamen
    geraete = []
    c += [befehl("layer.current", name="ELT_PALETTE"), befehl("style.current", name="PLAN_FETT"),
          befehl("text", at=[0, 30 * m], text=f"Symbol-Palette Elektro 1:{m:g}  (DIN EN 60617-11)",
                 height=round(4 * m, 1)),
          befehl("style.current", name="PLAN")]
    for i, zeile_text in enumerate([
            "1. Diese Palette und den Plan in CADCraft öffnen (zwei Reiter).",
            "2. Hier: Strg+Umschalt+C, Einfügepunkt des Symbols anklicken (Fang „Einfügung“), Symbol wählen, Enter.",
            "3. Im Plan: Strg+V und den Punkt auf die Wandoberfläche setzen (Fang „Nächster“ bzw. „Lot“).",
            "4. Stromkreis / Höhe ändern: Doppelklick auf das Symbol (oder ATTEDIT). Nicht ATTSYNC verwenden."]):
        c.append(befehl("text", at=[0, round((25 - i * 3.2) * m, 1)], text=zeile_text,
                        height=round(2.0 * m, 1)))
    for k, (titel, _) in enumerate(RICHTUNGEN):
        c.append(befehl("text", at=[round((x0 + sp_x[k]) * m, 1), 9 * m], text=titel,
                        height=round(2.4 * m, 1)))
    for r, cs in enumerate(syms):
        y = -r * zeile * m
        c += [befehl("layer.current", name="ELT_PALETTE"),
              befehl("text", at=[0, round(y - 1.5 * m, 1)], text=cs.name, height=round(2.2 * m, 1)),
              befehl("text", at=[0, round(y - 5.0 * m, 1)], text=cs.block, height=round(1.6 * m, 1))]
        richt = RICHTUNGEN if cs.wand else [("Decke", 0)]
        for k, (_, rot) in enumerate(richt):
            x = (x0 + sp_x[k]) * m
            # Wand links/rechts: Ursprung (Wandpunkt) in die Spaltenmitte, Symbol ragt seitlich
            d = {"stromkreis": "UV" if cs.familie == "verteiler" else "F1",
                 "hoehe": HOEHE.get(cs.familie, "") if cs.wand else ""}
            ge = Geraet(d, cs, round(x, 1), round(y, 1), rot, cs.wand, False)
            geraete.append(ge)
            at = ge.attribute()
            c += [befehl("layer.current", name=cs.layer),
                  befehl("insert", name=cs.block, at=[ge.x, ge.y], scale=m, rotation=rot, attribs=at)]
            if cs.wand:                            # Wandlinie zur Orientierung
                lx, ly = {0: (1, 0), 180: (1, 0), 90: (0, 1), 270: (0, 1)}[rot]
                h = 6 * m
                c += [befehl("layer.current", name="ELT_PALETTE"),
                      befehl("line", points=[[round(ge.x - lx * h, 1), round(ge.y - ly * h, 1)],
                                             [round(ge.x + lx * h, 1), round(ge.y + ly * h, 1)]])]
    _beschriftungen(geraete, m, _OhneWand(), [])
    c += [befehl("layer.current", name="ELT_STECKDOSEN"), befehl("zoom", mode="extents")]
    return _schreiben(c, ziel, geraete, pdf=True)


def vorlage(ziel: Path, m: float = 50.0, grundriss: Path | None = None, seite: int = 1) -> Path:
    c, _ = _kopf(m)
    if grundriss:
        g = Grundriss.aus_pdf(grundriss, m, seite)
        c += g.befehle()
    c += [befehl("layer.current", name="ELT_STECKDOSEN"), befehl("dimstyle.current", name=_dimstil()),
          befehl("zoom", mode="extents")]
    return _schreiben(c, ziel, [], pdf=False)


def _dimstil() -> str:
    """Name des Meter-Bemaßungsstils aus bemassungsstile() (EP_M)."""
    for b in bemassungsstile(50):
        if '"current": true' in b:
            return b.split('"name": "')[1].split('"')[0]
    return "Standard"


def _schreiben(c: list[str], ziel: Path, geraete, pdf: bool) -> Path:
    ziel = Path(ziel).with_suffix(".dxf")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    scr = ziel.with_suffix(".scr")
    scr.write_text("\n".join(c) + "\n", encoding="utf-8")
    cadcraft("run", "--script-file", scr, "--save", ziel)
    if geraete:
        patche_attribute(ziel, geraete)
    nach = [befehl("saveas", path=str(ziel.with_suffix(".dwg")), format="dwg")]
    args = ["run", ziel]
    for b in nach:
        args += ["--cmd", b]
    if pdf:
        args += ["--export", ziel.with_suffix(".pdf"), "--view", "extents"]
    cadcraft(*args)
    scr.unlink(missing_ok=True)
    return ziel


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("art", choices=["palette", "vorlage"])
    ap.add_argument("ausgabe", type=Path)
    ap.add_argument("--massstab", type=float, default=50.0)
    ap.add_argument("--grundriss", type=Path, help="Architektenplan als Vektor-PDF (nur vorlage)")
    ap.add_argument("--seite", type=int, default=1)
    a = ap.parse_args(argv)
    if a.art == "palette":
        p = palette(a.ausgabe, a.massstab)
    else:
        p = vorlage(a.ausgabe, a.massstab, a.grundriss, a.seite)
    print(f"{a.art}: {p}  (+ .dwg{', .pdf' if a.art == 'palette' else ''}), Maßstab 1:{a.massstab:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
