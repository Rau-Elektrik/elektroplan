#!/usr/bin/env bash
# Installiert den Skill "elektroplan" für Claude Code (macOS/Linux) und startet die Einrichtung.
#
#   Aus dem heruntergeladenen Repository:   bash install.sh
#   Direkt aus dem Netz:                    curl -fsSL https://raw.githubusercontent.com/Rau-Elektrik/elektroplan/main/install.sh | bash
#
# Kopiert skills/elektroplan nach ~/.claude/skills/elektroplan und fragt dann einzeln, ob fehlende
# Programme geladen werden sollen: Python (Homebrew bzw. Paketmanager), die Python-Pakete,
# CADCraft (DXF/DWG, optional) und QElectroTech (optional). Danach Firmendaten und Logo
# (gespeichert in ~/.elektroplan). Ohne Zustimmung wird nichts installiert.
set -euo pipefail
REPO="Rau-Elektrik/elektroplan"
ZIEL="$HOME/.claude/skills/elektroplan"
schritt() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
# bei "curl | bash" kommt die Antwort vom Terminal, nicht aus der Pipe
frage() { local a; read -r -p "$1 (j/n) " a </dev/tty; case "$a" in j*|J*|y*|Y*) return 0 ;; *) return 1 ;; esac; }
finde_python() {
  PY=""
  for k in python3 python; do
    if command -v "$k" >/dev/null && "$k" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then PY="$k"; return 0; fi
  done
  return 1
}

HIER="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
if [ -n "$HIER" ] && [ -f "$HIER/skills/elektroplan/SKILL.md" ]; then
  QUELLE="$HIER/skills/elektroplan"
else
  schritt "Lade elektroplan von GitHub ($REPO)"
  TMP="$(mktemp -d)"
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.tar.gz" | tar -xz -C "$TMP"
  QUELLE="$(find "$TMP" -path '*/skills/elektroplan/SKILL.md' -print -quit | xargs dirname)"
  [ -n "$QUELLE" ] || { echo "Download unvollständig."; exit 1; }
fi

schritt "Prüfe Python"
if ! finde_python; then
  echo "Python 3.9 oder neuer fehlt (wird für den Skill gebraucht)."
  if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null; then
    frage "Python jetzt mit Homebrew installieren (brew install python)?" && brew install python
  elif command -v apt-get >/dev/null; then
    frage "Python jetzt installieren (sudo apt-get install python3 python3-pip)?" \
      && sudo apt-get install -y python3 python3-pip
  elif command -v dnf >/dev/null; then
    frage "Python jetzt installieren (sudo dnf install python3 python3-pip)?" && sudo dnf install -y python3 python3-pip
  elif command -v pacman >/dev/null; then
    frage "Python jetzt installieren (sudo pacman -S python python-pip)?" && sudo pacman -S --noconfirm python python-pip
  fi
  finde_python || { echo "Bitte Python 3.9+ installieren (macOS: https://www.python.org/downloads/ oder Homebrew) und erneut starten."; exit 1; }
fi
"$PY" --version

schritt "Installiere Skill nach $ZIEL"
if [ -L "$ZIEL" ]; then
  echo "$ZIEL ist ein Symlink – zum Schutz deiner Dateien wird nichts überschrieben."; exit 1
fi
if [ -e "$ZIEL" ]; then
  frage "Es gibt schon einen Skill 'elektroplan'. Ersetzen?" || { echo "Abgebrochen."; exit 1; }
  rm -rf "$ZIEL"
fi
mkdir -p "$(dirname "$ZIEL")"
cp -R "$QUELLE" "$ZIEL"
find "$ZIEL" -name __pycache__ -type d -prune -exec rm -rf {} +

# fragt Pakete, CADCraft und QElectroTech einzeln ab, dann die Firmendaten
schritt "Einrichtung: Programme und deine Firmendaten"
"$PY" "$ZIEL/scripts/einrichtung.py" </dev/tty

printf '\n\033[32mFertig. Starte Claude Code neu und sag z. B.: "Erstelle einen Verteilerplan für …"\033[0m\n'
echo "Programme später nachholen: $PY \"$ZIEL/scripts/einrichtung.py\" installieren cadcraft qelectrotech"
