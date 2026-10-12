"""Projekt als QElectroTech-Datei (.qet, Format 0.100) schreiben."""
from __future__ import annotations

import base64
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from .model import ORIENT_NUM, Blatt, Bauteil, Leitung, Projekt, Symbol, det_uuid
from .schriftfeld import vorlage_fuer, vorlage_xml

QET_VERSION = "0.100.0"
KATEGORIE = "elektroplan_din_en_60617"


def _n(v) -> str:
    """Zahl ohne überflüssige Nachkommastellen."""
    if isinstance(v, float):
        v = round(v, 3)
        if v == int(v):
            return str(int(v))
        return f"{v:g}"
    return str(v)


def _schrift(pt: float, fett: bool = False) -> str:
    gewicht, stil = (75, "Bold") if fett else (50, "Regular")
    return f"Arial,{_n(float(pt))},-1,5,{gewicht},0,0,0,0,0,{stil}"


def _typ(s: Symbol) -> str:
    return f"embed://import/{KATEGORIE}/{_dateiname(s)}"


def _dateiname(s: Symbol) -> str:
    sauber = "".join(c if c.isalnum() or c in "_-" else "_" for c in s.key)
    return f"{sauber}.elmt"


# --------------------------------------------------------------------------
# Symboldefinition
# --------------------------------------------------------------------------
def symbol_xml(s: Symbol) -> ET.Element:
    x0, y0, x1, y1 = s.grenzen()
    gx0 = math.floor(x0 / 10) * 10
    gy0 = math.floor(y0 / 10) * 10
    gx1 = max(math.ceil(x1 / 10) * 10, gx0 + 10)
    gy1 = max(math.ceil(y1 / 10) * 10, gy0 + 10)
    d = ET.Element("definition", version=QET_VERSION, type="element", link_type="simple",
                   width=_n(gx1 - gx0), height=_n(gy1 - gy0), hotspot_x=_n(-gx0),
                   hotspot_y=_n(-gy0))
    ET.SubElement(d, "uuid", uuid=s.uuid)
    names = ET.SubElement(d, "names")
    ET.SubElement(names, "name", lang="de").text = s.name
    ET.SubElement(names, "name", lang="en").text = s.name
    ET.SubElement(d, "informations").text = (
        "Symbolsatz nach DIN EN 60617 (Skill elektroplan)")
    desc = ET.SubElement(d, "description")
    for p in s.prims:
        a = p.attrs
        if p.tag == "text":
            ET.SubElement(desc, "text", x=_n(float(a["x"])), y=_n(float(a["y"])), text=a["text"],
                          rotation="0", font=_schrift(a["pt"]), color="#000000")
        else:
            ET.SubElement(desc, p.tag, {k: _n(v) if isinstance(v, (int, float)) else v
                                        for k, v in a.items()})
    for i, t in enumerate(s.texte):
        dt = ET.SubElement(desc, "dynamic_text", x=_n(float(t.x)), y=_n(float(t.y)), z=str(10 + i),
                           text_width="-1", Halignment="AlignLeft", Valignment="AlignTop",
                           frame="false", rotation=_n(float(t.rot)), keep_visual_rotation="true",
                           text_from="ElementInfo", uuid=det_uuid("dyn", s.key, i),
                           font=_schrift(t.pt, t.fett))
        ET.SubElement(dt, "text")
        ET.SubElement(dt, "info_name").text = t.info
    for a in s.anschluesse:
        ET.SubElement(desc, "terminal", uuid=s.anschluss_uuid(a.name), name=a.name,
                      x=_n(float(a.x)), y=_n(float(a.y)), orientation=a.ori, type="Generic")
    return d


# --------------------------------------------------------------------------
# Blattinhalt
# --------------------------------------------------------------------------
_ANDOCK = {"n": (0, 4), "s": (0, -4), "e": (-4, 0), "w": (4, 0)}


def _bauteil_xml(b: Bauteil, zaehler: list[int]) -> ET.Element:
    s = b.symbol
    e = ET.Element("element", type=_typ(s), uuid=b.uid, prefix="", freezeLabel="false",
                   x=_n(float(b.x)), y=_n(float(b.y)), z="10", orientation=str(b.ori))
    terms = ET.SubElement(e, "terminals")
    for a in s.anschluesse:
        dx, dy = _ANDOCK[a.ori]
        ET.SubElement(terms, "terminal", id=str(zaehler[0]), x=_n(float(a.x + dx)),
                      y=_n(float(a.y + dy)), orientation=str(ORIENT_NUM[a.ori]))
        zaehler[0] += 1
    ET.SubElement(e, "inputs")
    infos = {k: v for k, v in b.info.items() if str(v).strip()}
    if infos:
        ei = ET.SubElement(e, "elementInformations")
        for k, v in infos.items():
            ET.SubElement(ei, "elementInformation", name=k, show="1").text = str(v)
    dts = ET.SubElement(e, "dynamic_texts")
    for i, t in enumerate(b.dyn_texte()):
        dt = ET.SubElement(dts, "dynamic_elmt_text", x=_n(float(t.x)), y=_n(float(t.y)),
                           rotation=_n(float(t.rot)), uuid=det_uuid("dyntext", b.uid, i),
                           font=_schrift(t.pt, t.fett), Halignment="AlignLeft",
                           Valignment="AlignTop", text_from="ElementInfo", text_width="-1",
                           frame="false", keep_visual_rotation="true")
        ET.SubElement(dt, "text").text = str(b.info.get(t.info, ""))
        ET.SubElement(dt, "info_name").text = t.info
    ET.SubElement(e, "texts_groups")
    return e


def _leitung_xml(l: Leitung, i: int, blatt_nr: int) -> ET.Element:
    stil = {"SolidLine": "normal", "DashLine": "dashed", "DotLine": "dashed"}.get(l.stil, "normal")
    attrs = dict(uuid=det_uuid("leitung", blatt_nr, i, l.a.uid, l.ta, l.b.uid, l.tb), x="0", y="0",
                 element1=l.a.uid, element1_label=str(l.a.info.get("label", "")),
                 element1_name=l.a.symbol.name, terminal1=l.a.symbol.anschluss_uuid(l.ta),
                 terminalname1=l.ta,
                 element2=l.b.uid, element2_label=str(l.b.info.get("label", "")),
                 element2_name=l.b.symbol.name, terminal2=l.b.symbol.anschluss_uuid(l.tb),
                 terminalname2=l.tb, freezeLabel="false",
                 type="single" if l.markiert else "multi", num=l.nummer,
                 displaytext="1" if l.nummer else "0", color=l.farbe, bicolor="false",
                 color2="#000000", **{"dash-size": "1"}, style=f"line-style: {stil}",
                 condsize=_n(float(l.breite)), numsize="7", text_color="#000000",
                 onetextperfolio="0", vertirotatetext="270", horizrotatetext="0",
                 formula="", cable="", bus="", function="", tension_protocol="",
                 conductor_color="", conductor_section="")
    if l.markiert:
        attrs.update(phase=str(l.phasen), neutral="true" if l.neutral else "false",
                     ground="true" if l.schutz else "false")
    c = ET.Element("conductor", attrs)
    for (x1, y1), (x2, y2) in zip(l.punkte, l.punkte[1:]):
        if y1 == y2:
            ET.SubElement(c, "segment", orientation="horizontal", length=_n(float(x2 - x1)))
        else:
            ET.SubElement(c, "segment", orientation="vertical", length=_n(float(y2 - y1)))
    ET.SubElement(c, "sequentialNumbers")
    return c


def _html(text: str) -> str:
    from html import escape
    return "<br/>".join(escape(z) for z in text.split("\n"))


def _blatt_xml(bl: Blatt, nr: int) -> ET.Element:
    fmt = bl.format
    f = bl.felder
    d = ET.Element("diagram", dict(
        uuid=det_uuid("blatt", nr, bl.titel), title=bl.titel, author=f.get("bearbeiter", ""),
        date=f.get("datum_iso", "null"), folio="%id/%total", plant=f.get("anlage", ""),
        locmach=f.get("ort", ""), indexrev=f.get("indexrev", ""), version=QET_VERSION, filename="",
        auto_page_num="", displayAt="bottom", titleblocktemplate=fmt.vorlage,
        titleblocktemplateCollection="embedded", cols=str(fmt.cols), colsize=str(fmt.colsize),
        rows=str(fmt.rows), rowsize=str(fmt.rowsize), height=str(fmt.rows * fmt.rowsize),
        displaycols="true" if bl.raster_anzeigen else "false",
        displayrows="true" if bl.raster_anzeigen else "false",
        order=str(nr), freezeNewElement="false", freezeNewConductor="false"))
    props = ET.SubElement(d, "properties")
    for k, v in f.items():
        if k in ("datum_iso",):
            continue
        ET.SubElement(props, "property", name=k, show="1").text = str(v)
    ET.SubElement(d, "defaultconductor", type="multi", num="", displaytext="0", condsize="1",
                  color="#000000", numsize="7")
    els = ET.SubElement(d, "elements")
    zaehler = [0]
    for b in bl.bauteile:
        els.append(_bauteil_xml(b, zaehler))
    cons = ET.SubElement(d, "conductors")
    for i, l in enumerate(bl.leitungen):
        cons.append(_leitung_xml(l, i, nr))
    inputs = ET.SubElement(d, "inputs")
    for i, t in enumerate(bl.texte):
        ET.SubElement(inputs, "input", uuid=det_uuid("text", nr, i), x=_n(float(t.x)),
                      y=_n(float(t.y)), text=_html(t.text), rotation=_n(float(t.rot % 360)),
                      font=_schrift(t.pt, t.fett))
    imgs = ET.SubElement(d, "images")
    for i, b in enumerate(bl.bilder):
        im = ET.SubElement(imgs, "image", uuid=det_uuid("bild", nr, i), x=_n(float(b.x)),
                           y=_n(float(b.y)), z="1", rotation="0", size=_n(float(b.skala)),
                           is_movable="1")
        im.text = base64.b64encode(b.png).decode("ascii")
        ET.SubElement(im, "transform", rotation="0", skewX="0", skewY="0",
                      scaleX=_n(float(b.skala)), scaleY=_n(float(b.skala)), pivotX="0", pivotY="0")
    shapes = ET.SubElement(d, "shapes")
    for i, fo in enumerate(bl.formen):
        attrs = dict(uuid=det_uuid("form", nr, i), type=fo.art, is_movable="1",
                     closed="1" if fo.geschlossen else "0", z="5")
        if fo.art != "Polygon":
            (x1, y1), (x2, y2) = fo.punkte
            attrs.update(x1=_n(float(x1)), y1=_n(float(y1)), x2=_n(float(x2)), y2=_n(float(y2)))
            if fo.art == "Rectangle":
                attrs.update(rx="0", ry="0")
        sh = ET.SubElement(shapes, "shape", attrs)
        ET.SubElement(sh, "pen", style=fo.stil, color=fo.farbe, widthF=_n(float(fo.breite)))
        ET.SubElement(sh, "brush", style="SolidPattern" if fo.fuellung else "NoBrush",
                      color=fo.fuellung or "#000000")
        if fo.art == "Polygon":
            pts = ET.SubElement(sh, "points")
            for x, y in fo.punkte:
                ET.SubElement(pts, "point", x=_n(float(x)), y=_n(float(y)))
    return d


def schreibe_qet(projekt: Projekt, pfad: Path) -> None:
    root = ET.Element("project", title=projekt.titel, version=QET_VERSION,
                      uuid=det_uuid("projekt", projekt.titel))
    # Schriftfeld-Vorlagen
    tbs = ET.SubElement(root, "titleblocktemplates")
    for vname in sorted({bl.format.key for bl in projekt.blaetter}):
        fmt = next(bl.format for bl in projekt.blaetter if bl.format.key == vname)
        tbs.append(vorlage_xml(vorlage_fuer(fmt)))
    ET.SubElement(root, "properties")
    # Texte in gedrehten Symbolen waagerecht halten (wie im PDF)
    ET.SubElement(root, "symbol_texts", upright="true")
    nd = ET.SubElement(root, "newdiagrams")
    f0 = projekt.blaetter[0].format
    ET.SubElement(nd, "border", cols=str(f0.cols), colsize=str(f0.colsize), rows=str(f0.rows),
                  rowsize=str(f0.rowsize), displaycols="true", displayrows="true")
    ET.SubElement(nd, "inset", titleblocktemplate=f0.vorlage, titleblocktemplateCollection="embedded",
                  folio="%id/%total", displayAt="bottom", date="null", title="", author="",
                  plant="", locmach="", indexrev="", version="", filename="", auto_page_num="")
    ET.SubElement(nd, "conductors", type="multi", num="", displaytext="0", condsize="1",
                  color="#000000", numsize="7")
    for i, bl in enumerate(projekt.blaetter, 1):
        root.append(_blatt_xml(bl, i))
    # eingebettete Symbole
    col = ET.SubElement(root, "collection")
    imp = ET.SubElement(col, "category", name="import")
    nm = ET.SubElement(imp, "names")
    ET.SubElement(nm, "name", lang="de").text = "Importierte Elemente"
    ET.SubElement(nm, "name", lang="en").text = "Imported elements"
    kat = ET.SubElement(imp, "category", name=KATEGORIE)
    nm = ET.SubElement(kat, "names")
    ET.SubElement(nm, "name", lang="de").text = "Elektroplan (DIN EN 60617)"
    ET.SubElement(nm, "name", lang="en").text = "Elektroplan (EN 60617)"
    symbole = {}
    for bl in projekt.blaetter:
        for b in bl.bauteile:
            symbole[b.symbol.key] = b.symbol
    for s in sorted(symbole.values(), key=lambda s: s.key):
        el = ET.SubElement(kat, "element", name=_dateiname(s))
        el.append(symbol_xml(s))
    ET.indent(root, space="    ")
    pfad.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=False))
