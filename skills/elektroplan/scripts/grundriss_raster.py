"""Grundriss (PDF/Bild) mit Meterraster überlagern, um Gerätepositionen abzulesen.

Aufruf:
  python grundriss_raster.py PLAN.pdf --massstab 100 [--seite 1] [--dpi 150] [--ausgabe raster.png]
  python grundriss_raster.py FOTO.jpg --breite-m 10.4 [--ausgabe raster.png]
  Optional: --ausschnitt x0 y0 x1 y1   (Bildpixel, wie später in "grundriss.ausschnitt")
            --schritt 0.5             (Rasterweite in Metern)

Die Rasterkoordinaten (Meter, Ursprung oben links) sind genau die Koordinaten,
die im Installationsplan unter "geraete" (x, y) ohne "raum" verwendet werden,
wenn "grundriss.bild" mit denselben Angaben eingebunden ist.
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def lade_bild(pfad: Path, seite: int, dpi: int):
    if pfad.suffix.lower() == ".pdf":
        import fitz
        with fitz.open(pfad) as doc:
            pix = doc[seite - 1].get_pixmap(dpi=dpi)
            return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return Image.open(pfad).convert("RGB")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("bild", type=Path)
    ap.add_argument("--massstab", type=float, help="Maßstab des PDF-Plans, z. B. 100 für 1:100")
    ap.add_argument("--breite-m", type=float, help="wirkliche Breite des (Ausschnitt-)Bildes in Metern")
    ap.add_argument("--seite", type=int, default=1)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--ausschnitt", type=int, nargs=4)
    ap.add_argument("--schritt", type=float, default=0.5)
    ap.add_argument("--ausgabe", type=Path)
    a = ap.parse_args(argv)

    im = lade_bild(a.bild, a.seite, a.dpi)
    if a.ausschnitt:
        im = im.crop(tuple(a.ausschnitt))
    if a.breite_m:
        m_px = a.breite_m / im.width
    elif a.massstab:
        m_px = (25.4 / a.dpi) * a.massstab / 1000
    else:
        raise SystemExit("--massstab (bei PDF) oder --breite-m angeben")

    # leicht aufhellen, Raster darüber
    im = Image.blend(im, Image.new("RGB", im.size, "white"), 0.35)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", max(10, int(0.12 / m_px)))
    except OSError:
        f = ImageFont.load_default()
    breite_m, hoehe_m = im.width * m_px, im.height * m_px
    n = 0
    while n * a.schritt <= breite_m:
        x = n * a.schritt / m_px
        ganz = abs((n * a.schritt) % 1) < 1e-6
        d.line([(x, 0), (x, im.height)], fill=(220, 40, 40) if ganz else (240, 160, 160),
               width=2 if ganz else 1)
        if ganz:
            # x-Beschriftung bei y = 1, 3, 5 … m, y-Beschriftung bei x = 0, 2, 4 … m
            for yl in range(int(1 / m_px), im.height, int(2 / m_px) or 1):
                d.text((x + 3, yl + 3), f"x={n * a.schritt:g}", fill=(200, 0, 0), font=f)
        n += 1
    n = 0
    while n * a.schritt <= hoehe_m:
        y = n * a.schritt / m_px
        ganz = abs((n * a.schritt) % 1) < 1e-6
        d.line([(0, y), (im.width, y)], fill=(40, 90, 220) if ganz else (160, 180, 240),
               width=2 if ganz else 1)
        if ganz:
            for xl in range(0, im.width, int(2 / m_px) or 1):
                d.text((xl + 3, y + 3), f"y={n * a.schritt:g}", fill=(0, 60, 200), font=f)
        n += 1
    ziel = a.ausgabe or a.bild.with_name(a.bild.stem + "_raster.png")
    im.save(ziel)
    print(f"Raster: {ziel}")
    print(f"Bild: {im.width} × {im.height} px = {breite_m:.2f} × {hoehe_m:.2f} m "
          f"({m_px * 1000:.2f} mm je Pixel)")
    print("Rot = x in Metern (senkrechte Linien), Blau = y in Metern (waagerechte Linien).")


if __name__ == "__main__":
    main()
