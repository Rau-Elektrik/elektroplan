"""Firmen-Stammdaten des Nutzers (Schriftfeld, Logo, Bearbeiter, Ablage).

Die Daten liegen bewusst NICHT im Skill-Ordner, sondern im Konfigurationsordner
  ~/.elektroplan/            (Windows: C:\\Users\\<Name>\\.elektroplan\\)
oder in dem Ordner, auf den die Umgebungsvariable ELEKTROPLAN_HOME zeigt.
So überschreibt ein Update des Skills nie die eigenen Firmendaten, und im
öffentlichen Repository stehen keine Firmendaten.

  firma.json                  Stammdaten (siehe FELDER)
  logo.png                    Firmenlogo für Schriftfeld und Excel-Vorlage
  vorlagen/…xltx              eigene Excel-Vorlage Stromkreisliste (wird erzeugt)

Ausnahme: Ein mit „einrichtung.py paket“ gebautes persönliches ZIP (für claude.ai, wo es kein
Home-Verzeichnis gibt) enthält die Daten im Unterordner firma/ des Skills.

Eingerichtet wird mit scripts/einrichtung.py.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

# Feld → (Beschriftung, Pflicht, Beispiel)
FELDER: dict[str, tuple[str, bool, str]] = {
    "name": ("Firmenname", True, "Muster Elektrotechnik GmbH"),
    "inhaber": ("Inhaber / Ansprechpartner", False, "Max Mustermann"),
    "titel": ("Qualifikation", False, "Elektrotechnikermeister"),
    "strasse": ("Straße und Hausnummer", False, "Musterstraße 1"),
    "ort": ("PLZ und Ort", False, "12345 Musterstadt"),
    "telefon": ("Telefon", False, "0123 456789"),
    "mail": ("E-Mail", False, "info@muster-elektro.de"),
    "web": ("Webseite", False, "muster-elektro.de"),
    "installateurverzeichnis": ("Eintrag Installateurverzeichnis (Netzbetreiber, Nr.)", False,
                                "Muster Netz GmbH, Nr. 12345"),
    "hwk_nr": ("Handwerkskammer-Betriebsnummer", False, "1234567"),
    "bearbeiter": ("Kürzel „Erstellt von“ im Schriftfeld", False, "M. Mustermann"),
    "akzentfarbe": ("Akzentfarbe der Excel-Vorlage (Hex)", False, "#1F5FAD"),
    "ablage": ("Standard-Ablageordner für Pläne", False, "~/Documents/Kunden/<Kunde>/Planung"),
}

PLATZHALTER_NAME = "Firma nicht eingerichtet"


SKILL_FIRMA = Path(__file__).resolve().parents[2] / "firma"   # nur im persönlichen Paket (einrichtung.py paket)


def konfig_ordner() -> Path:
    """ELEKTROPLAN_HOME → ~/.elektroplan → <Skill>/firma (persönliches Paket, z. B. für claude.ai)."""
    if os.environ.get("ELEKTROPLAN_HOME"):
        return Path(os.environ["ELEKTROPLAN_HOME"]).expanduser()
    heim = Path.home() / ".elektroplan"
    if not (heim / "firma.json").exists() and (SKILL_FIRMA / "firma.json").exists():
        return SKILL_FIRMA
    return heim


def konfig_datei() -> Path:
    return konfig_ordner() / "firma.json"


def vorlagen_ordner() -> Path:
    return konfig_ordner() / "vorlagen"


@lru_cache(maxsize=1)
def lade() -> dict:
    """Stammdaten lesen. Ohne Einrichtung kommt ein Platzhalter zurück (eingerichtet = False)."""
    pfad = konfig_datei()
    if pfad.exists():
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        daten["_eingerichtet"] = bool(str(daten.get("name") or "").strip())
        return daten
    return {"name": PLATZHALTER_NAME, "_eingerichtet": False}


def eingerichtet() -> bool:
    return bool(lade().get("_eingerichtet"))


def speichere(daten: dict) -> Path:
    pfad = konfig_datei()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    sauber = {k: v for k, v in daten.items() if not k.startswith("_") and v not in (None, "")}
    sauber.setdefault("version", 1)
    pfad.write_text(json.dumps(sauber, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lade.cache_clear()
    return pfad


def logo_pfad() -> Path | None:
    name = lade().get("logo") or "logo.png"
    p = Path(name).expanduser()
    if not p.is_absolute():
        p = konfig_ordner() / p
    return p if p.exists() else None


def bearbeiter() -> str:
    d = lade()
    if d.get("bearbeiter"):
        return d["bearbeiter"]
    inhaber = str(d.get("inhaber") or "").split()
    if len(inhaber) >= 2:                          # „Max Mustermann“ → „M. Mustermann“
        return f"{inhaber[0][0]}. {' '.join(inhaber[1:])}"
    return " ".join(inhaber)


def wert(feld: str) -> str:
    return str(lade().get(feld) or "").strip()


def stromkreisliste_vorlage() -> Path | None:
    """Eigene Excel-Vorlage: Umgebungsvariable EP_VORLAGE_STROMKREISLISTE, Eintrag
    „vorlage_stromkreisliste“ in firma.json oder die bei der Einrichtung erzeugte Datei."""
    from .excel_vorlage import VORLAGE_NAME
    kandidaten = [os.environ.get("EP_VORLAGE_STROMKREISLISTE"), lade().get("vorlage_stromkreisliste"),
                  str(vorlagen_ordner() / VORLAGE_NAME)]
    for k in kandidaten:
        if k and Path(k).expanduser().exists():
            return Path(k).expanduser()
    return None
