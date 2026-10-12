# Ausstattung nach DIN 18015-2 / RAL-RG 678 vorschlagen

Die Zahlen in **`referenz/ausstattung_din18015.json`** sind am 12.10.2026 mit dem Normtext abgeglichen
(DIN 18015-2:2021-10 Tabelle 1 und 2, RAL-RG 678:2023-02 Ausstattungswert 2 und 3; Normen-Handbuch
Elektrotechniker-Handwerk, 13. Aufl. 2025, S. 499–502 und S. 23–25), `"geprueft": true`. Dieselbe Datei nutzt die
Normprüfung. Diese Seite beschreibt, wie damit geplant wird.

## Ausstattungswert

| Wert | Kennzeichnung | Bedeutung | im Plan-JSON |
|---|---|---|---|
| 1 | ★ | Mindestausstattung = DIN 18015-2 | Standard (`"ausstattungswert": 1`) |
| 2 | ★★ | Standardausstattung RAL-RG 678 | `"ausstattungswert": 2` |
| 3 | ★★★ | Komfortausstattung RAL-RG 678 | `"ausstattungswert": 3` |

„plus“-Werte (mit Gebäudesystemtechnik nach DIN 18015-4) sind im Handbuch nicht abgedruckt. Mehr als ★ nur auf
Wunsch – das ist das Gespräch des Elektrikers mit dem Kunden. Den Nachweis bestätigt der Elektriker im Verteiler, auf der
Rechnung oder einem Beleg.

## Wann

Nennt der Nutzer für einen Installationsplan nur Räume (Name, Größe), aber keine Geräte, dann zuerst eine
**Ausstattung vorschlagen**, nicht raten:

1. Je Raum den Typ bestimmen (Tabelle `raeume[].erkennen`, im Zweifel nachfragen) und die Fläche aus den Innenmaßen
   berechnen (Flur: Raumlänge = längere Seite). Zusammengefasste Nutzungsbereiche (Wohn-Ess-Küche) als Liste:
   `"nutzung": ["kueche", "essen", "wohnen"]` – je Bereich reduziert sich die Zahl der allgemeinen Steckdosen um 1
   (Fußnote a).
2. Je Raum aus der Tabelle: Beleuchtungsanschlüsse, Steckdosen allgemein, Steckdosen je 1,20 m Arbeitsfläche
   (Küche, Hauswirtschaftsraum – Länge als `"arbeitsflaeche_m"` am Raum angeben), Steckdosen für IuK/RuK, Kühlgerät,
   Dunstabzug, Abluftgerät, Telefon/Daten (IuK), Radio/TV (RuK) und Anschlüsse mit eigenem Stromkreis
   (`anschluesse`).
3. Stromkreise für Steckdosen und Beleuchtung nach Wohnfläche (`stromkreise_steckdosen_beleuchtung`, Tabelle 1:
   ≤ 50 m² 3, ≤ 75 m² 4, ≤ 100 m² 5, ≤ 125 m² 6, darüber 7); bei ★★/★★★ je Raum laut `stromkreise`. Dazu je
   besonderes Verbrauchsmittel ein eigener Stromkreis, Keller/Dachboden zusätzlich.
4. Vorschlag kurz als Liste je Raum zeigen, `allgemein`-Regeln dazu (Schaltstelle je Zugang, je Bettplatz
   Schaltstelle + 2 Steckdosen, Verteilergröße, Rauchwarnmelder). Der Nutzer ergänzt oder streicht – erst dann zeichnen.

## Zählweise

- Steckdosen: Standard = jede Kombination an einem Platz zählt als **ein Auslass** (strenger). Der Normtext 2021
  regelt das nicht ausdrücklich; mit `"zaehlweise": "einsatz"` zählt jede Steckdose einer Kombination.
- Die Normprüfung vergleicht je Raum die Summe aller Steckdosen (allgemein + Arbeitsfläche + IuK/RuK + Kühlgerät +
  Dunstabzug) mit den gezeichneten Steckdosen.
- Beleuchtung: jeder Leuchtenauslass (Decke, Wand, Spot-Gruppe) zählt einmal, Linearleuchten (`langfeld`) je Stück.
- IuK/RuK: Daten-, Telefon- und TV-Dosen zusammen gegen IuK + RuK (RuK darf auch als IuK ausgeführt werden).
- Mehrere Räume gleichen Namens (L-Form) zählen zusammen; die Fläche aus `flaeche` hat Vorrang.
- Fußnote d: Waschmaschine und Trockner je Wohnung nur einmal (Küche, Bad, HWR oder Keller).

## Platzierung (DIN 18015-3)

Geräte in die Installationszonen setzen: Schalter neben Türen an der **Schlossseite** im Streifen 10–30 cm neben der
Rohbaukante, Mitte höchstens 1,05 m; Steckdosen h = 0,30 m; über Arbeitsflächen h = 1,15 m (ZW-m 1,00–1,30 m nur
in Räumen mit Arbeitsflächen). Barrierefrei (`"barrierefrei": true`): Bedienhöhe 0,85 m (DIN 18040-2). Die
Normprüfung meldet Abweichungen. Für die Küche zusätzlich die Wandansicht (`"plan": "kuechenplan"`) mit Höhen.
