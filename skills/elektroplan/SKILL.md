---
name: elektroplan
description: "Elektropläne nach DIN EN 60617 als QElectroTech-Datei (.qet) plus PDF mit eigenem Firmenschriftfeld und Logo – Verteilerplan einpolig und Stromlaufplan der Verteilung allpolig (Klemmleiste X1, Hauptschalter, Schienen, FI, LS, Abgangsklemmen), beides auch aus der Excel-Stromkreisliste; Stromlaufplan von Installationsschaltungen (Wechsel-, Kreuz-, Stromstoßschaltung, Wendeschütz …); Installationsplan (Grundriss mit Symbolen, Legende mit Stückzahlen); Küchenplan/Wandansicht (Frontansicht je Wand mit Küchenmöbeln, Dosen, Höhen über OKFF, Installationszonen, Punkteliste); Deckenspiegel mit Lichtberechnung (Wartungswert nach DIN EN 12464-1 je Raum, Leuchten aus einem Großhandelskatalog wählen, Anzahl nach Wirkungsgradverfahren, im Raster setzen, Berechnungsblatt mit Alternativen und Leuchtenliste). Installationsplan und Deckenspiegel auch als CADCraft-Zeichnung (DXF + DWG + A3-PDF, Architektengrundriss maßgenau aus dem Vektor-PDF, Symbole als Blöcke mit Attributen). Normhinweise nach DIN 18015-1/-2/-3, RAL-RG 678, DIN 18040-2, DIN 14676-1. Verwenden bei Schaltplan, Verteilerplan, Stromlaufplan, Übersichtsschaltplan, Installationsplan, Elektroplan, Küchenplan, Küchenansicht, Wandansicht, Höhenplan, Deckenspiegel, Lichtplanung, Lichtberechnung, Beleuchtungsplanung, Leuchtenauswahl, Lux, Verteilerdokumentation, Stromkreisliste, QElectroTech, CADCraft, CAD, DXF, DWG – und zum Einrichten oder Ändern der Firmendaten/des Logos für diese Pläne."
---

# Elektroplan (Verteilerplan · Stromlaufplan · Installationsplan · Küchenplan · Deckenspiegel)

Erzeugt aus einer JSON-Beschreibung (oder der Excel-Stromkreisliste):
- **`.qet`**: Projekt für QElectroTech (ab 0.100), voll bearbeitbar. Symbole eingebettet unter „Importierte Elemente › Elektroplan (DIN EN 60617)“, Schriftfeld als eingebettete Vorlage `elektroplan_a3q` / `_a4q` / `_a4h`.
- **`.pdf`**: druckfertig, 1 px = 0,25 mm (Maßstäbe stimmen bei Druck in Originalgröße), Schriftfeld mit Logo und Firmendaten des Nutzers.
- **Vorschau-PNG** je Blatt zur Sichtkontrolle.
- Installationsplan und Deckenspiegel zusätzlich als **CADCraft-Zeichnung (DXF + DWG + A3-PDF)** mit maßgenauem Architektengrundriss – Schalter `--cadcraft` / `--nur-cadcraft` (Schritt 3). Braucht das freie CAD-Programm CADCraft.

`<SKILL>` = Ordner dieses Skills (wird beim Laden als Basisverzeichnis angezeigt). Python-Aufruf: Windows `python -X utf8`, macOS/Linux `python3`. Pakete: reportlab, PyMuPDF, Pillow, openpyxl (`<SKILL>/requirements.txt`).

## 0. Einrichtung (immer zuerst prüfen)

Die Firmendaten gehören dem Nutzer und liegen **nicht** im Skill, sondern in `~/.elektroplan/` (oder `ELEKTROPLAN_HOME`). Vor dem ersten Plan in jeder Sitzung:

```
python -X utf8 <SKILL>/scripts/einrichtung.py status
```

- **Programme** (`status` meldet `pakete_fehlen`, `cadcraft`, `qelectrotech`; ausführlich: `einrichtung.py pruefen`). Fehlt etwas, das für die Aufgabe gebraucht wird, **den Nutzer zuerst fragen** – mit Name, Quelle und Größe – und erst nach seinem Ja installieren:
  | Programm | wofür | Nachfrage, dann |
  |---|---|---|
  | Python-Pakete (`pakete_fehlen`) | immer nötig | `einrichtung.py installieren pakete --ja` (pip, Benutzerordner) |
  | CADCraft (`cadcraft` = null) | nur für `--cadcraft` (DXF/DWG) | „CADCraft (Open Source, ca. 60 MB) von github.com/storytold/cadcraft laden?“ → `einrichtung.py installieren cadcraft --ja` (ohne Adminrechte nach `~/.elektroplan/programme`, SHA256 geprüft) |
  | QElectroTech (`qelectrotech` = null) | nur zum Bearbeiten der `.qet` | Windows: `einrichtung.py installieren qelectrotech --ja` (winget, evtl. Windows-Nachfrage); macOS/Linux: Download-Seite bzw. Paketmanager nennen |

  `--ja` nur, wenn der Nutzer im Chat zugestimmt hat; sonst fragt das Skript selbst im Terminal nach. Optionale Programme nicht ungefragt nachinstallieren und nicht erneut anbieten, wenn der Nutzer abgelehnt hat. `cadcraft_zu_alt` gesetzt → vorhandene Version ist älter als 0.5.0, Neuinstallation anbieten.
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
  Nennt der Nutzer nur Räume, aber keine Geräte: zuerst eine **Ausstattung nach DIN 18015-2 vorschlagen** (`referenz/ausstattung_din18015.md`, Zahlen in `ausstattung_din18015.json`, mit DIN 18015-2:2021-10 abgeglichen) und bestätigen lassen, erst dann zeichnen. Standard ist Ausstattungswert 1 (Mindestausstattung); ★★/★★★ nach RAL-RG 678 nur auf Wunsch (`"ausstattungswert": 2|3`).
- *Küchenplan / Wandansicht*: je Wand Breite, Fenster/Türen (Brüstung, Anschlag) und die Möbel von links nach rechts mit Breiten – am besten aus dem Plan des Küchenstudios (PDF/Foto, Maße ablesen und bestätigen lassen). Dazu je Elektropunkt x (Mitte ab linker Wandecke), h (Mitte über OKFF), Kombination, Stromkreis. Fehlen Punkte: Ausstattung Küche nach DIN 18015-2 vorschlagen (2 Steckdosen je 1,20 m Arbeitsfläche, Herd 3 × 230 V, Geschirrspüler, Mikrowelle/Dampfgarer, Kühlgerät, Dunstabzug, IuK) und Lage nach Praxis (Geschirrspüler-Anschluss im Nachbarschrank, Kühlschrank im Hochschrank über dem Gerät, Arbeitsplatte h = 1,15 m, nicht über Spüle/Kochfeld). Herstellerangaben gehen vor. Eine Wand je A3-Blatt bei 1:20; alle Wände auf einem Blatt mit `"massstab": 50`.
- *Deckenspiegel / Lichtplanung* (`"plan": "deckenspiegel"`, Format `plan_format.md` Abschnitt 5): Grundriss wie beim Installationsplan, je Raum die **Nutzung** (Arbeitsstätte → DIN EN 12464-1, Werte in `referenz/licht_din12464.json`; Wohnung → `"licht": {"wohnung": true}`, Praxiswerte), Deckenhöhe bzw. Unterkante abgehängte Decke, Decke massiv oder abgehängt. Schräge Räume auf dem Architektenplan als `polygon` (mit `grundriss_raster.py` ablesen). Leuchten kommen aus `referenz/leuchten_katalog.json` (mitgeliefert: Auswahl aus dem LICHTZENTRALE Kernsortiment 2026 mit Art.-Nr., lm, W, Ra, UGR, IP, Dimmung – für den eigenen Großhandel ersetzen oder ergänzen). Ergebnis dem Nutzer als Vorschlag nennen (Leuchte, Anzahl, Ē, Alternativen) und angenommene Nutzungen bestätigen lassen. Vor dem Installationsplan erstellen; die gesetzten Leuchten stehen in `<Name> Leuchten.json` zum Übernehmen.
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

**CADCraft (DXF/DWG/PDF)** – für Installationsplan und Deckenspiegel, vor allem mit Architektenplan. Vorher `cadcraft` in `einrichtung.py status` prüfen (Schritt 0).
```
python -X utf8 <SKILL>/scripts/elektroplan.py PLAN.json --cadcraft --vorschau "<Temp-Ordner>"
python -X utf8 <SKILL>/scripts/elektroplan.py PLAN.json --nur-cadcraft --vorschau "<Temp-Ordner>"
```
`--cadcraft` = QET/PDF wie bisher **plus** `<Name> CAD.dxf/.dwg/.pdf`; `--nur-cadcraft` nur die CAD-Ausgabe. Der Architektengrundriss (Vektor-PDF, `"grundriss": {"pdf": …, "massstab": 50}`) wird maßgenau in mm übernommen statt als Rasterbild; Wandgeräte rasten wandbündig auf Massivwände ein (auch schräge). Ablauf: Skript `(1 Modell).scr` (Grundriss, Blöcke `EP_*` mit Attributen SK/HOEHE/BEM, Layer `ELT_*`, Leitungen, Zählung) → Attributtexte waagrecht und überdeckungsfrei neben die Symbole → Skript `(2 Layout).scr` (Layout „A3 Plan“, Ansichtsfenster im Maßstab, Legende mit Stückzahlen, Schriftfeld) → DXF, DWG, PDF. Beide `.scr` liegen neben dem Plan und laufen auch von Hand (`cadcraft-cli run --script-file "<…(1 Modell).scr>" --save X.dxf`). Das Logo steht im PDF als Originalgrafik, in DXF/DWG steht dort der Firmenname (CADCraft kann keine Bilder). Beim Deckenspiegel enthält die CAD-Ausgabe nur den Plan; das Berechnungsblatt kommt aus der QET-PDF (`--cadcraft` erzeugt beides). Format: `plan_format.md` Abschnitt 3 c. Bestehende JSON mit `"bild": "….pdf"` funktionieren unverändert; Rasterbilder (PNG/JPG, Scans) gehen in CADCraft nicht.
Koordinaten für einen neuen Architektenplan: `grundriss_raster.py PLAN.pdf --massstab 50` **ohne** `--ausschnitt` → Meter ab linker oberer Seitenecke = Koordinaten für `"pdf"`. Nur den Grundriss als DXF: `python -X utf8 <SKILL>/scripts/ep/grundriss_dxf.py PLAN.pdf 50 AUSGABE`. Symbolbibliothek (alle Blöcke mit Namen) als DXF/DWG/PDF: `python -X utf8 <SKILL>/scripts/ep/cad_symbole.py "<Ordner>"`.
**Selbst zeichnen** (Nutzer will Symbole von Hand setzen): Symbol-Palette im Planmaßstab (jedes Wandsymbol in 4 Richtungen, Beschriftung waagrecht) bzw. leere Startzeichnung mit Layern/Stilen/Blöcken, optional mit Architektengrundriss: `python -X utf8 <SKILL>/scripts/ep/cad_vorlage.py palette "<Ordner>/Symbol-Palette Elektro 1zu50.dxf" [--massstab 100]` · `… vorlage "<Ordner>/<Name>.dxf" [--grundriss PLAN.pdf --massstab 50]`. Arbeitsweise erklären: Palette als zweiten Reiter öffnen, Strg+Umschalt+C (Basispunkt = Einfügepunkt des Symbols) → im Plan Strg+V an die Wand, Stromkreis/Höhe per Doppelklick; nicht ATTSYNC.

## 4. Prüfen

Vorschau-PNG ansehen (unter Windows kurzen Vorschauordner wählen, z. B. `%TEMP%\ep_vorschau` – Pfade über 260 Zeichen scheitern). Die Ausgabe meldet:
- `HINWEIS (Einrichtung)`: keine Firmendaten → Schritt 0 nachholen.
- `HINWEIS (Layout)`: überlappende Texte oder Inhalt außerhalb des Rahmens. Durch Ändern der JSON beheben (andere Position, kürzerer Text, anderes Format).
- `HINWEIS (fachlich)`: nur Verteilung (FI-Pflicht, Querschnitt zu Nennstrom, Polzahl zu Aderzahl, Anzahl Stromkreise je FI). Nichts eigenmächtig ändern, sondern dem Nutzer nennen. Die Bemessung bleibt Sache der Elektrofachkraft.
- `HINWEIS (Norm)`: Spannungsfall je Stromkreis (> 3 %, DIN 18015-1), Stromkreisanzahl zur `wohnflaeche` (DIN 18015-2 Tab. 1), Herd 20 A / Durchlauferhitzer 35 A / Ladeeinrichtung 32 A / Zuleitung 63 A (DIN 18015-1), Ausstattung je Raum (DIN 18015-2 Tab. 2 bzw. RAL-RG 678), Schaltstelle je Raumzugang, Installationszonen und Schaltermitte ≤ 1,05 m, Schalter an der Schlossseite (DIN 18015-3), barrierefrei 0,85 m (DIN 18040-2), Rauchwarnmelder (DIN 14676-1), Bereich 1/2 von Dusche/Wanne (VDE 0100-701), im Küchenplan Steckdosen je 1,20 m Arbeitsfläche und Küchenanschlüsse. „Praxis“-Hinweise sind keine Norm. Ebenfalls nur Hinweise.
- `HINWEIS (Licht)`: nur Deckenspiegel – Ergebnis je Raum (Leuchte, Anzahl, Ē gegen Ēm), angenommene Nutzung, zu großer Leuchtenabstand (Uo), Zusatzhinweise der Norm (Spiegel, Nachtlicht, Bildschirmarbeit). Die Lichtberechnung ist ein Überschlag (Wirkungsgradverfahren, ηR-Näherung, MF 0,8); für einen Nachweis eine Lichtberechnung mit Herstellerdaten (DIALux/Relux).

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
- Fachliche Grundlagen, Normwerte mit Fundstellen und Konventionen: `referenz/fachliches.md`. Normtexte nicht wörtlich in Pläne oder den Skill übernehmen (Urheberrecht DIN) – nur Zahlenwerte und Fundstellen.
- Grundriss vom Architekten: zuerst Raster erzeugen und Positionen ablesen:
  ```
  python -X utf8 <SKILL>/scripts/grundriss_raster.py PLAN.pdf --massstab 100 --dpi 150 [--ausschnitt x0 y0 x1 y1] --ausgabe raster.png
  ```
  Dieselben Werte (`massstab`, `dpi`, `ausschnitt`) in `grundriss` der JSON übernehmen. Die Koordinaten aus dem Raster (Meter, Ursprung oben links) gelten direkt für `geraete`; ohne Räume `wand` je Gerät angeben.
- Mehrere Pläne für denselben Kunden: je Plan eine JSON und eine PDF; bei Bedarf die PDFs zu einer Mappe zusammenfügen.
- **CADCraft** (getestet mit 0.5.0 und 0.7.0): Befehlsantworten kommen über stderr; ein ungültiger Befehl bricht das ganze Skript ab. Umlaute nur mit TTF-Stil (`PLAN` = arial.ttf, `PLAN_FETT` = arialbd.ttf). Attribute drehen beim Einfügen mit dem Block – der Generator setzt sie danach in der DXF waagrecht; in CADCraft nicht `attsync` auf die Blöcke anwenden, sonst springen die Texte zurück. PDF-Export nur über das Layout, Text wird dabei zu Kurven (PDF ca. 3 MB). Eine vom Nutzer in CADCraft bearbeitete DXF/DWG nicht überschreiben – neue Revision erzeugen. Bemaßung: Stile `EP_M` (Meter, 3,19) und `EP_MM` (mm) mit DIMSCALE = Maßstab, Layer `ELT_MASSE`; in der DXF beim Öffnen aktiv, in der DWG einmal `EP_M` wählen. CADCraft-Pfad: `ELEKTROPLAN_CADCRAFT` (Umgebungsvariable) → PATH → Programme-Ordner → `~/.elektroplan/programme`.
- Symbole fehlen? Neue Symbolfabrik in `scripts/ep/symbole.py` ergänzen (gleicher Stil: Raster 10 px, Anschlüsse `1` oben bei y=-30 und `2` unten bei y=+30) und mit einem Testblatt prüfen. Übersicht aller Symbole: `scripts/symbolkatalog.py`.

## Dateien

| Datei | Zweck |
|---|---|
| `scripts/einrichtung.py` | Einrichtung: Firmendaten, Logo, Excel-Vorlage, Testblatt, Status, Programme prüfen/installieren |
| `scripts/ep/programme.py` | Python-Pakete, CADCraft, QElectroTech finden und nach Rückfrage installieren (CADCraft aus GitHub-Releases mit SHA256-Prüfung) |
| `scripts/elektroplan.py` | Einstieg: JSON/Excel → .qet + .pdf + Vorschau |
| `scripts/grundriss_raster.py` | Meterraster über Architektenplan zum Ablesen von Positionen |
| `scripts/symbolkatalog.py` | Katalogblatt aller Symbole |
| `scripts/ep/firma.py` | Lesen/Schreiben der Firmendaten in `~/.elektroplan` |
| `scripts/ep/excel_vorlage.py` | Excel-Vorlage Verteilerdokumentation mit eigenen Firmendaten |
| `scripts/ep/verteilerplan.py` | Layout Verteilerplan einpolig + fachliche Plausibilitätsprüfung |
| `scripts/ep/verteiler_allpolig.py` | Stromlaufplan der Verteilung, allpolig |
| `scripts/ep/stromlaufplan.py` | Schaltungsbausteine Stromlaufplan |
| `scripts/ep/installationsplan.py` | Grundriss, Wandautomatik, Legende, Maßstabsbalken |
| `scripts/ep/cadplan.py` | CADCraft-Ausgabe Installationsplan/Deckenspiegel: Skript 1 (Modell) + Attribut-Platzierung + Skript 2 (Layout A3, Legende, Schriftfeld) → DXF/DWG/PDF |
| `scripts/ep/grundriss_dxf.py` | Vektor-PDF des Architekten → CADCraft-Befehle 1:1 in mm, Wandflächen/-kanten für das Einrasten (auch als Skript) |
| `scripts/ep/cad_vorlage.py` | Symbol-Palette (alle Blöcke, 4 Wandrichtungen, waagrechte Beschriftung) und Startzeichnung zum Selberzeichnen in CADCraft |
| `scripts/ep/cad_symbole.py` | Installationssymbole als CADCraft-Blöcke `EP_*` mit Attributen SK/HOEHE/BEM, Layer `ELT_*`; als Skript: Symbolbibliothek |
| `scripts/ep/wandansicht.py` | Küchenplan/Wandansicht: Möbel, Dosen maßstäblich, steigende Bemaßung, Zonen, Punkteliste, Küchen-Normhinweise |
| `scripts/ep/deckenspiegel.py` | Deckenspiegel + Lichtberechnung: Nutzung → Ēm, Wirkungsgradverfahren, Leuchtenwahl, Raster/k-Means-Anordnung, Berechnungsblatt, Leuchtenliste |
| `referenz/licht_din12464.json` | Ēm/Uo/Ra/UGR je Nutzung nach DIN EN 12464-1:2021-11 (nur Zahlenwerte und Tabellen-Nr.), Wohnungs-Praxiswerte, Raumwirkungsgrad-Näherung |
| `referenz/leuchten_katalog.json` | Leuchtenkatalog (Beispiel: LICHTZENTRALE Kernsortiment 2026) + Empfehlungsreihenfolge je Nutzung |
| `scripts/ep/stromkreisliste.py` | Import der Excel-Stromkreisliste und Ausfüllen der Vorlage |
| `scripts/ep/normpruefung.py` | Normhinweise (DIN 18015-1/-2/-3, RAL-RG 678, DIN 18040-2, DIN 14676-1, VDE 0100-701) |
| `scripts/ep/symbole.py` | Symbolsatz DIN EN 60617 (QElectroTech-Elementformat) |
| `scripts/ep/qet_writer.py`, `pdf_writer.py` | Ausgabe .qet / PDF aus demselben Modell |
| `scripts/ep/schriftfeld.py` | Schriftfeld mit Firmendaten und Logo |
| `referenz/plan_format.md` | JSON-Format aller Planarten (Abschnitt 3 c: CADCraft, Abschnitt 4: Küchenplan/Wandansicht) |
| `referenz/fachliches.md` | Normen, Kennbuchstaben, Konventionen |
| `referenz/ausstattung_din18015.md` / `.json` | Ausstattung nach DIN 18015-2:2021-10 + RAL-RG 678 ★★/★★★ (abgeglichen) |
| `referenz/beispiele/*.json` | Musterpläne |
