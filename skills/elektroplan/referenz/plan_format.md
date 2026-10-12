# Planformat (JSON) – Referenz

Eine Plandatei beschreibt **einen** Plan. Gemeinsame Felder:

```json
{
  "plan": "verteilerplan | stromlaufplan | installationsplan | kuechenplan (= wandansicht)",
  "format": "A3 quer | A4 quer | A4 hoch",
  "dateiname": "2026-10-08 Verteilerplan UV Wohnung",
  "titel": "Verteilerplan UV Wohnung 1. OG",
  "anlage": "Untertitel im Schriftfeld (optional)",
  "projekt": {
    "kunde": "Familie Muster",
    "objekt": "Musterstraße 12, 12345 Musterstadt",
    "auftrag": "2026-014",
    "datum": "08.10.2026",
    "bearbeiter": "M. Mustermann",
    "revision": "A"
  }
}
```

Standardformate: Verteilerplan A3 quer, Stromlaufplan A4 quer, Installationsplan A3 quer, Wandansicht A3 quer.
Im PDF gilt immer 1 px = 0,25 mm. Der Maßstab im Installationsplan stimmt deshalb, wenn das PDF in Originalgröße gedruckt wird.
Textfelder dürfen Umlaute und `×`, `²`, `Δ` enthalten.

---

## 1. Verteilerplan (Übersichtsschaltplan, einpolig)

Aufbau wie die Excel-Vorlage „Verteilerdokumentation Stromkreisliste“: eine Zeile je Schutzorgan, in Verteilerreihenfolge.
Die Excel-Datei kann auch direkt übergeben werden (`elektroplan.py Stromkreisliste.xlsx`), dann werden die Blätter „Anlage“ und „Stromkreisliste“ gelesen.

```json
{
  "plan": "verteilerplan",
  "verteiler": {"name": "UV Wohnung 1. OG", "standort": "Flur", "netz": "TN-C-S"},
  "einspeisung": {"von": "Zählerplatz Keller", "leitung": "NYM-J", "adern": "5×10",
                  "laenge": 18, "vorsicherung": "SLS E 35 A"},
  "schutzorgane": [
    {"bmk": "Q1", "art": "Hauptschalter", "in": 63, "pole": 3},
    {"bmk": "F0", "art": "Überspannungsschutz", "typ": "Typ 2", "pole": 4},
    {"bmk": "F1", "art": "FI", "in": 40, "idn": 30, "fi_typ": "A", "pole": 4},
    {"bmk": "F2", "art": "LS", "char": "B", "in": 16, "pole": 1, "fi": "F1", "phase": "L1",
     "leitung": "NYM-J", "adern": "3×2,5", "laenge": 12, "raum": "Küche",
     "verbraucher": "Steckdosen Arbeitsplatte links"},
    {"bmk": "F7", "art": "LS", "char": "B", "in": 10, "fi": "F1", "adern": "3×1,5",
     "verbraucher": "Licht Flur", "geraet": {"bmk": "K1", "art": "Stromstoßschalter"}},
    {"bmk": "F12", "art": "FI/LS", "char": "B", "in": 16, "idn": 30, "fi_typ": "A", "pole": 2,
     "leitung": "NYM-J", "adern": "3×2,5", "verbraucher": "Waschmaschine", "raum": "Bad"}
  ]
}
```

| Feld | Bedeutung |
|---|---|
| `bmk` | Betriebsmittelkennzeichen wie auf dem Beschriftungsstreifen (F1, F2 … / Q1) |
| `art` | `LS`, `FI` (auch `FI/RCD`, `RCD`), `FI/LS` (auch `FI/LS (RCBO)`), `Hauptschalter`, `SLS`, `Überspannungsschutz`, `NH-Sicherung`/`Neozed`/`Sicherung`, `Trennschalter`, `Zähler`, `Abzweig` (ungesicherter Abgang direkt von Schiene/Verteilerklemme, z. B. Zuleitung UV mit eigenem Hauptschalter; Text an der Leitung über `hinweis`), sonst Gerät |
| `char` | Auslösecharakteristik B, C, D, K, Z bzw. gG bei Sicherungen |
| `in` | Bemessungsstrom in A |
| `pole` | `1`, `1+N`, `2`, `3`, `3+N`, `4` |
| `fi` | BMK des vorgeschalteten FI → der LS wird unter diesem FI gezeichnet |
| `idn`, `fi_typ` | Bemessungsdifferenzstrom in mA, FI-Typ (A, F, B, B+, AC, EV) |
| `phase` | L1, L2, L3 (optional; bei 3-poligen Schutzorganen automatisch L1–L3) |
| `leitung`, `adern`, `laenge` | z. B. `NYM-J`, `3×2,5`, `12` (m). Die Aderzahl bestimmt die Leitermarkierung (3 = L/N/PE, 5 = 3L/N/PE) |
| `raum`, `verbraucher` | erscheinen senkrecht in der Tabelle |
| `geraet` | nachgeschaltetes Gerät in Zeile 3: `{"bmk": "K1", "art": "Stromstoßschalter"}`. Kurzzeichen werden aus `art` abgeleitet (SST, TLZ, K, ZSU, DIM, AKT, LAR, TR …) oder mit `"kurz"` vorgegeben |
| `wohnflaeche` (oben, neben `verteiler`) | Wohnfläche in m² → Normhinweis, wenn weniger Steckdosen-/Beleuchtungsstromkreise als nach DIN 18015-2 |
| `verteiler.te_je_reihe`, `verteiler.reihen`, `verteiler.hersteller` | nur für die Excel-Stromkreisliste (Reihe/Platz, Standard 12 TE je Reihe) |
| `stromkreisliste` (oben) | `true` = wie `--stromkreisliste`: Excel-Vorlage mit ausfüllen |
| `spannungsfall_max` (oben) | Grenze für den Spannungsfall-Hinweis in % (Standard 3) |
| `position` | `"einspeisung"` erzwingt den Platz in der Einspeisung (sonst automatisch: Hauptschalter, SLS, Zähler, Trenner, Sicherungen ohne Verbraucher). `"vor_hauptschalter"` (nur `Überspannungsschutz` und `Abzweig`, allpolig) hängt das Gerät an eine Vorschiene zwischen Einspeiseklemmen und Hauptschalter (z. B. SPD und ungesicherte Zuleitung zur UV Keller vor Q1); bei 3-poligem Hauptschalter läuft N daran vorbei. `"abgang"` setzt z. B. einen Lasttrennschalter als Abgang an die Schiene (Zuleitung zu einer weiteren UV), gezeichnet mit Lasttrenner-Symbol, allpolig 3-polig + N + PE |

Regeln für die Anordnung:
- Einspeisung (höchstens zwei Geräte, z. B. Zähler + Hauptschalter) links, darunter die Sammelschiene.
- FI-Schalter und Überspannungsschutz hängen an der Schiene. Die LS mit `"fi": "<BMK>"` stehen darunter an einer Unterschiene.
- LS ohne `fi` und FI/LS hängen direkt an der Schiene.
- Passen nicht alle Spalten auf ein Blatt, wird an Gruppengrenzen umgebrochen; die Schiene läuft mit „weiter Blatt 2“ / „von Blatt 1“ weiter.

### Allpolige Darstellung (Stromlaufplan der Verteilung)

Gleiche Daten, Aufruf mit `--darstellung allpolig` (oder `"darstellung": "allpolig"` in der JSON, `beide` für Übersichtsschaltplan + Stromlaufplan in einer Datei). Zusätzliche Felder:

| Feld | Bedeutung |
|---|---|
| `klemmen` (je Stromkreis) | Anzahl Klemmenblöcke L/N/PE für diesen Stromkreis (Standard 1); weitere Blöcke werden über Querverbindungen angeschlossen |
| `ziele` (je Stromkreis) | Beschriftung der Felder unter den Klemmenblöcken, je Block ein Text oder `{"verbraucher", "raum", "leitung", "adern", "laenge"}`; `""` = Feld frei lassen. Ohne `ziele` steht im ersten Feld Verbraucher, Raum und Leitung aus der Liste |
| `klemmen_start` | erste Nummer der Abgangsklemmen (Standard 4, weil 1–3 die Einspeisung sind) |
| `klemmleiste` | Name der Klemmleiste (Standard `X1`) |
| `bmk_praefix` | Vorzeichen der BMK (Standard `-` → -F1, -X1; `""` ohne) |
| `titel_allpolig` | Titel des Stromlaufplans (Standard „Stromlaufplan <Verteiler>“) |

Aufbau: Einspeiseklemmen 1, 2, 3, N, PE unten links → Hauptschalter (3- oder 4-polig, SLS oder Sicherungen) → Hauptschienen L1, L2, L3, N oben. FI 4-polig mit eigenen Unterschienen (2-polige FI bei `pole` 2 oder 1+N), Überspannungsschutz 3+1 an PE, LS 1- oder 3-polig mit Klemmennummern, FI/LS 2-polig, nachgeschaltetes Gerät (`geraet`) im Außenleiter. Je Stromkreis ein Klemmenblock (L fortlaufend nummeriert, N, PE), PE-Schiene über der Klemmleiste. Unter jedem Klemmenblock liegt ein Beschriftungsfeld (A3/A4 hoch ca. 28 mm, A4 quer ca. 19 mm) für das Ziel der Klemmen; unter den Einspeiseklemmen stehen die Angaben zur Zuleitung. Passt nicht alles auf ein Blatt, laufen die Schienen mit Verweis auf das nächste Blatt weiter.
Fehlt `phase` bei einpoligen Stromkreisen, wird reihum L1, L2, L3 angenommen und gemeldet.

Fachliche Hinweise (nur Hinweise, keine Bemessung): Steckdosen, Bad und Außenbereich ohne 30-mA-FI, LS-Nennstrom über der typischen Belastbarkeit des Querschnitts, Polzahl passt nicht zur Aderzahl, mehr als 6 Stromkreise je FI, doppelte BMK.

---

## 2. Stromlaufplan (aufgelöste Darstellung)

Schienen L1–L3 oben, N und PE unten. Jeder Strompfad liegt in einer Rasterspalte, die Spaltennummer ist die Strompfadnummer. BMK werden automatisch vergeben (F, S, E, K, XD, B), wenn sie fehlen.

```json
{
  "plan": "stromlaufplan",
  "titel": "Stromlaufplan Beleuchtung",
  "anlage": "UV Wohnung 1. OG",
  "stromkreise": [
    {"typ": "wechselschaltung", "bezeichnung": "Licht Wohnzimmer", "phase": "L2",
     "ls": {"bmk": "F8", "bez": "B16"},
     "schalter": [{"ort": "Tür Flur"}, {"ort": "Tür Balkon"}], "leuchten": [{"text": "Decke"}]}
  ]
}
```

Gemeinsame Felder je Stromkreis: `typ`, `bezeichnung` (Text unter den Pfaden), `phase` (L1/L2/L3, Standard L1), `ls` (`{"bmk", "bez"}`, `false` = kein LS im Plan), `leuchten` (Anzahl oder Liste `{"bmk", "text"}`).

| `typ` | zusätzliche Felder | Spalten |
|---|---|---|
| `ausschaltung` | `schalter: [{"bmk","ort"}]` | Anzahl Leuchten |
| `serienschaltung` | `schalter`, `leuchten_1`, `leuchten_2` | Gruppe 1 + Gruppe 2 (+1) |
| `wechselschaltung` | `schalter`: 2 Einträge | mind. 2 |
| `kreuzschaltung` | `kreuzschalter`: 1 oder 2, `schalter`: Wechsel – Kreuz(e) – Wechsel | mind. 2 |
| `stromstoss` | `taster` (Anzahl oder Liste `{"bmk","ort"}`), `relais: {"bmk"}` | Taster + Leuchten |
| `treppenlicht` | wie `stromstoss` (Spule mit Rückfallverzögerung) | Taster + Leuchten |
| `dimmer` | `geraet: {"bmk","ort","kurz"}`, `mit_n` (Standard false) | 1 (2 mit N) |
| `bewegungsmelder` | `geraet`, `mit_n` (Standard true) | 2 |
| `steckdosen` | `steckdosen` (Anzahl oder Liste `{"bmk","text"}`) | Anzahl Steckdosen |
| `herd` / `drehstrom` | `verbraucher: {"text": "Herd", "bmk"}`, `ls` 3-polig | 2 |
| `wendeschuetz` | `f1` (Sicherungen 3-polig), `f2` (Überlastrelais, `einstellung`), `f3` (Steuersicherung, `false` = ohne), `k1`/`k2` (Schütze, `text` = Rechts-/Linkslauf), `s0`/`s1`/`s2` (Taster Aus/Rechts/Links), `motor`, `tasterverriegelung` (Standard true); je Eintrag `{"bmk", "text"}`. `phase` = Phase des Steuerstromkreises (gegen N) | 9 |
| `frei` | `pfade: [{"phase", "elemente": [...], "ende": "N"/"PE"/"keins", "beschreibung"}]` | je Pfad 1 |

Elemente im freien Pfad (von oben nach unten, max. 6): `{"symbol": "ls"|"sicherung"|"schalter"|"taster"|"schliesser"|"oeffner"|"spule"|"leuchte"|"motor"|"kasten", "bmk", "text", ...}`.
`schliesser`/`oeffner` mit `oben`/`unten` (Klemmennummern), `spule` mit `art` (`""`, `rv` Rückfallverzögerung, `av` Ansprechverzögerung, `sst` Stromstoß), `kasten`/`geraet` mit `kurz` (Text im Kasten), `motor` mit `motor` (z. B. `"M\n1~"`).

Bei Stromstoß-/Treppenlichtschaltungen steht unter der Spule der Kontaktspiegel („1–2 → Pfad 9“).

Wendeschützschaltung (`wendeschuetz`): Hauptstromkreis F1 → K1/K2 (K2 tauscht L1 und L3) → F2 → M1 3~ mit PE, Steuerstromkreis F3 → F2 95-96 → S0 → S1‖K1 13-14 (Selbsthaltung) → S2 21-22 (Tasterverriegelung) → K2 21-22 (Schützverriegelung) → K1, gespiegelt für K2. Kontaktspiegel mit Strompfadnummern unter den Spulen. Beispiel: `referenz/beispiele/wendeschuetz.json`.

---

## 3. Installationsplan (Grundriss)

Koordinaten in **Metern**, Ursprung oben links, x nach rechts, y nach unten.

### a) Grundriss aus Raummaßen (Aufmaß)

```json
{
  "plan": "installationsplan",
  "massstab": 50,
  "grundriss": {
    "wanddicke": 0.115,
    "raeume": [
      {"name": "Küche", "x": 0, "y": 0, "b": 3.5, "t": 3.2, "wand": {"n": 0.3, "w": 0.3}},
      {"name": "Flur", "x": 0, "y": 3.315, "b": 9.73, "t": 1.4, "textpos": [6.2, 0.9]}
    ],
    "tueren": [{"raum": "Küche", "seite": "s", "pos": 2.4, "breite": 0.885,
                "anschlag": "anfang|ende", "aufgehend": "innen|aussen"}],
    "fenster": [{"raum": "Küche", "seite": "n", "pos": 1.0, "breite": 1.2}]
  },
  "geraete": [
    {"raum": "Küche", "symbol": "steckdose", "anzahl": 2, "x": 0.5, "y": 0,
     "stromkreis": "F2", "hoehe": 1.1}
  ]
}
```

- Räume sind Rechtecke mit **Innenmaßen** (`x`, `y` = innere linke obere Ecke, `b` Breite, `t` Tiefe). Nebeneinanderliegende Räume liegen eine Wanddicke auseinander (z. B. 3,5 + 0,115 = 3,615).
  L-förmige Räume aus zwei Rechtecken bilden, die sich berühren. An der gemeinsamen Kante beide Seiten mit `"offen": ["o"]` bzw. `["w"]` öffnen; das zweite Rechteck ohne `name`, die Gesamtfläche mit `"flaeche": 23.4` vorgeben (`false` blendet sie aus).
- `wand`: eine Zahl für alle Seiten oder je Seite `n`, `o`, `s`, `w` (Außenwand z. B. 0,30).
- `nutzung` (optional): Raumtyp für die Ausstattungsprüfung nach DIN 18015-2, falls der Name ihn nicht verrät (`kueche`, `essen`, `wohnen`, `schlafen`, `arbeiten`, `bad`, `wc`, `flur`, `freisitz`, `hausarbeitsraum`, `hobby`, `abstellraum`, `keller`, `garage`). Zusammengefasste Nutzungsbereiche als Liste, z. B. `["kueche", "essen", "wohnen"]` (allgemeine Steckdosen je Bereich −1).
- `arbeitsflaeche_m` (optional, Küche/HWR): Länge der Arbeitsfläche für „2 Steckdosen je 1,20 m“.
- Oben im Plan (optional): `"ausstattungswert": 1 | 2 | 3` (DIN 18015-2 bzw. RAL-RG 678 ★★/★★★), `"zaehlweise": "auslass" | "einsatz"` (Mehrfachsteckdose = 1 oder je Steckdose), `"barrierefrei": true` (Schalterhöhe 0,85 m und 50 cm Seitenabstand nach DIN 18040-2).
- `grundriss.deckenhoehe` (Standard 2,50 m) für die obere Installationszone.
- `grundriss.sanitaer`: `[{"raum": "Bad", "art": "dusche" | "wanne", "x", "y", "b", "t"}]` (Meter, relativ zur Rauminnenecke) – wird gestrichelt gezeichnet und für die Bereiche 1/2 nach VDE 0100-701 geprüft.
- Türen/Fenster: `seite` des Raums (n, o, s, w), `pos` = Abstand von der linken bzw. oberen Raumecke, `breite` (Rohbaumaß). Bei Türen `anschlag` (`anfang` = Band an der linken/oberen Kante, `ende` = rechts/unten) – daraus ergibt sich die Schlossseite für die Schalterzone; `fluegel: 2` für zweiflügelige Türen.
- `massstab` optional; sonst wird der größte passende aus 1:20 … 1:250 gewählt.

### b) Grundriss als Bild/PDF (Architektenplan)

```json
"grundriss": {"bild": "Grundriss EG.pdf", "seite": 1, "dpi": 150, "massstab": 100,
              "ausschnitt": [x0, y0, x1, y1], "aufhellen": 0.45, "versatz": [0, 0]}
```

- PDF: `massstab` des Originalplans (100 = 1:100) und `dpi` für die Umrechnung angeben.
- Foto/PNG/JPG: statt `massstab` die wirkliche Breite des Bildes `breite_m` angeben.
- `ausschnitt` (Bildpixel bei der gewählten dpi) schneidet den Plan zu.
- Gerätepositionen vorher mit `grundriss_raster.py` (gleiche Angaben) ablesen. Ohne Räume gibt es keine Wandautomatik, also `wand` je Gerät angeben.
- Relative Bildpfade beziehen sich auf den Ordner der JSON-Datei.

### Geräte

| `symbol` | Parameter | an Wand |
|---|---|---|
| `steckdose` | `anzahl` 1–4, `schutzkontakt` (Standard true) | ja |
| `schalter` | `art`: `aus`, `zweipolig`, `serie`, `wechsel`, `kreuz`, `dimmer`, `taster`, `taster_licht`, `kontroll` | ja |
| `taster`, `dimmer` | – | ja |
| `leuchte` | `art`: `decke` (Standard), `wand`, `spot`, `lang`, `not` | nur `wand` |
| `wandleuchte`, `spot` | – | ja / nein |
| `tv`, `daten`, `telefon` | `text` (z. B. SAT, LAN) | ja |
| `geraet` | `text`: H (Herd), BO, GS, WM, T, DLE, KS, DA … | ja |
| `dose` | `art`: `abzweig`, `anschluss` | nein |
| `verteiler`, `klingel` | – | ja |
| `rauchmelder`, `bewegungsmelder`, `melder` | `text` | nein |

### Linien und freie Texte

```json
"linien": [
  {"art": "lichtschiene", "punkte": [[8.0, 6.0], [5.4, 10.0]], "name": "Lichtschiene", "text": "F15"},
  {"art": "kanal", "punkte": [[7.95, 8.42], [7.38, 9.5]], "text": "BR-Kanal", "textpos": [8.05, 8.95]}
],
"texte": [{"x": 4.35, "y": 4.15, "text": "Behandlung 1", "groesse": 8}]
```

- `linien[].art`: `lichtschiene` (dick, durchgezogen), `ledprofil` (strichpunktiert), `kanal` (Brüstungskanal, rot gestrichelt), `leitung` (Leitungsweg, dünn gestrichelt), `lichtlinie` (LED-Einbauprofil, sehr dick), `voute` (indirekte Lichtvoute, kupfer gestrichelt), `stromschiene` (strichpunktiert), `kontur` (Deckensegel/Deckenversprung, grau gestrichelt), `langfeld` (Linearleuchte mit Endstrichen, zählt in der Legende als Stück).
- Statt `punkte` geht `"mitte": [x, y], "winkel": 55.7, "laenge": 1.15` (Winkel in Grad, im Uhrzeigersinn ab x-Achse) – für schräg gestellte Linearleuchten über Liegen oder Tresen.
- Leuchte `"art": "strahler"` = Strahler mit Richtungspfeil; die Richtung kommt über `wand` (n = Pfeil nach unten, o = nach links, s = nach oben, w = nach rechts). `name` = Text in der Legende (gleicher Name + Stil wird zusammengefasst, Gesamtlänge in m), `text`/`textpos` = Beschriftung im Plan.
- `texte`: freie Beschriftung (Raumnamen auf einem Architektenplan ohne `raeume`).
- Beschriftungen von Geräten an senkrechten Wänden (`wand` o/w) stehen neben dem Symbol im Raum, mittig auf Symbolhöhe – Geräte an einer Wand mit ca. 0,45 m Abstand setzen (bei 1:50), dann überlappt nichts.

Felder je Gerät: `x`, `y` (Meter; mit `raum` relativ zur Rauminnenecke), `raum`, `wand` (n/o/s/w; ohne Angabe wird die nächste Wand des Raums gewählt; `"frei"` = keine Automatik), `stromkreis` (Beschriftung, z. B. F3), `hoehe` (Montagehöhe in m), `bemerkung`.
Wandgeräte werden auf die Wandinnenseite gesetzt und zeigen in den Raum. Die Legende rechts zählt alle Geräte.

---

## 4. Wandansicht / Küchenplan (Frontansicht mit Höhen)

`"plan": "kuechenplan"` (oder `"wandansicht"` für andere Räume, z. B. Bad). Je Wand eine Frontansicht: Blick auf die
Wand, **x ab linker Wandecke** (fertige Wand), **h über OKFF**, beides in Metern. Gezeichnet werden Wand mit Boden und
Decke, Fenster/Türen, Möbel, die Dosen maßstäblich (Ø 68 mm, Kombination im 71-mm-Raster), Positionsnummern mit
Kurzzeichen, steigende Bemaßung für x (unten) und h (links), Höhenkoten der Möbel (rechts) und die Installationszonen
nach DIN 18015-3 (blau). Rechts die Punkteliste mit Symbol nach DIN EN 60617-11. Maßstab automatisch 1:20 (sonst
1:25/1:50, oder `"massstab"`), passen mehrere Wände nicht auf ein Blatt, folgen weitere Blätter.

```json
{
  "plan": "kuechenplan",
  "raum": "Küche",
  "deckenhoehe": 2.50,
  "kueche": {"arbeitsplatte": 0.91, "plattenstaerke": 0.04, "sockel": 0.10,
             "oberschrank_uk": 1.45, "oberschrank_ok": 2.17, "hochschrank_ok": 2.17, "dunstabzug_abstand": 0.65},
  "zonen": true, "hilfslinien": true, "ausstattungswert": 1, "zaehlweise": "auslass", "barrierefrei": false,
  "waende": [
    {"name": "Wand A", "bezeichnung": "Spülenzeile", "breite": 3.40,
     "oeffnungen": [{"art": "fenster", "x": 1.30, "breite": 1.00, "bruestung": 1.05, "hoehe": 1.20},
                    {"art": "tuer", "x": 0.25, "breite": 0.885, "hoehe": 2.01, "anschlag": "links"}],
     "moebel": [{"art": "unterschrank", "breite": 0.60}, {"art": "geschirrspueler", "breite": 0.60},
                {"art": "spuele", "breite": 0.80}, {"art": "oberschrank", "x": 0, "breite": 1.20},
                {"art": "dunstabzug", "x": 1.80, "breite": 0.80}],
     "linien": [{"art": "led", "x": 0.05, "breite": 1.10, "h": 1.43, "text": "LED"}],
     "punkte": [{"symbol": "steckdose", "anzahl": 2, "x": 0.40, "h": 1.15, "stromkreis": "F3", "text": "Arbeitsplatte"},
                {"symbol": "geraet", "text": "GS", "x": 0.30, "h": 0.30, "stromkreis": "F6", "bemerkung": "im Nachbarschrank"}]}
  ]
}
```

**`kueche`** (alle optional, Standard wie oben): Höhe OK Arbeitsplatte, Plattenstärke, Sockel, Oberschrank UK/OK,
Hochschrank OK, Abstand Kochfeld → UK Dunstabzug. Maße aus der Küchenplanung übernehmen.

**`oeffnungen`**: `art` `fenster` (`bruestung`, `hoehe`) oder `tuer` (`hoehe`, `anschlag` `links`/`rechts` = Bandseite in
der Ansicht, `fluegel`), `x` = linke Rohbaukante, `breite`, optional `text`.

**`moebel`**: `art`, `breite`, `x` (fehlt `x`, wird hinter dem vorigen Möbel derselben Ebene angereiht – Unterschränke
und Hochschränke zusammen, Oberschränke für sich), optional `text`, `uk`, `ok`, `gestrichelt`.

| `art` | Ebene | gezeichnet |
|---|---|---|
| `unterschrank`, `eckschrank`, `auszug`, `blende` | unten (Sockel bis UK Arbeitsplatte) | Korpus + Sockel, Text „US 60“ |
| `geschirrspueler` | unten | mit Bedienblende, „GSP“ |
| `spuele` | unten | Becken gestrichelt, Armatur |
| `kochfeld` (oder `"kochfeld": true` an einem Unterschrank) | unten | Kochfeld auf der Arbeitsplatte |
| `herd` / `backofen_unterbau` | unten | Backofentür + Kochfeld |
| `waschmaschine`, `trockner` | unten | Bullauge |
| `hochschrank`, `kuehlschrank`, `backofen_hoch`, `geraeteschrank` | Boden bis OK Hochschrank | `nischen: [{"uk", "ok", "text"}]` für Gerätenischen |
| `oberschrank`, `regal` | UK–OK Oberschrank | Korpus, „OS 60“ |
| `dunstabzug` | UK = Arbeitsplatte + Abstand | `form` `wand` (Haube + Kamin bis Decke, Standard) oder `flach` |
| `arbeitsplatte` | – | nur nötig für abweichende Platten; sonst automatisch über zusammenhängenden Unterschränken |
| sonst (`rechteck` …) | frei: `uk`, `ok`/`hoehe` | Rechteck mit Text |

**`linien`**: `{"art": "led" | "kanal", "x", "breite", "h", "text"}` – LED-Band unter Oberschränken, Kanal.

**`punkte`**: `symbol`, `x`, `h` (Dosenmitte), `anzahl` (Kombination), `richtung` (`waagerecht` Standard: x = Mitte,
h = Dosenmitte; `senkrecht`: h = **oberste** Dose wie DIN 18015-3), `stromkreis`, `text`, `bemerkung`, optional `nr`.

| `symbol` | Kurzzeichen | Farbe |
|---|---|---|
| `steckdose` (`text` z. B. Arbeitsplatte, Kühlschrank, Dunstabzug) | SD / 2×SD | schwarz |
| `schalter` (`art` aus, wechsel, kreuz, serie, taster, dimmer …), `taster`, `dimmer` | S, W, K, SR, T, D | blau |
| `geraet` (`text` = Code: H, KF, HD, BO, GS, KS, KG, DA, MW, DG, WM, T, DLE, WW, KL, KM, WX) | Code | rot |
| `auslass` / `unterbauleuchte` / `leuchte` (`art` wand, unterbau, sockel) | L | orange |
| `daten`, `telefon`, `tv` | LAN, TEL, TV | grün |
| `dose`, `thermostat`, `melder` | AD, RTR, RM | grau |

Normhinweise (nur Hinweise): Punkte außerhalb der Installationszonen (in Küchen zulässig, Stichleitung), Schalter über
1,05 m bzw. barrierefrei nicht 0,85 m, Schalter auf der Bandseite oder nicht 10–30 cm neben der Tür, Steckdosen über
der Arbeitsfläche weniger als 2 (★★/★★★: 3) je angefangene 1,20 m, Steckdose dicht über der Arbeitsplatte,
allgemeine Steckdose hinter einem Möbel, Küchenausstattung nach DIN 18015-2 Tab. 2 (Herd, Geschirrspüler,
Mikrowelle/Dampfgarer, Kühlgerät, Dunstabzug, IuK, Steckdosenzahl), „Praxis“: Steckdose direkt über Spüle/Kochfeld.
Beispiel: `referenz/beispiele/kuechenplan.json`.

---

## 5. Deckenspiegel mit Lichtberechnung

`"plan": "deckenspiegel"` – gleicher Grundriss wie der Installationsplan (Abschnitt 3: `raeume` oder Architektenplan als
`bild`). Je Raum wird der Wartungswert Ēm nach **DIN EN 12464-1:2021-11** ermittelt (Wohnungen: Praxiswert, keine Norm),
die passende Leuchte aus `referenz/leuchten_katalog.json` (LICHTZENTRALE Kernsortiment 2026) gewählt, die Anzahl mit dem
Wirkungsgradverfahren berechnet und die Leuchten im Raster gesetzt. Blatt 1 = Deckenspiegel, Blatt 2 = Lichtberechnung
(Anforderung, k, Leuchte mit Art.-Nr., n, Ē, W/m², Abstand, Alternativen, Leuchtenliste). Zusätzlich entsteht
`<Name> Leuchten.json` mit den gesetzten Leuchten zum Übernehmen in den Installationsplan.

```json
{
  "plan": "deckenspiegel",
  "titel": "Deckenspiegel Praxis EG",
  "licht": {"deckenhoehe": 2.60, "reflexion": "hell", "wartungsfaktor": 0.8,
            "stufe": "erforderlich", "max_ueber": 1.6, "wohnung": false, "beschriftung": true},
  "grundriss": { "...": "wie Installationsplan" },
  "lichtraeume": [
    {"raum": "Büro", "stromkreis": "F6"},
    {"name": "Behandlung 1", "nutzung_licht": "massage", "polygon": [[3.5, 1.7], [6.8, 1.7], [6.8, 3.9], [4.2, 7.4]],
     "stromkreis": "F3"},
    {"raum": "Bad", "decke": "massiv", "ip": 44},
    {"raum": "Empfang", "leuchte": "lz_dlg_150", "anzahl": 4}
  ],
  "geraete": [], "linien": [], "texte": []
}
```

- **`lichtraeume`** (optional): ohne Angabe werden alle `grundriss.raeume` mit Namen berechnet. Je Raum entweder
  `raum` (Name aus `grundriss.raeume`), `polygon` (Eckpunkte in Plankoordinaten, für schräge Räume auf einem
  Architektenplan – Werte mit `grundriss_raster.py` ablesen) oder `x`/`y`/`b`/`t`.
- **`nutzung_licht`**: Schlüssel aus `referenz/licht_din12464.json`, z. B. `buero` (34.2, 500 lx), `empfang` (34.6, 300),
  `warteraum` (45.1, 200), `praxis_flur` (45.2, 100), `flur` (9.1, 100), `sanitaer` (10.4, 200), `pausenraum` (10.2, 100),
  `kantine` (10.1, 200), `mitarbeiterraum` (46.2, 300), `untersuchung` (48.1, 500, Ra 90, 4000–5000 K),
  `massage` (53.6, 300 – auch Physiotherapie), `lager` (12.1, 100), `archiv`, `besprechung`, `garderobe` …;
  Wohnung (`"licht": {"wohnung": true}`): `wohnen`, `essen`, `kueche`, `schlafen`, `kind`, `arbeiten`, `bad`, `wc`,
  `flur_wohnung`, `hausarbeitsraum`, `keller`, `garage`. Ohne Angabe wird die Nutzung aus dem Raumnamen erkannt;
  „Behandlung“ wird als Untersuchung (48.1) angenommen und als `Annahme` gemeldet.
- Je Raum optional: `deckenhoehe` (Lichtpunkthöhe, bei abgehängter Decke deren UK), `nutzebene` (Standard aus der Norm:
  0,75 m bzw. 0 m bei Fluren/Sanitär), `reflexion` (`hell` 0,7/0,5/0,2 · `mittel` · `dunkel`), `stufe` (`modifiziert`
  = höherer Normwert), `ziel_lx`, `decke` (`massiv` → keine Einbauleuchten), `ip` (Mindestschutzart), `leuchte`
  (Katalog-ID erzwingen), `auswahl` (eigene Reihenfolge von Katalog-IDs), `anzahl`, `winkel` (Rasterdrehung in Grad,
  sonst längste Wand), `pendel: true` (Pendelleuchten zulassen), `dali: true` (DALI-dimmbare Variante mit deren
  Art.-Nr.; auch global unter `licht`), `stromkreis`, `textpos`. Die Leuchtenliste nennt je Leuchte die Dimm-Möglichkeit
  lt. Katalog (`dimmung`).
- **Leuchtenwahl**: Reihenfolge je Nutzung aus `leuchten_katalog.json › empfehlung`; geeignet ist eine Leuchte, wenn
  Ra, UGR (ohne Angabe nur bei UGR-Grenze ≥ 25), IP, Lichtfarbe, Montage und Raumgröße passen. Gewählt wird die erste,
  die Ēm erreicht, den Abstand einhält (≤ `abstand_faktor` × Höhe über Nutzebene) und höchstens `max_ueber` × Ēm bringt;
  sonst die mit der kleinsten Leistung. Zwei weitere passende Leuchten stehen als Alternativen auf Blatt 2.
- **`auslass`** (Deckenauslass, Leuchte bauseits): für Wohnräume/Betondecken – statt einer Leuchte wird der
  Mindest-Lichtstrom je Leuchte berechnet (1 Auslass je ca. 18 m² bzw. je 3,5 m Raumlänge).
- Rechteckige Räume: gleichmäßiges Raster mit der kleinsten passenden Leuchtenzahl; schräge/verwinkelte Räume:
  gleichmäßige Flächenteilung (k-Means), Punkte auf 5 cm gerundet. Eine Leuchte kommt an den Punkt mit dem größten
  Wandabstand.
- Eigene oder projektbezogene Leuchten: `"licht": {"katalog": [{"id": "...", "name": "...", "bauform":
  "panel|downlight|linear|anbau|auslass", "montage": "einbau|anbau|pendel|einbau_anbau", "lm", "w", "ra", "ugr", "ip",
  "tcp": [...], "b"/"t" bzw. "d" bzw. "laenge", "abstand_faktor", "art_nr"}], "empfehlung": {"buero": ["..."]}}`.
- Ausgabe `HINWEIS (Licht)`: Ergebnis je Raum, Annahmen, Abstand zu groß (Uo prüfen), Normhinweise (z. B. Spiegel,
  Nachtbeleuchtung Flur). Überschlag – Uo und UGR werden nicht berechnet; Nachweis mit Herstellerdaten (DIALux/Relux).
Beispiel: `referenz/beispiele/deckenspiegel_praxis.json`.
