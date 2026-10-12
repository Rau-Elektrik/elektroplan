# Fachliche Grundlagen und Konventionen

Diese Grundlagen und Konventionen verwendet der Skill. Maßgeblich bleibt immer der aktuelle Normtext; die Bemessung macht der Elektriker.

**Normstand:** abgeglichen am 12.10.2026 mit dem *DIN-Normen-Handbuch Elektrotechniker-Handwerk*, 13. Aufl. 2025 (DIN Media, Stand der Normen 09/2025). Seitenangaben „S. …“ beziehen sich auf dieses Buch. Hier stehen nur Zahlenwerte und Fundstellen, kein Normtext – maßgeblich ist die gekaufte Norm. Normen, die dort nicht enthalten sind (DIN EN 60617, DIN VDE 0100-xxx), sind wie bisher aus dem allgemeinen Fachwissen und nicht neu abgeglichen.

## Normen, auf die sich die Pläne stützen

| Norm (Ausgabe) | Wofür | Fundstelle |
|---|---|---|
| DIN EN 60617 | Schaltzeichen (Teil 7 Schalt- und Schutzeinrichtungen, Teil 11 Installationspläne) | – |
| DIN EN 61082-1 | Darstellung in Dokumenten der Elektrotechnik | – |
| DIN EN IEC 81346-1/-2 | Referenzkennzeichen und Kennbuchstaben | – |
| DIN VDE 0100-510 (514.5) | Schaltungsunterlagen, Kennzeichnung von Stromkreisen | – |
| DIN 18015-1 (2020-05) | Planungsgrundlagen Wohngebäude, Dokumentation | S. 453 ff. |
| DIN 18015-2 (2021-10) | Mindestausstattung (Tabelle 1 Stromkreise, Tabelle 2 Steckdosen/Anschlüsse) | S. 491 ff. |
| DIN 18015-3 (2016-09) | Leitungsführung, Installationszonen, Montagehöhen | S. 510 ff. |
| DIN 18015-4 (2022-08) / -5 (2015-07) | Gebäudesystemtechnik / luftdicht, wärmebrückenfrei | S. 524 ff. / 565 ff. |
| RAL-RG 678 (2023-02) | Ausstattungswerte ★ / ★★ / ★★★ (Mindest-, Standard-, Komfortausstattung) | S. 21 ff. |
| DIN 18040-2 (2011-09) | Barrierefreie Wohnungen: Bedienhöhen, Bewegungsflächen | S. 582 ff. |
| DIN 14676-1 (2025-05) | Rauchwarnmelder: Planung, Einbau | S. 300 ff. |
| DIN 18012 / 18013 / 18014 | Hausanschluss, Zählerschranknischen, Erdungsanlage | S. 338 / 371 / 382 |
| DIN VDE 0100-410 / -701 | FI-Schutz Steckdosen ≤ 32 A und Beleuchtung, Räume mit Badewanne/Dusche | – |

## Kennbuchstaben (DIN EN IEC 81346-2), wie im Skill verwendet

| Buchstabe | Betriebsmittel |
|---|---|
| F | Schutz: LS, FI, FI/LS, Sicherung, Überspannungsschutz |
| Q | Schalten von Energie: Hauptschalter, Lasttrennschalter |
| K | Relais, Schütz, Stromstoßschalter, Treppenlichtzeitschalter |
| S | Schalter, Taster, Dimmer (handbetätigt) |
| E | Leuchte, Herd/Heizung |
| B | Sensor, Bewegungsmelder |
| M | Motor (Lüfter, Rollladen) |
| X / XD | Klemme / Steckdose |
| T | Transformator, Netzteil |

Im Verteilerplan (einpolig) stehen BMK ohne Bindestrich (F1, Q1) wie auf üblichen Beschriftungsstreifen, im allpoligen Stromlaufplan mit Bindestrich (-F1, -X1). Im Verteiler laufen FI und LS gemeinsam durch: F1 = FI, F2–F6 = LS dahinter (wie Stromkreisliste und Beschriftungsstreifen).

## Darstellung

- **Verteilerplan**: einpolig. Die Leitermarkierung auf der Abgangsleitung zeigt die Aderzahl: Schrägstrich = Außenleiter, Punkt = N, Querstrich = PE. Die Aderzahl kommt aus `adern` (3 → L/N/PE, 5 → 3L/N/PE).
- **Stromlaufplan**: aufgelöst, L1–L3 oben, N und PE unten, Betriebsmittel in Ruhestellung (unbetätigt). Wechselschalter liegen am Öffnerkontakt an. Kontaktspiegel unter Relaisspulen verweist auf die Strompfadnummer (Spalte).
- **Installationsplan**: Symbole nach DIN EN 60617-11; am Symbol Stromkreis und Montagehöhe (h in m über OKFF). DIN 18015-1 (4.7) verlangt: Lage **aller** Anschluss- und Schaltstellen im Installationsplan auf Basis des Grundrisses, Schaltpläne nach VDE 0100-510, Unterlagen nach der Ausführung auf Ist-Stand bringen, Prüfberichte VDE 0100-600 und Erdungsdoku DIN 18014 beilegen, Wartungs-/Prüfintervalle angeben (FI, Rauchwarnmelder, SPD).
- **Wandansicht (Küchenplan)**: Frontansicht je Wand, x ab linker Wandecke, h über OKFF (Fußbodenhöhe über den Meterriss ermitteln, DIN 18015-3, 4.1), Dosen maßstäblich, steigende Bemaßung.

## Installationszonen (DIN 18015-3:2016-09)

Gelten für **unsichtbar verlegte** Leitungen in Wänden (auch Leichtbau, Vorwand, Ständerwand), auch bei Sanierung.

- **Waagerecht** (30 cm breit): ZW-o 15–45 cm unter der Deckenbekleidung, ZW-u 15–45 cm über Fußboden, **ZW-m 100–130 cm** über Fußboden – ZW-m nur in Räumen mit Arbeitsflächen vor den Wänden (Küche, Kochnische, Hausarbeitsraum).
- **Senkrecht** (20 cm breit): 10–30 cm neben den **Rohbaukanten** von Türen (ZS-t), Fenstern (ZS-f) und Wandecken (ZS-e), von Decke zu Decke. Fenster, zweiflügelige Türen und Ecken beidseitig, **einflügelige Türen nur an der Schlossseite**. Dachschrägen: Zonen parallel zu den Bezugskanten.
- **Außenwand außen** (WDVS, vorgehängte Fassade): AZW-o 20–40 cm unter Innendecke, AZW-u 20–40 cm über Fußboden, AZS-t/-f 10–30 cm neben Rohbaukante, AZS-w 50–70 cm neben Wandkanten; Trennungsabstand zum Blitzschutz beachten.
- **Auf der Rohdecke** (unter Estrich): parallel zu den Wänden, gebündelt; ZD-r im Raum max. 30 cm breit, mind. 20 cm Wandabstand; ZD-t im Türdurchgang mind. 15 cm Wandabstand; zwischen Zonen verschiedener Gewerke mind. 20 cm.
- **Unter der Decke** (Putz, Hohlraum, abgehängt): mind. 20 cm parallel zu den Wänden. In der Rohdecke keine Zonen.
- Abweichen in Fertigteilen/Leichtbau nur mit ≥ 6 cm Überdeckung oder ausweichfähig im Hohlraum. Leitungen nicht in Metallprofilen, Durchführungen mit Kantenschutz.
- Betriebsmittel außerhalb der Zonen: **senkrechte Stichleitung** aus einer Zone. Leitungen zu Verteilern nur senkrecht. Restwandstärke hinter Verteilern ≥ 6 cm.

## Montagehöhen

| Gerät | Höhe (Mitte) | Quelle |
|---|---|---|
| Schalter neben Türen | **höchstens 1,05 m** | DIN 18015-3, 5.3 |
| Kombinationen bis 3-fach | oberste Dose auf 1,05 m; 4-fach: zweite, 5-fach: dritte von oben | DIN 18015-3, Bild 6 |
| Steckdosen in ZW-u | 0,30 m | DIN 18015-3, 5.3 |
| Schalter/Steckdosen über Arbeitsflächen | 1,15 m (in ZW-m); Türschalter in der Nähe der Arbeitsfläche angleichen | DIN 18015-3, 5.3 |
| Barrierefrei: Bedienelemente | **0,85 m**, bei mehreren übereinander / begründet bis 1,05 m; seitlich ≥ 50 cm zu Wänden/Einbauten (Rollstuhl) | DIN 18040-2, 4.5.2 |
| Sondergeräte (Display, Thermostat, Videosprechanlage) | nach Hersteller | DIN 18015-3, 5.3 |

Schalter und Steckdosen in einer Zone eines Raums auf gleiche Höhe angleichen. In Küchen mit individuell geplanter Einrichtung darf von den Zonen abgewichen werden (DIN 18015-3, 5.3 Anm. 2).

## Küche – Planungswerte

- **Arbeitsfläche** = Arbeitsplatte 0,85–1,10 m über OKFF; Ausschnitte für Geräte und Spüle werden übermessen (DIN 18015-2, 3.6).
- Mindestausstattung (DIN 18015-2, Tab. 2): 2 Beleuchtungsanschlüsse, 3 Steckdosen allgemein, **2 Steckdosen je 1,20 m Arbeitsfläche**, 1 Steckdose IuK/RuK, Kühlgerät, Dunstabzug; eigene Stromkreise für Elektroherd (3 × 230 V), Mikrowelle/Dampfgarer, Geschirrspüler; Waschmaschine/Trockner und Warmwassergerät, falls nicht anderswo; 1 IuK-Anschluss. Beleuchtung der Arbeitsfläche schatten- und blendfrei (Anschlussstellen dafür vorsehen, 4.1).
- Herd/Kochmulde: 3L+N+PE, ≥ 20 A Strombelastbarkeit, Schutzeinrichtung 20 A (DIN 18015-1, 5.2.5).
- Praxiswerte (keine Norm, Küchenplanung/Hersteller gehen vor): Arbeitsplatte meist 0,91 m, Sockel 0,10 m, Oberschrank UK 1,45 m / OK 2,17 m, Dunstabzug UK etwa 0,65 m über Kochfeld (Elektro), Geschirrspüler-Anschluss im Nachbarschrank, Kühlschrank-Steckdose im Hochschrank über dem Gerät, keine Steckdose direkt über Spüle oder Kochfeld.
- Barrierefrei (R): Herd, Arbeitsplatte und Spüle übereck, Bewegungsfläche vor Kücheneinrichtung 150 cm (sonst 120 cm) (DIN 18040-2, 5.4).

## Stromkreise und Verteiler (DIN 18015-1:2020-05, DIN 18015-2:2021-10)

- Steckdosen-/Beleuchtungsstromkreise nach Wohnfläche (DIN 18015-2, Tab. 1): bis 50 m² **3**, über 50–75 **4**, über 75–100 **5**, über 100–125 **6**, über 125 **7**. Besondere Verbrauchsmittel und Keller-/Dachbodenräume zusätzlich. Mehr Steckdosen als Mindestausstattung → Stromkreise angemessen erhöhen.
- Verteiler im Flur nahe Belastungsschwerpunkt; Einraumwohnung mind. 3-reihig, Mehrraumwohnung mind. 4-reihig à 12 TE; **20 % Reserve** empfohlen; Wohnung über mehrere Etagen: mind. 2 Verteiler (weitere mind. 2-reihig).
- Zuleitung Zählerplatz → erster Wohnungsverteiler: 3L+N+PE, ≥ 63 A. Zählerplatz ≥ 63 A je Zähler, davor selektive Überstromschutzeinrichtung (SH-Schalter).
- **FI 30 mA für Steckdosen bis 32 A und für Beleuchtungsstromkreise** (VDE 0100-410:2018-10, DIN 18015-1, 5.2.5).
- **FI-Belegung** (DIN 18015-1, 5.2.5): 2-poliger FI höchstens **2**, 4-poliger FI höchstens **6** einphasige Endstromkreise; alternativ FI/LS (höchste Verfügbarkeit). Mehr Stromkreise je FI meldet der Skill als Hinweis.
- Durchlauferhitzer: 3L (ggf. N) + PE, ≥ 35 A. Ladeeinrichtung E-Auto: 3L+N+PE ≥ 32 A (oder Leerrohr) plus Leerrohr Netzwerkkabel, Dauerlast; Erzeugungsanlage nicht in Endstromkreis einspeisen (VDE 0100-551).
- Spannungsfall hinter der Messeinrichtung bis zum Verbraucher **höchstens 3 %**, gerechnet mit dem Nennstrom der vorgeschalteten Schutzeinrichtung (5.2.1).
- Hochwassergebiet: HAK, Zählerplatz, Verteiler über Überschwemmungshöhe, darunter liegende Stromkreise mit 30-mA-FI.
- Fehlerlichtbögen: Empfehlungen in VDE 0100-420 (AFDD). Überspannungsschutz nach VDE 0100-443/-534 so nah wie möglich am Speisepunkt.
- IuK und RuK in getrennten, sternförmigen Rohrnetzen; für IuK/RuK-Dosen und SPD Typ 3 Geräteverbindungsdosen ≥ 60 mm tief; mind. Cat.5. Leerrohr Zählerplatz → HÜP (≥ 25 mm) und → Kommunikationsverteiler der Wohnung.

## Schaltstellen und Ausstattung (DIN 18015-2:2021-10, 4.5.2)

- Jedem Raumzugang eine Schaltstelle; Räume mit mehreren Zugängen und Flure: Licht von jedem Zugang schaltbar (Flur alternativ Bewegungs-/Präsenzmelder). Geschosstreppe in der Wohnung: Schaltstelle in jedem Geschoss.
- Je Bettplatz zusätzlich eine Schaltstelle und zwei Steckdosen. Steckdosen auf die Wandabschnitte verteilen (Stolperstellen vermeiden).
- Nicht in Tabelle 2 genannte Räume: mind. 1 Licht, 1 Schaltstelle, 1 Steckdose.
- Zählweise von Mehrfachsteckdosen: Der Normtext 2021 enthält dazu keine Regel. Der Skill zählt standardmäßig **jede Kombination als einen Auslass** (strenger); `"zaehlweise": "einsatz"` zählt jede Steckdose einzeln.
- Allgemeine Räume: Treppenhaus-Schalter/Taster mit Leuchtmittel, Abschaltautomatik mit Warnfunktion; Keller-/Bodengänge je 6 m ein Leuchtenanschluss; Steckdosen dort und im Freien gegen unbefugte Benutzung sichern.

## Rauchwarnmelder (DIN 14676-1:2025-05)

Schlafräume, Kinderzimmer, Flure als Rettungsweg (Pflicht über die Landesbauordnung, z. B. Bayern BayBO Art. 46 Abs. 4). Je Raum mind. einer, je angefangene 60 m² einer; an der Decke möglichst Raummitte, **mind. 0,5 m** von Wand, Unterzug, Einrichtung. Flure: Abstand Melder–Melder max. 15 m, zur Stirnseite max. 7,5 m (mit Unterzügen 7,5 / 3,75 m); Türöffnungen teilen den Flur; in Ecken/Kreuzungen je ein Melder. Abstand zu Täuschungsquellen (Herd, Bad).

## Plausibilitätsprüfung im Verteilerplan (nur Hinweise)

- Steckdosen- und Beleuchtungsstromkreise ohne 30-mA-FI, Stromkreise im Bad (VDE 0100-701, Ausnahmen beachten) und im Außenbereich.
- LS-Nennstrom über typischen Höchstwerten für Cu-Leitungen, Verlegeart C ohne Häufung (Tippfehler-Erkennung, ersetzt keine Bemessung nach DIN VDE 0298-4 / 0100-430):

| mm² | 1,0 | 1,5 | 2,5 | 4 | 6 | 10 | 16 | 25 |
|---|---|---|---|---|---|---|---|---|
| einphasig max. A | 10 | 16 | 25 | 32 | 40 | 63 | 80 | 100 |
| dreiphasig max. A | 10 | 16 | 20 | 32 | 40 | 50 | 63 | 80 |

- Polzahl passt nicht zur Aderzahl (3-polig an 3 Adern; einpolig an 5 Adern).
- Mehr einphasige Stromkreise je FI als DIN 18015-1 vorsieht (2-polig: 2, 4-polig: 6).
- Herd < 20 A oder nicht 3-polig, DLE/Ladeeinrichtung unter Mindestquerschnitt, Zuleitung < 10 mm².
- Doppelte BMK.

## Leiterfarben (Hinweistexte)

L1 braun, L2 schwarz, L3 grau, N blau, PE grün-gelb.
