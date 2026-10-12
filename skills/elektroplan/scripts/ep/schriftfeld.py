"""Schriftfeld mit Firmendaten und Logo – als QElectroTech-Vorlage und für das PDF.

Die Firmendaten kommen aus der eigenen Konfiguration (ep/firma.py, ~/.elektroplan/firma.json),
nicht aus dem Code. Einrichten mit scripts/einrichtung.py.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from .blatt import SCHRIFTFELD_H, Format

from . import firma as _firma


@dataclass
class Zelle:
    zeile: int
    spalte: int
    wert: str = ""            # Text mit Variablen (%title, %kunde …)
    pt: float = 7.0
    h: str = "left"           # left / center / right
    v: str = "center"         # top / center / bottom
    zeilen: int = 1           # rowspan
    spalten: int = 1          # colspan
    logo: bool = False


@dataclass
class Vorlage:
    name: str
    breiten: list[float]
    hoehen: list[float]
    zellen: list[Zelle]

    def rechteck(self, z: Zelle) -> tuple[float, float, float, float]:
        x = sum(self.breiten[: z.spalte])
        y = sum(self.hoehen[: z.zeile])
        w = sum(self.breiten[z.spalte: z.spalte + z.spalten])
        h = sum(self.hoehen[z.zeile: z.zeile + z.zeilen])
        return x, y, w, h

    def logo_zelle(self) -> Zelle | None:
        return next((z for z in self.zellen if z.logo), None)


def _verbinde(*teile) -> str:
    return " · ".join(str(x).strip() for x in teile if x and str(x).strip())


def _firmenzeilen() -> list[str]:
    w = _firma.wert
    tel = f"Tel. {w('telefon')}" if w("telefon") else ""
    zeilen = [w("name") or _firma.PLATZHALTER_NAME, _verbinde(w("inhaber"), w("strasse")), w("ort"),
              _verbinde(tel, w("web") or w("mail"))]
    return zeilen


def vorlage_fuer(fmt: Format) -> Vorlage:
    gesamt = fmt.rahmen[2]
    zeilen_h = [SCHRIFTFELD_H / 4] * 4
    if fmt.key == "A4H":
        breiten = [120, 0, 55, 185, 60]
        breiten[1] = gesamt - sum(breiten)
        c_logo, c_titel, c_lab, c_wert, c_blatt = 0, 1, 2, 3, 4
        w = _firma.wert
        zellen = [_logo_zelle(c_logo),
                  Zelle(0, c_titel, "%title", 11, "center", zeilen=2),
                  Zelle(2, c_titel, "%anlage", 7, "center"),
                  Zelle(3, c_titel, _verbinde(w("name") or _firma.PLATZHALTER_NAME, w("inhaber"), w("strasse"),
                                              w("ort"), f"Tel. {w('telefon')}" if w("telefon") else ""),
                        5, "center")]
    else:
        if fmt.key == "A3Q":
            breiten = [170, 250, 0, 70, 330, 80]
        else:
            breiten = [130, 200, 0, 60, 230, 70]
        breiten[2] = gesamt - sum(breiten)
        c_logo, c_firma, c_titel, c_lab, c_wert, c_blatt = 0, 1, 2, 3, 4, 5
        fz = _firmenzeilen()
        zellen = [_logo_zelle(c_logo),
                  Zelle(0, c_firma, fz[0], 8), Zelle(1, c_firma, fz[1], 6),
                  Zelle(2, c_firma, fz[2], 6), Zelle(3, c_firma, fz[3], 6),
                  Zelle(0, c_titel, "%title", 12 if fmt.key == "A3Q" else 11, "center", zeilen=2),
                  Zelle(2, c_titel, "%anlage", 8 if fmt.key == "A3Q" else 7, "center"),
                  Zelle(3, c_titel, "%plantyp", 6, "center")]
    for i, (lab, wert) in enumerate([("Kunde", "%kunde"), ("Objekt", "%objekt"),
                                     ("Auftrag", "%auftrag"), ("Erstellt", "%datum · %bearbeiter")]):
        zellen.append(Zelle(i, c_lab, lab, 6))
        zellen.append(Zelle(i, c_wert, wert, 7))
    zellen += [Zelle(0, c_blatt, "Blatt", 6, "center"),
               Zelle(1, c_blatt, "%folio", 11, "center", zeilen=2),
               Zelle(3, c_blatt, "Rev. %indexrev", 6, "center")]
    return Vorlage(fmt.vorlage, [float(b) for b in breiten], zeilen_h, zellen)


def _logo_zelle(spalte: int) -> Zelle:
    """Logo-Zelle; ohne eingerichtetes Logo steht dort der Firmenname."""
    if _firma.logo_pfad():
        return Zelle(0, spalte, zeilen=4, logo=True)
    return Zelle(0, spalte, _firma.wert("name") or _firma.PLATZHALTER_NAME, 8, "center", zeilen=4)


def logo_png(breite_px: float, hoehe_px: float, aufloesung: int = 4) -> bytes:
    """Logo im exakten Seitenverhältnis der Zelle (QElectroTech streckt Bilder auf die Zelle)."""
    from PIL import Image
    W, H = int(breite_px * aufloesung), int(hoehe_px * aufloesung)
    leinwand = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    logo = Image.open(_firma.logo_pfad()).convert("RGBA")
    rand = 0.12
    maxw, maxh = W * (1 - 2 * rand), H * (1 - 2 * rand)
    f = min(maxw / logo.width, maxh / logo.height)
    logo = logo.resize((max(1, int(logo.width * f)), max(1, int(logo.height * f))), Image.LANCZOS)
    leinwand.alpha_composite(logo, ((W - logo.width) // 2, (H - logo.height) // 2))
    buf = io.BytesIO()
    leinwand.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Ausgabe als QElectroTech-Vorlage
# --------------------------------------------------------------------------
def vorlage_xml(v: Vorlage):
    import xml.etree.ElementTree as ET
    root = ET.Element("titleblocktemplate", name=v.name)
    ET.SubElement(root, "information").text = f"Schriftfeld {_firma.wert('name')} – erzeugt vom Skill elektroplan"
    logos = ET.SubElement(root, "logos")
    lz = v.logo_zelle()
    if lz:
        x, y, w, h = v.rechteck(lz)
        lo = ET.SubElement(logos, "logo", name="firmenlogo.png", type="png", storage="base64")
        lo.text = base64.b64encode(logo_png(w, h)).decode("ascii")
    grid = ET.SubElement(root, "grid",
                         cols="".join(f"{b:g};" for b in v.breiten),
                         rows="".join(f"{h:g};" for h in v.hoehen))
    belegt = set()
    for z in v.zellen:
        for r in range(z.zeile, z.zeile + z.zeilen):
            for c in range(z.spalte, z.spalte + z.spalten):
                belegt.add((r, c))
        attrs = dict(row=str(z.zeile), col=str(z.spalte), name="")
        if z.zeilen > 1:
            attrs["rowspan"] = str(z.zeilen)
        if z.spalten > 1:
            attrs["colspan"] = str(z.spalten)
        if z.logo:
            attrs["resource"] = "firmenlogo.png"
            ET.SubElement(grid, "logo", attrs)
            continue
        attrs.update(fontsize=f"{z.pt:g}", align=z.h, valign=z.v, hadjust="true",
                     displaylabel="false")
        f = ET.SubElement(grid, "field", attrs)
        val = ET.SubElement(f, "value")
        ET.SubElement(val, "translation", lang="de").text = z.wert
        ET.SubElement(val, "translation", lang="en").text = z.wert
        ET.SubElement(f, "label")
    # leere Zellen explizit anlegen, sonst rahmt QElectroTech sie nicht
    for r in range(len(v.hoehen)):
        for c in range(len(v.breiten)):
            if (r, c) not in belegt:
                f = ET.SubElement(grid, "field", row=str(r), col=str(c), name="", fontsize="7",
                                  align="left", valign="center", hadjust="true", displaylabel="false")
                ET.SubElement(f, "value")
                ET.SubElement(f, "label")
    return root
