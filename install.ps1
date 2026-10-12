# Installiert den Skill "elektroplan" für Claude Code (Windows) und startet die Einrichtung.
#
#   Aus dem heruntergeladenen Repository:   powershell -ExecutionPolicy Bypass -File install.ps1
#   Direkt aus dem Netz:                    irm https://raw.githubusercontent.com/julayyt/elektroplan/main/install.ps1 | iex
#
# Kopiert skills\elektroplan nach %USERPROFILE%\.claude\skills\elektroplan, installiert die
# Python-Pakete und fragt danach Firmendaten und Logo ab (gespeichert in %USERPROFILE%\.elektroplan).

$ErrorActionPreference = "Stop"
$Repo = "julayyt/elektroplan"
$Ziel = Join-Path $env:USERPROFILE ".claude\skills\elektroplan"

function Schritt($t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }

# --- Quelle: lokales Repository oder Download von GitHub
$Quelle = $null
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "skills\elektroplan\SKILL.md"))) {
    $Quelle = Join-Path $PSScriptRoot "skills\elektroplan"
} else {
    Schritt "Lade elektroplan von GitHub ($Repo)"
    $tmp = Join-Path $env:TEMP ("elektroplan_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
    New-Item -ItemType Directory -Force $tmp | Out-Null
    $zip = Join-Path $tmp "elektroplan.zip"
    Invoke-WebRequest "https://github.com/$Repo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $tmp -Force
    $Quelle = Get-ChildItem $tmp -Directory | ForEach-Object { Join-Path $_.FullName "skills\elektroplan" } |
              Where-Object { Test-Path (Join-Path $_ "SKILL.md") } | Select-Object -First 1
    if (-not $Quelle) { throw "Download unvollständig – skills\elektroplan nicht gefunden." }
}

# --- Python suchen
Schritt "Prüfe Python"
$Py = $null
foreach ($k in @("py", "python", "python3")) {
    if (-not (Get-Command $k -ErrorAction SilentlyContinue)) { continue }
    try { $v = (& $k --version 2>&1 | Out-String) } catch { continue }   # Store-Platzhalter liefert nichts
    if ($v -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 9) { $Py = $k; break }
}
if (-not $Py) {
    Write-Host "Python 3.9+ fehlt. Bitte von https://www.python.org/downloads/ installieren" -ForegroundColor Yellow
    Write-Host "(Haken bei 'Add python.exe to PATH' setzen) und dieses Skript erneut starten."
    exit 1
}
& $Py --version

# --- Skill kopieren
Schritt "Installiere Skill nach $Ziel"
if (Test-Path $Ziel) {
    $item = Get-Item $Ziel -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Write-Host "$Ziel ist eine Verknüpfung (Junction/Symlink) auf einen anderen Ordner." -ForegroundColor Yellow
        Write-Host "Zum Schutz deiner Dateien wird dort nichts überschrieben. Verknüpfung erst selbst entfernen."
        exit 1
    }
    $antwort = Read-Host "Es gibt schon einen Skill 'elektroplan'. Durch die neue Version ersetzen? (j/n)"
    if ($antwort -notmatch '^[jJyY]') { Write-Host "Abgebrochen."; exit 1 }
    Remove-Item $Ziel -Recurse -Force
}
New-Item -ItemType Directory -Force (Split-Path $Ziel) | Out-Null
Copy-Item $Quelle $Ziel -Recurse
Get-ChildItem $Ziel -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# --- Pakete
Schritt "Installiere Python-Pakete (reportlab, PyMuPDF, Pillow, openpyxl)"
& $Py -m pip install --user --disable-pip-version-check -q -r (Join-Path $Ziel "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install ist fehlgeschlagen." }

# --- Einrichtung
Schritt "Einrichtung: deine Firmendaten"
& $Py -X utf8 (Join-Path $Ziel "scripts\einrichtung.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Einrichtung nicht abgeschlossen. Später nachholen mit:" -ForegroundColor Yellow
    Write-Host "  $Py -X utf8 `"$Ziel\scripts\einrichtung.py`"   (oder in Claude Code: 'elektroplan einrichten')"
    exit 1
}

Write-Host ""
Write-Host "Fertig. Starte Claude Code neu und sag z. B.: 'Erstelle einen Verteilerplan für …'" -ForegroundColor Green
Write-Host "QElectroTech (optional, zum Bearbeiten der .qet): https://qelectrotech.org/download.php"
