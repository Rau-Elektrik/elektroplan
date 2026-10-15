"""Installationssymbole (DIN EN 60617-11) als CADCraft-Blöcke mit Attributen.

Die Geometrie kommt unverändert aus symbole.py (QElectroTech-Pixel, 1 px = 0,25 mm
auf dem Papier, y nach unten) und wird in Papier-mm mit y nach oben umgerechnet.
Blockursprung = Wandpunkt, das Symbol ragt in -y-Richtung (in den Raum).
Eingefügt wird mit Faktor = Maßstab (1:50 → 50) im Modell bzw. 1 in der Legende.

Attribute je Block: SK (Stromkreis), HOEHE (h über OKFF), BEM (Bemerkung).

Als Skript: python -X utf8 cad_symbole.py AUSGABEORDNER
            → Symbolbibliothek CADCraft.dxf / .dwg / .pdf (alle Standardblöcke mit Namen)
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ep.grundriss_dxf import befehl, cadcraft            # noqa: E402
    from ep.model import ASCENT, PX_PRO_PT                 # noqa: E402
    from ep.symbole import symbol                          # noqa: E402
else:
    from .grundriss_dxf import befehl, cadcraft
    from .model import ASCENT, PX_PRO_PT
    from .symbole import symbol

MM = 0.25                       # Papier-mm je Symbolpixel
H_SK, H_INFO = 1.8, 1.4         # Schrifthöhe der Attribute auf dem Papier (mm)
ABLAGE = (-200000.0, -200000.0)  # freier Bereich zum Zusammenbauen der Blöcke (Papier-mm)

# Layer je Symbolfamilie: (Layer, Farbe ACI, Linienstärke mm)
LAYER = {
    "verteiler": ("ELT_VERTEILER", 7, 0.35), "steckdose": ("ELT_STECKDOSEN", 7, 0.25),
    "geraet": ("ELT_GERAETE", 7, 0.25), "fernmelde": ("ELT_DATEN", 5, 0.25),
    "schalter": ("ELT_SCHALTER", 7, 0.25), "leuchte": ("ELT_LEUCHTEN", 7, 0.25),
    "dose": ("ELT_DOSEN", 7, 0.18), "melder": ("ELT_MELDER", 7, 0.25),
    "klingel": ("ELT_SCHWACHSTROM", 5, 0.25),
}
WEITERE_LAYER = [("ELT_LEITUNGEN", 7, 0.25), ("ELT_LINIEN", 7, 0.35), ("ELT_TEXT", 8, 0.18),
                 ("ELT_RAUM", 8, 0.18), ("ELT_LEGENDE", 7, 0.18), ("ELT_SCHRIFTFELD", 7, 0.25),
                 ("ELT_RAHMEN", 7, 0.5), ("ELT_LOGO", 7, 0.0),
                 ("ELT_MASSE", 7, 0.18)]


@dataclass
class CadSymbol:
    block: str               # Blockname EP_…
    name: str                # Klartext für die Legende
    familie: str             # Schlüssel in LAYER
    sym: object              # symbole.Symbol
    grenzen: tuple           # x0, y0, x1, y1 in Papier-mm (y nach oben)
    wand: bool               # an der Wand (Ursprung auf der Wandoberfläche)

    @property
    def layer(self) -> str:
        return LAYER[self.familie][0]


def _slug(s: str) -> str:
    s = s.upper().replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE").replace("ß", "SS")
    return re.sub(r"[^A-Z0-9]+", "_", s).strip("_")


def _blockname(key: str) -> tuple[str, str]:
    """Symbolschlüssel aus symbole.py → (Blockname, Familie)."""
    teile = key.split("_")
    fam = teile[1]
    rest = teile[2:]
    if fam == "steckdose":
        n, sk = rest
        return f"EP_SD_{n}FACH" + ("" if sk == "1" else "_OHNE_SK"), fam
    kurz = {"schalter": "SCHALTER", "leuchte": "LEUCHTE", "fernmelde": "FM", "geraet": "GERAET",
            "melder": "MELDER", "dose": "DOSE", "verteiler": "VERTEILER", "klingel": "KLINGEL"}[fam]
    return "_".join(["EP", kurz] + [_slug(r) for r in rest if r]), fam


def cad_symbol(sym, wand: bool, legende: str = "") -> CadSymbol:
    block, fam = _blockname(sym.key)
    if legende:
        block += "_" + _slug(legende)[:40]
    x0, y0, x1, y1 = sym.grenzen()
    return CadSymbol(block, legende or sym.name, fam, sym,
                     (x0 * MM, -y1 * MM, x1 * MM, -y0 * MM), wand)


# --------------------------------------------------------------------------
def _p(x, y, ox, oy):
    return [round(ox + x * MM, 4), round(oy - y * MM, 4)]


def geometrie(sym, ox: float, oy: float) -> list[str]:
    """Zeichenbefehle eines Symbols am Punkt (ox, oy) in Papier-mm."""
    out, fuellen = [], []
    for pr in sym.prims:
        a = pr.attrs
        if pr.tag == "line":
            p1, p2 = _p(a["x1"], a["y1"], ox, oy), _p(a["x2"], a["y2"], ox, oy)
            if p1 != p2:
                out.append(befehl("line", points=[p1, p2]))
        elif pr.tag == "rect":
            pts = [_p(a["x"], a["y"], ox, oy), _p(a["x"] + a["width"], a["y"], ox, oy),
                   _p(a["x"] + a["width"], a["y"] + a["height"], ox, oy),
                   _p(a["x"], a["y"] + a["height"], ox, oy)]
            out.append(befehl("pline", vertices=pts, closed=True))
            if "filling:black" in a.get("style", ""):
                fuellen.append(pts)
        elif pr.tag == "ellipse":
            c = _p(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2, ox, oy)
            if abs(a["width"] - a["height"]) < 1e-6:
                out.append(befehl("circle", center=c, radius=round(a["width"] / 2 * MM, 4)))
                if "filling:black" in a.get("style", ""):
                    r = a["width"] / 2 * MM
                    out.append(befehl("donut", center=c, inside=0, outside=round(2 * r, 4)))
            else:
                out.append(befehl("ellipse", center=c, major=[round(a["width"] / 2 * MM, 4), 0],
                                  ratio=a["height"] / a["width"]))
        elif pr.tag == "arc":
            c = _p(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2, ox, oy)
            s, w = float(a["start"]), float(a["angle"])
            if w < 0:
                s, w = s + w, -w
            out.append(befehl("arc", center=c, radius=round(a["width"] / 2 * MM, 4),
                              start=s, end=s + w))
        elif pr.tag == "polygon":
            pts, i = [], 1
            while f"x{i}" in a:
                pts.append(_p(a[f"x{i}"], a[f"y{i}"], ox, oy))
                i += 1
            zu = a.get("closed") == "true"
            out.append(befehl("pline", vertices=pts, closed=zu))
            if "filling:black" in a.get("style", "") and zu:
                fuellen.append(pts)
        elif pr.tag == "text":
            h = a["pt"] * PX_PRO_PT * ASCENT * 0.8 * MM        # Versalhöhe ≈ 0,72 em
            out.append(befehl("text", at=_p(a["x"], a["y"], ox, oy), text=a["text"],
                              height=round(h, 3)))
    for pts in fuellen:
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        out.append(befehl("hatch", points=[[round(cx, 4), round(cy, 4)]], pattern="SOLID"))
    return out


def blockdefinition(cs: CadSymbol, nr: int) -> list[str]:
    """Block cs.block an einer freien Stelle zeichnen, Attribute anlegen, zum Block machen."""
    ox, oy = ABLAGE[0] + nr * 100.0, ABLAGE[1]
    x1 = cs.grenzen[2]
    c = [befehl("layer.current", name="0"), befehl("color", color="ByBlock")]
    c += geometrie(cs.sym, ox, oy)
    tx = ox + x1 + 1.0
    c += [befehl("style.current", name="PLAN_FETT"),
          befehl("attdef", tag="SK", prompt="Stromkreis", default="", at=[tx, oy - 1.0],
                 height=H_SK),
          befehl("style.current", name="PLAN"),
          befehl("attdef", tag="HOEHE", prompt="Montagehöhe über OKFF", default="",
                 at=[tx, oy - 1.0 - 2.4], height=H_INFO),
          befehl("attdef", tag="BEM", prompt="Bemerkung", default="",
                 at=[tx, oy - 1.0 - 4.6], height=H_INFO),
          befehl("color", color="ByLayer"),
          befehl("select", window=[[ox - 40, oy - 40], [ox + 40, oy + 40]]),
          befehl("block", name=cs.block, base=[ox, oy], keep="delete",
                 description=cs.name),
          befehl("ai_deselect")]
    return c


def grundbefehle() -> list[str]:
    """Linientypen, Textstile und alle ELT-Layer."""
    c = [befehl("linetype", load="*"),
         befehl("style", name="PLAN", font="arial.ttf", current=True),
         befehl("style", name="PLAN_FETT", font="arialbd.ttf")]
    for name, col, lw in list(LAYER.values()) + WEITERE_LAYER:
        c.append(befehl("layer.new", name=name, color=col, lineweight=lw))
    return c


# --------------------------------------------------------------------------
STANDARD = [  # (symbole-Fabrik, Parameter, an der Wand)
    ("i_verteiler", {}, True),
    ("i_steckdose", {"anzahl": 1}, True), ("i_steckdose", {"anzahl": 2}, True),
    ("i_steckdose", {"anzahl": 3}, True), ("i_steckdose", {"anzahl": 4}, True),
    ("i_steckdose", {"anzahl": 1, "schutzkontakt": False}, True),
    ("i_geraet", {"text": "H"}, True), ("i_geraet", {"text": "GS"}, True),
    ("i_geraet", {"text": "WM"}, True), ("i_geraet", {"text": "DLE"}, True),
    ("i_fernmelde", {"text": "LAN"}, True), ("i_fernmelde", {"text": "TV"}, True),
    ("i_fernmelde", {"text": "TEL"}, True),
    ("i_schalter", {"art": "aus"}, True), ("i_schalter", {"art": "zweipolig"}, True),
    ("i_schalter", {"art": "serie"}, True), ("i_schalter", {"art": "wechsel"}, True),
    ("i_schalter", {"art": "kreuz"}, True), ("i_schalter", {"art": "taster"}, True),
    ("i_schalter", {"art": "taster_licht"}, True), ("i_schalter", {"art": "dimmer"}, True),
    ("i_schalter", {"art": "kontroll"}, True),
    ("i_leuchte", {"art": "decke"}, False), ("i_leuchte", {"art": "wand"}, True),
    ("i_leuchte", {"art": "spot"}, False), ("i_leuchte", {"art": "lang"}, False),
    ("i_leuchte", {"art": "strahler"}, False), ("i_leuchte", {"art": "not"}, False),
    ("i_melder", {"text": "RM"}, False), ("i_melder", {"text": "BWM"}, False),
    ("i_dose", {"art": "abzweig"}, False), ("i_dose", {"art": "anschluss"}, False),
    ("i_klingel", {}, True),
]


def main(argv=None):
    a = argv or sys.argv[1:]
    ziel = Path(a[0]) if a else Path(".")
    ziel.mkdir(parents=True, exist_ok=True)
    syms = [cad_symbol(symbol(f, **p), w) for f, p, w in STANDARD]
    c = [befehl("new", metric=True)] + grundbefehle()
    for i, cs in enumerate(syms):
        c += blockdefinition(cs, i)
    # Übersicht: je Block eine Zeile mit Beispielwerten
    for i, cs in enumerate(syms):
        sp, zl = divmod(i, 12)
        x, y = sp * 90.0, -zl * 14.0
        c += [befehl("layer.current", name=cs.layer),
              befehl("insert", name=cs.block, at=[x, y], scale=1,
                     attribs={"SK": "F1", "HOEHE": "h=0,30" if cs.wand else "", "BEM": ""}),
              befehl("layer.current", name="ELT_TEXT"),
              befehl("text", at=[x + 22, y - 2], text=f"{cs.block}", height=1.6),
              befehl("text", at=[x + 22, y - 5], text=cs.name, height=1.4)]
    c += [befehl("layer.current", name="ELT_TEXT"),
          befehl("text", at=[0, 14], text="Symbolbibliothek elektroplan – DIN EN 60617-11 "
                                          "(Blöcke EP_*, Attribute SK / HOEHE / BEM)", height=3),
          befehl("zoom", mode="extents")]
    scr = ziel / "Symbolbibliothek CADCraft.scr"
    scr.write_text("\n".join(c) + "\n", encoding="utf-8")
    dxf = ziel / "Symbolbibliothek CADCraft.dxf"
    cadcraft("run", "--script-file", scr, "--save", dxf,
             "--cmd", befehl("saveas", path=str(dxf.with_suffix(".dwg")), format="dwg"),
             "--export", dxf.with_suffix(".pdf"), "--view", "extents")
    print(f"{len(syms)} Blöcke → {dxf}")


if __name__ == "__main__":
    main()
