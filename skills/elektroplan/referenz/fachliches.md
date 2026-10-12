# Fachliche Grundlagen und Konventionen

Diese Grundlagen und Konventionen verwendet der Skill. Maßgeblich bleibt immer der aktuelle Normtext; die Bemessung macht der Elektriker.

## Normen, auf die sich die Pläne stützen

| Norm | Wofür |
|---|---|
| DIN EN 60617 | Schaltzeichen (Teil 7 Schalt- und Schutzeinrichtungen, Teil 11 Installationspläne) |
| DIN EN 61082-1 | Darstellung in Dokumenten der Elektrotechnik (Übersichtsschaltplan, Stromlaufplan aufgelöst) |
| DIN EN IEC 81346-1/-2 | Referenzkennzeichen und Kennbuchstaben |
| DIN VDE 0100-510 (514.5) | Schaltungsunterlagen, Kennzeichnung von Stromkreisen |
| DIN 18015-1 / -3 | Planung Wohngebäude, Installationszonen |
| DIN VDE 0100-410 / -701 | FI-Schutz Steckdosen ≤ 32 A, Räume mit Badewanne/Dusche |

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
- **Installationsplan**: Symbole nach DIN EN 60617-11; am Symbol Stromkreis und Montagehöhe (h in m über OKFF).

## Installationszonen und Montagehöhen (DIN 18015-3, Vorzugsmaße)

- Waagerechte Zonen: oben 15–45 cm unter der Decke, unten 15–45 cm über dem fertigen Fußboden, mittig 90–130 cm (Räume mit Arbeitsflächen über Wänden).
- Senkrechte Zonen: 10–30 cm neben Türen, Fenstern und Raumecken.
- Schalter neben Türen h = 1,05 m, Steckdosen h = 0,30 m, über Arbeitsflächen h = 1,15 m.

## Plausibilitätsprüfung im Verteilerplan (nur Hinweise)

- Steckdosenstromkreise ohne 30-mA-FI (VDE 0100-410), Stromkreise im Bad (VDE 0100-701, Ausnahmen beachten) und im Außenbereich.
- LS-Nennstrom über typischen Höchstwerten für Cu-Leitungen, Verlegeart C ohne Häufung (Tippfehler-Erkennung, ersetzt keine Bemessung nach DIN VDE 0298-4 / 0100-430):

| mm² | 1,0 | 1,5 | 2,5 | 4 | 6 | 10 | 16 | 25 |
|---|---|---|---|---|---|---|---|---|
| einphasig max. A | 10 | 16 | 25 | 32 | 40 | 63 | 80 | 100 |
| dreiphasig max. A | 10 | 16 | 20 | 32 | 40 | 50 | 63 | 80 |

- Polzahl passt nicht zur Aderzahl (3-polig an 3 Adern; einpolig an 5 Adern).
- Mehr als 6 Stromkreise an einem FI (Ableitströme, Verfügbarkeit).
- Doppelte BMK.

## Leiterfarben (Hinweistexte)

L1 braun, L2 schwarz, L3 grau, N blau, PE grün-gelb.
