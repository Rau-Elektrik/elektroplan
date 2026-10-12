# Ausstattung nach DIN 18015-2 vorschlagen

> **Achtung, ungeprüft:** Die Zahlen in `ausstattung_din18015.json` sind ein Arbeitsstand, aus dem
> Gedächtnis zusammengefasst und **nicht** aus dem Normtext übernommen. Solange dort `"geprueft": false` steht,
> jeden Vorschlag als „Vorschlag, Tabelle noch nicht mit DIN 18015-2 abgeglichen“ kennzeichnen. Wer die
> Tabelle mit dem Normtext (z. B. VDE NormenBibliothek) abgeglichen hat, setzt `"geprueft": true`.

Maßgeblich sind die Zahlen in **`referenz/ausstattung_din18015.json`** (dieselbe Datei nutzt die Normprüfung). Diese
Seite beschreibt nur, wie damit geplant wird.

## Wann

Nennt der Nutzer für einen Installationsplan nur Räume (Name, Größe), aber keine Geräte, dann zuerst eine
**Ausstattung vorschlagen**, nicht raten:

1. Je Raum den Typ bestimmen (Küche, Bad, Wohnen …; Tabelle `raeume[].erkennen`, im Zweifel nachfragen) und die
   Fläche aus den Innenmaßen berechnen (Flur: Länge = längere Seite).
2. Je Raum aus der Tabelle: Anzahl Steckdosen, Beleuchtungsanschlüsse, feste Anschlüsse (Herd, Geschirrspüler,
   Waschmaschine …) und weitere Ausstattung (TV, Daten, Klingel).
3. Stromkreise für Steckdosen und Beleuchtung nach Wohnfläche (`stromkreise_steckdosen_beleuchtung`), dazu je
   fester Anschluss (Herd, Geschirrspüler, Waschmaschine, Trockner, Durchlauferhitzer …) ein eigener Stromkreis.
4. Vorschlag kurz als Liste je Raum zeigen. Der Nutzer ergänzt oder streicht – erst dann zeichnen.
5. Mehr als die Mindestausstattung (Komfort) nur auf Wunsch; das ist das Gespräch des Elektrikers mit dem Kunden.

## Zählweise

- Steckdosen: jeder Steckdosen-Auslass zählt einmal, eine 2- oder 3-fach-Kombination an einem Platz zählt als
  **ein** Auslass (im Zweifel mit Normtext prüfen).
- Beleuchtung: jeder Leuchtenauslass (Decke, Wand, Spot-Gruppe) zählt einmal, Linearleuchten (`langfeld`) je Stück.
- Mehrere Räume gleichen Namens (L-Form) zählen zusammen; die Fläche aus `flaeche` hat Vorrang.

## Platzierung (DIN 18015-3)

Geräte in die Installationszonen setzen: Schalter neben Türen h = 1,05 m im senkrechten Streifen 10–30 cm neben
der Türzarge, Steckdosen h = 0,30 m, über Arbeitsflächen h = 1,15 m. Die Normprüfung meldet Abweichungen.
