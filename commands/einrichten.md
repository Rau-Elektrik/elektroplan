---
description: Firmendaten und Logo für den Skill elektroplan einrichten oder ändern
---

Führe den Einrichtungs-Assistenten des Skills **elektroplan** aus (Abschnitt „0. Einrichtung“ in seiner SKILL.md).

Skript: `${CLAUDE_PLUGIN_ROOT}/skills/elektroplan/scripts/einrichtung.py`
(Falls die Variable oben nicht ersetzt ist: den Basisordner des Skills elektroplan verwenden.)

1. `python -X utf8 <skript> status` ausführen (macOS/Linux: `python3`).
2. Fehlen Python-Pakete, die Installation mit `python -m pip install -r <skill>/requirements.txt` vorschlagen.
3. Ist schon etwas eingerichtet, die aktuellen Daten zeigen und fragen, was geändert werden soll. Sonst alle Angaben gesammelt abfragen: Firmenname (Pflicht), Inhaber, Qualifikation, Straße, PLZ + Ort, Telefon, E-Mail, Webseite, optional Installateurverzeichnis, HWK-Betriebsnummer, Kürzel „Erstellt von“, Akzentfarbe, Ablageordner – und den Pfad zum Logo (PNG/JPG/PDF).
4. Mit `einrichtung.py setzen …` speichern, dann `einrichtung.py test` und das Vorschaubild des Testblatts zeigen.
5. Zum Schluss kurz sagen, wo die Daten liegen (`~/.elektroplan`) und dass sie bei Updates des Plugins erhalten bleiben.

$ARGUMENTS
