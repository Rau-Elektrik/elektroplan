#!/usr/bin/env bash
# Installiert den Skill "elektroplan" für Claude Code (macOS/Linux) und startet die Einrichtung.
#
#   Aus dem heruntergeladenen Repository:   bash install.sh
#   Direkt aus dem Netz:                    curl -fsSL https://raw.githubusercontent.com/Rau-Elektrik/elektroplan/main/install.sh | bash
#
# Kopiert skills/elektroplan nach ~/.claude/skills/elektroplan, installiert die Python-Pakete
# und fragt danach Firmendaten und Logo ab (gespeichert in ~/.elektroplan).
set -euo pipefail
REPO="Rau-Elektrik/elektroplan"
ZIEL="$HOME/.claude/skills/elektroplan"
schritt() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }

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
PY=""
for k in python3 python; do
  if command -v "$k" >/dev/null && "$k" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then PY="$k"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.9+ fehlt (macOS: brew install python, Linux: Paketmanager)."; exit 1; }
"$PY" --version

schritt "Installiere Skill nach $ZIEL"
if [ -L "$ZIEL" ]; then
  echo "$ZIEL ist ein Symlink – zum Schutz deiner Dateien wird nichts überschrieben."; exit 1
fi
if [ -e "$ZIEL" ]; then
  # bei "curl | bash" kommt die Antwort vom Terminal, nicht aus der Pipe
  read -r -p "Es gibt schon einen Skill 'elektroplan'. Ersetzen? (j/n) " antwort </dev/tty
  case "$antwort" in j*|J*|y*|Y*) rm -rf "$ZIEL" ;; *) echo "Abgebrochen."; exit 1 ;; esac
fi
mkdir -p "$(dirname "$ZIEL")"
cp -R "$QUELLE" "$ZIEL"
find "$ZIEL" -name __pycache__ -type d -prune -exec rm -rf {} +

schritt "Installiere Python-Pakete (reportlab, PyMuPDF, Pillow, openpyxl)"
"$PY" -m pip install --user --disable-pip-version-check -q -r "$ZIEL/requirements.txt" \
  || "$PY" -m pip install --user --break-system-packages --disable-pip-version-check -q -r "$ZIEL/requirements.txt"

schritt "Einrichtung: deine Firmendaten"
"$PY" "$ZIEL/scripts/einrichtung.py" </dev/tty

printf '\n\033[32mFertig. Starte Claude Code neu und sag z. B.: "Erstelle einen Verteilerplan für …"\033[0m\n'
echo "QElectroTech (optional, zum Bearbeiten der .qet): https://qelectrotech.org/download.php"
