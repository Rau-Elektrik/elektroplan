---
name: elektroplan
description: "Elektropläne nach DIN EN 60617 als QElectroTech-Datei (.qet) plus PDF mit eigenem Firmenschriftfeld und Logo – Verteilerplan einpolig und Stromlaufplan der Verteilung allpolig (Klemmleiste X1, Hauptschalter, Schienen, FI, LS, Abgangsklemmen), beides auch aus der Excel-Stromkreisliste; Stromlaufplan von Installationsschaltungen (Wechsel-, Kreuz-, Stromstoßschaltung, Wendeschütz …); Installationsplan (Grundriss mit Symbolen, Legende mit Stückzahlen). Verwenden bei Schaltplan, Verteilerplan, Stromlaufplan, Übersichtsschaltplan, Installationsplan, Elektroplan, Verteilerdokumentation, Stromkreisliste, QElectroTech – und zum Einrichten oder Ändern der Firmendaten/des Logos für diese Pläne."
---

# Elektroplan (Verteilerplan · Stromlaufplan · Installationsplan)

Erzeugt aus einer JSON-Beschreibung (oder der Excel-Stromkreisliste):
- **`.qet`**: Projekt für QElectroTech (ab 0.100), voll bearbeitbar. Symbole eingebettet unter „Importierte Elemente › Elektroplan (DIN EN 60617)“, Schriftfeld als eingebettete Vorlage `elektroplan_a3q` / `_a4q` / `_a4h`.
- **`.pdf`**: druckfertig, 1 px = 0,25 mm (Maßstäbe stimmen bei Druck in Originalgröße), Schriftfeld mit Logo und Firmendaten des Nutzers.
- **Vorschau-PNG** je Blatt zur Sichtkontrolle.

`<SKILL>` = Ordner dieses Skills (wird beim Laden als Basisverzeichnis angezeigt). Python-Aufruf: Windows `python -X utf8`, macOS/Linux `python3`. Pakete: reportlab, PyMuPDF, Pillow, openpyxl (`<SKILL>/requirements.txt`).

## 0. Einrichtung (immer zuerst prüfen)

Die Firmendaten gehören dem Nutzer und liegen **nicht** im Skill, sondern in `~/.elektroplan/` (oder `ELEKTROPLAN_HOME`). Vor dem ersten Plan in jeder Sitzung:

```
python -X utf8 <SKILL>/scripts/einrichtung.py status
```

- `pakete_fehlen` nicht leer → dem Nutzer den Befehl `python -m pip install -r <SKILL>/requirements.txt` vorschlagen und nach Bestätigung ausführen.
- `"eingerichtet": false` → **Einrichtungs-Assistent** durchführen, bevor ein Plan gezeichnet wird:
  1. Kurz begrüßen und erklären: Die Angaben erscheinen im Schriftfeld jedes Plans und in der Excel-Stromkreisliste; sie bleiben lokal auf diesem Rechner.
  2. Abfragen (gesammelt in einer Nachricht, nicht einzeln): **Firmenname** (Pflicht), Inhaber/Ansprechpartner, Qualifikation (z. B. Elektrotechnikermeister), Straße, PLZ + Ort, Telefon, E-Mail, Webseite. Optional: Eintrag Installateurverzeichnis (Netzbetreiber + Nr.), Handwerkskammer-Betriebsnummer, Kürzel für „Erstellt von“, Akzentfarbe (Hex), Standard-Ablageordner für Pläne.
  3. **Logo**: Pfad zu einer PNG/JPG/PDF-Datei erfragen (SVG vorher als PNG exportieren lassen). Ohne Logo steht der Firmenname im Logo-Feld.
  4. Speichern (nur angegebene Felder):
     ```
     python -X utf8 <SKILL>/scripts/einrichtung.py setzen --name "…" --inhaber "…" --titel "…" --strasse "…" --ort "…" --telefon "…" --mail "…" --web "…" [--installateurverzeichnis "…" --hwk-nr "…" --bearbeiter "…" --akzentfarbe "#…" --ablage "…"] --logo "<pfad>"
     ```
     Das erzeugt auch die eigene Excel-Vorlage „Verteilerdokumentation Stromkreisliste Messprotokoll.xltx“ in `~/.elektroplan/vorlagen/`.
  5. Testblatt erzeugen und das Vorschau-PNG ansehen bzw. zeigen: `python -X utf8 <SKILL>/scripts/einrichtung.py test`. Passt das Logo nicht (zu klein, Rand), ein anderes Logo erfragen.
- Ändern später: „Firmendaten ändern“ → `einrichtung.py setzen` nur mit den geänderten Feldern; neues Logo → `einrichtung.py logo <pfad>`.
- Niemals Firmendaten in Dateien des Skill-Ordners schreiben.

## 1. Planart und Daten klären (nur fragen, was fehlt)

- *Verteilerplan / Stromlaufplan der Verteilung*: Gibt es schon eine ausgefüllte Stromkreisliste (`…Verteilerdokumentation….xlsx`)? Dann direkt die Excel-Datei verwenden. Sonst Schutzorgane wie in der Stromkreisliste erfassen: BMK, Art, Char., In, Pole, vorgeschalteter FI, Leitung, Adern×mm², Länge, Raum, Verbraucher.
  „Stromlaufplan“ für eine Verteilung meint in der Praxis meist den **allpoligen Stromlaufplan der Verteilung** (`--darstellung allpolig`). Den Baustein-Stromlaufplan (Wechsel-, Kreuzschaltung …) nur, wenn ausdrücklich Installationsschaltungen gewünscht sind. Im Zweifel kurz nachfragen.
- *Stromlaufplan*: welche Schaltungen (Typen siehe Referenz, auch Wendeschützschaltung `wendeschuetz`), LS und Phase, Anzahl Schalter/Taster/Leuchten, Orte der Schalter.
- *Installationsplan*: Raummaße aus dem Aufmaß (Innenmaße, Wanddicken, Türen, Fenster) **oder** Grundriss vom Architekten (PDF/Bild + Maßstab bzw. eine bekannte Breite). Dazu je Gerät Raum, Position, Wand, Stromkreis, Höhe.
  Nennt der Nutzer nur Räume, aber keine Geräte: zuerst eine **Ausstattung nach DIN 18015-2 vorschlagen** (`referenz/ausstattung_din18015.md`, Zahlen in `ausstattung_din18015.json`) und bestätigen lassen, erst dann zeichnen. Solange die Tabelle `"geprueft": false` hat, den Vorschlag als „Tabelle noch nicht mit Normtext abgeglichen“ kennzeichnen.
- Kopfdaten: Kunde, Objekt, Auftrags-Nr., Datum, Revision. `bearbeiter` weglassen = Kürzel aus der Einrichtung.

## 2. Plan-JSON schreiben

Format in `referenz/plan_format.md`, Beispiele in `referenz/beispiele/`. Die JSON-Datei zusammen mit dem Plan ablegen; sie ist die Quelle für spätere Änderungen.

## 3. Erzeugen

```
python -X utf8 <SKILL>/scripts/elektroplan.py PLAN.json --ziel "<Ordner>" --vorschau "<Temp-Ordner>"
python -X utf8 <SKILL>/scripts/elektroplan.py "<Stromkreisliste>.xlsx" --ziel "<Ordner>" --name "<Dateiname>"
```
Optionen: `--format "A3 quer" | "A4 quer" | "A4 hoch"`, `--name`, `--keine-vorschau`,
`--darstellung einpolig | allpolig | beide` (nur Verteilung; „beide“ = Übersichtsschaltplan + allpoliger Stromlaufplan in einer Datei),
`--stromkreisliste` (nur Verteilung: füllt die eigene Excel-Vorlage aus der Einrichtung mit Anlage- und Stromkreisdaten → `<Name> Stromkreisliste.xlsx`).
Allpolig: BMK mit Minus (-F1, -X1). Phasen ohne Angabe werden reihum verteilt und als `HINWEIS (Annahme)` gemeldet – Zuordnung bestätigen lassen.

## 4. Prüfen

Vorschau-PNG ansehen (unter Windows kurzen Vorschauordner wählen, z. B. `%TEMP%\ep_vorschau` – Pfade über 260 Zeichen scheitern). Die Ausgabe meldet:
- `HINWEIS (Einrichtung)`: keine Firmendaten → Schritt 0 nachholen.
- `HINWEIS (Layout)`: überlappende Texte oder Inhalt außerhalb des Rahmens. Durch Ändern der JSON beheben (andere Position, kürzerer Text, anderes Format).
- `HINWEIS (fachlich)`: nur Verteilung (FI-Pflicht, Querschnitt zu Nennstrom, Polzahl zu Aderzahl, Anzahl Stromkreise je FI). Nichts eigenmächtig ändern, sondern dem Nutzer nennen. Die Bemessung bleibt Sache der Elektrofachkraft.
- `HINWEIS (Norm)`: Spannungsfall je Stromkreis (> 3 %, DIN 18015-1 / VDE 0100-520), Stromkreisanzahl zur `wohnflaeche` und Ausstattung je Raum (DIN 18015-2), Montagehöhen und Schalter neben Türen (DIN 18015-3), Steckdosen/Schalter in Bereich 1/2 von Dusche/Wanne (VDE 0100-701, wenn `sanitaer` angegeben). Ebenfalls nur Hinweise.

## 5. Ablage und Übergabe

Ablage: der Ordner, den der Nutzer nennt, sonst `ablage` aus der Einrichtung (`<Kunde>` ersetzen), sonst nachfragen. Dateiname `JJJJ-MM-TT <Planart> <Bezeichnung>` (z. B. `2026-10-08 Verteilerplan UV Wohnung OG`). PDF, `.qet` und JSON nennen.
Öffnen in QElectroTech: Pfad aus `einrichtung.py status` (`qelectrotech`). Unter Windows zuverlässig:
```
& "C:\Program Files\QElectroTech\bin\qelectrotech.exe" -platform windows:fontengine=freetype --common-elements-dir=elements/ --common-tbt-dir=titleblocks/ --lang-dir=lang/ "<pfad.qet>"
```
(Arbeitsverzeichnis `C:\Program Files\QElectroTech`. Eine laufende Instanz übernimmt keine weitere Datei, dann über Datei › Öffnen.)

## Wichtig

- **Neu erzeugen überschreibt die `.qet`.** Wurde die Datei in QElectroTech von Hand bearbeitet: nicht überschreiben, sondern mit neuem Namen oder neuer Revision erzeugen und vorher fragen.
- Die Pläne sind ein Werkzeug für Elektrofachkräfte. Normhinweise ersetzen keine Bemessung und Prüfung nach VDE.
- BMK im Verteilerplan ohne Bindestrich (`F1`, `Q1`, `K1`), fortlaufend in Verteilerreihenfolge; FI und LS teilen sich die F-Nummern (wie in der Stromkreisliste).
- Fachliche Grundlagen und Konventionen: `referenz/fachliches.md`.
- Grundriss vom Architekten: zuerst Raster erzeugen und Positionen ablesen:
  ```
  python -X utf8 <SKILL>/scripts/grundriss_raster.py PLAN.pdf --massstab 100 --dpi 150 [--ausschnitt x0 y0 x1 y1] --ausgabe raster.png
  ```
  Dieselben Werte (`massstab`, `dpi`, `ausschnitt`) in `grundriss` der JSON übernehmen. Die Koordinaten aus dem Raster (Meter, Ursprung oben links) gelten direkt für `geraete`; ohne Räume `wand` je Gerät angeben.
- Mehrere Pläne für denselben Kunden: je Plan eine JSON und eine PDF; bei Bedarf die PDFs zu einer Mappe zusammenfügen.
- Symbole fehlen? Neue Symbolfabrik in `scripts/ep/symbole.py` ergänzen (gleicher Stil: Raster 10 px, Anschlüsse `1` oben bei y=-30 und `2` unten bei y=+30) und mit einem Testblatt prüfen. Übersicht aller Symbole: `scripts/symbolkatalog.py`.

## Dateien

| Datei | Zweck |
|---|---|
| `scripts/einrichtung.py` | Einrichtung: Firmendaten, Logo, Excel-Vorlage, Testblatt, Status |
| `scripts/elektroplan.py` | Einstieg: JSON/Excel → .qet + .pdf + Vorschau |
| `scripts/grundriss_raster.py` | Meterraster über Architektenplan zum Ablesen von Positionen |
| `scripts/symbolkatalog.py` | Katalogblatt aller Symbole |
| `scripts/ep/firma.py` | Lesen/Schreiben der Firmendaten in `~/.elektroplan` |
| `scripts/ep/excel_vorlage.py` | Excel-Vorlage Verteilerdokumentation mit eigenen Firmendaten |
| `scripts/ep/verteilerplan.py` | Layout Verteilerplan einpolig + fachliche Plausibilitätsprüfung |
| `scripts/ep/verteiler_allpolig.py` | Stromlaufplan der Verteilung, allpolig |
| `scripts/ep/stromlaufplan.py` | Schaltungsbausteine Stromlaufplan |
| `scripts/ep/installationsplan.py` | Grundriss, Wandautomatik, Legende, Maßstabsbalken |
| `scripts/ep/stromkreisliste.py` | Import der Excel-Stromkreisliste und Ausfüllen der Vorlage |
| `scripts/ep/normpruefung.py` | Normhinweise (Spannungsfall, DIN 18015-2/-3, VDE 0100-701) |
| `scripts/ep/symbole.py` | Symbolsatz DIN EN 60617 (QElectroTech-Elementformat) |
| `scripts/ep/qet_writer.py`, `pdf_writer.py` | Ausgabe .qet / PDF aus demselben Modell |
| `scripts/ep/schriftfeld.py` | Schriftfeld mit Firmendaten und Logo |
| `referenz/plan_format.md` | JSON-Format aller drei Planarten |
| `referenz/fachliches.md` | Normen, Kennbuchstaben, Konventionen |
| `referenz/ausstattung_din18015.md` / `.json` | Ausstattung nach DIN 18015-2 (Tabelle noch ungeprüft) |
| `referenz/beispiele/*.json` | Musterpläne |
