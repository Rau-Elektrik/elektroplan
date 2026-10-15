"""Programme, die der Skill nutzt: finden, prüfen und – nur nach Rückfrage – installieren.

  Python-Pakete   reportlab, PyMuPDF, Pillow, openpyxl          Pflicht
  CADCraft        DXF/DWG/PDF für Installationsplan/Deckenspiegel (--cadcraft)   optional
  QElectroTech    zum Bearbeiten der .qet-Dateien                 optional

CADCraft wird ohne Administratorrechte in den Konfigurationsordner geladen
(~/.elektroplan/programme/cadcraft-<Version>), aus den offiziellen GitHub-Releases
(github.com/storytold/cadcraft) und mit Prüfung der SHA256-Summe. Eine vorhandene
Installation (Programme-Ordner, PATH, Umgebungsvariable ELEKTROPLAN_CADCRAFT) hat Vorrang.
"""
from __future__ import annotations

import hashlib
import importlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from . import firma

PAKETE = {"reportlab": "reportlab", "fitz": "PyMuPDF", "PIL": "Pillow", "openpyxl": "openpyxl"}
CADCRAFT_VERSION = "0.7.0"           # mit dieser Version getestet
CADCRAFT_MIN = (0, 5, 0)             # ältere können kein Layout/exportpdf wie benötigt
CADCRAFT_REPO = "storytold/cadcraft"
QET_WEB = "https://qelectrotech.org/download.php"

SYSTEM = platform.system()           # Windows | Darwin | Linux | FreeBSD


# ----------------------------------------------------------------------------- Finden
def fehlende_pakete() -> list[str]:
    fehlt = []
    for modul, paket in PAKETE.items():
        try:
            importlib.import_module(modul)
        except ImportError:
            fehlt.append(paket)
    return fehlt


def programme_ordner() -> Path:
    return firma.konfig_ordner() / "programme"


def _exe(name: str) -> str:
    return name + (".exe" if SYSTEM == "Windows" else "")


def cadcraft_cli() -> Path | None:
    """Pfad zu cadcraft-cli: ELEKTROPLAN_CADCRAFT → PATH → übliche Orte → eigener Programme-Ordner."""
    kandidaten: list[Path] = []
    if os.environ.get("ELEKTROPLAN_CADCRAFT"):
        kandidaten.append(Path(os.environ["ELEKTROPLAN_CADCRAFT"]).expanduser())
    w = shutil.which("cadcraft-cli")
    if w:
        kandidaten.append(Path(w))
    if SYSTEM == "Windows":
        for basis in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                      os.environ.get("LOCALAPPDATA") and Path(os.environ["LOCALAPPDATA"]) / "Programs"):
            if basis:
                kandidaten.append(Path(basis) / "CADCraft" / "cadcraft-cli.exe")
    elif SYSTEM == "Darwin":
        kandidaten += [Path("/Applications/CADCraft.app/Contents/MacOS/cadcraft-cli"),
                       Path("/opt/homebrew/bin/cadcraft-cli"), Path("/usr/local/bin/cadcraft-cli")]
    else:
        kandidaten += [Path("/usr/bin/cadcraft-cli"), Path("/usr/local/bin/cadcraft-cli"),
                       Path("/opt/cadcraft/cadcraft-cli")]
    eigen = programme_ordner()
    if eigen.exists():                                  # neueste eigene Installation zuerst
        for ordner in sorted(eigen.glob("cadcraft-*"), reverse=True):
            kandidaten += sorted(ordner.rglob(_exe("cadcraft-cli")))
    for k in kandidaten:
        if k.is_file() and cadcraft_version(k) >= CADCRAFT_MIN:
            return k
    return None


def cadcraft_version(cli: Path) -> tuple[int, ...]:
    try:
        r = subprocess.run([str(cli), "--version"], capture_output=True, text=True, timeout=20)
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", (r.stdout or "") + (r.stderr or ""))
        return tuple(int(x) for x in m.groups()) if m else (0,)
    except (OSError, subprocess.SubprocessError):
        return (0,)


def cadcraft_irgendeine() -> Path | None:
    """Auch zu alte Installationen finden (für die Meldung „Version zu alt“)."""
    for k in [shutil.which("cadcraft-cli"),
              SYSTEM == "Windows" and Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "CADCraft" / "cadcraft-cli.exe"]:
        if k and Path(k).is_file():
            return Path(k)
    return None


def qelectrotech_pfad() -> Path | None:
    kandidaten = []
    if SYSTEM == "Windows":
        for basis in (Path("C:/Program Files"), Path("C:/Program Files (x86)")):
            kandidaten += [basis / "QElectroTech" / "bin" / "qelectrotech.exe",
                           basis / "QElectroTech" / "qelectrotech.exe"]
    elif SYSTEM == "Darwin":
        kandidaten.append(Path("/Applications/QElectroTech.app"))
    gefunden = shutil.which("qelectrotech")
    if gefunden:
        kandidaten.insert(0, Path(gefunden))
    return next((k for k in kandidaten if k.exists()), None)


def uebersicht() -> dict:
    cli = cadcraft_cli()
    alt = None if cli else cadcraft_irgendeine()
    return {
        "python": ".".join(map(str, sys.version_info[:3])),
        "pakete_fehlen": fehlende_pakete(),
        "cadcraft": str(cli) if cli else None,
        "cadcraft_version": ".".join(map(str, cadcraft_version(cli))) if cli else None,
        "cadcraft_zu_alt": str(alt) if alt else None,
        "qelectrotech": str(qelectrotech_pfad()) if qelectrotech_pfad() else None,
    }


# ----------------------------------------------------------------------------- Installieren
class Abbruch(Exception):
    pass


def _ja(frage: str, ja: bool) -> bool:
    if ja:
        return True
    try:
        return input(f"  {frage} (j/n): ").strip().lower().startswith(("j", "y"))
    except EOFError:
        raise Abbruch("Keine Eingabe möglich. Bitte im Terminal starten oder nach Rückfrage mit --ja aufrufen.")


def _arch() -> str:
    m = platform.machine().lower()
    if m in ("amd64", "x86_64", "x64"):
        return "x86_64"
    if m in ("arm64", "aarch64"):
        return "aarch64"
    if m in ("x86", "i386", "i686"):
        return "x86"
    return m


def cadcraft_datei(version: str = CADCRAFT_VERSION) -> str:
    """Name der Release-Datei für dieses System."""
    a = _arch()
    if SYSTEM == "Windows":
        return f"cadcraft-{version}-windows-{ {'x86_64': 'x64', 'aarch64': 'arm64'}.get(a, a) }-portable.zip"
    if SYSTEM == "Darwin":
        return f"cadcraft-cli-{version}-macos-universal.zip"
    if SYSTEM == "Linux" and a in ("x86_64", "aarch64", "riscv64"):
        return f"cadcraft-{version}-linux-{a}.tar.gz"
    if SYSTEM == "FreeBSD":
        return f"cadcraft-{version}-freebsd-x86_64.tar.gz"
    raise Abbruch(f"Für {SYSTEM}/{platform.machine()} gibt es kein CADCraft-Paket – "
                  f"siehe https://github.com/{CADCRAFT_REPO}/releases")


def _laden(url: str, ziel: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "elektroplan-skill"})
    with urllib.request.urlopen(req, timeout=60) as r, open(ziel, "wb") as f:
        gesamt = int(r.headers.get("Content-Length") or 0)
        geladen = 0
        while True:
            block = r.read(1 << 20)
            if not block:
                break
            f.write(block)
            geladen += len(block)
            if gesamt and sys.stdout.isatty():
                print(f"\r  {geladen / 1e6:5.1f} / {gesamt / 1e6:.1f} MB", end="", flush=True)
    if sys.stdout.isatty():
        print()


def _sicher_entpacken(archiv: Path, ziel: Path) -> None:
    """Entpacken ohne Pfade außerhalb von ziel (Zip-Slip)."""
    ziel = ziel.resolve()
    if archiv.suffix == ".zip":
        with zipfile.ZipFile(archiv) as z:
            for n in z.namelist():
                if not (ziel / n).resolve().is_relative_to(ziel):
                    raise Abbruch(f"Ungültiger Pfad im Archiv: {n}")
            z.extractall(ziel)
    else:
        with tarfile.open(archiv) as t:
            if hasattr(tarfile, "data_filter"):           # Python 3.12+ (und Sicherheits-Updates)
                t.extractall(ziel, filter="data")
                return
            for m in t.getmembers():
                ziel_m = (ziel / m.name).resolve()
                link = (ziel_m.parent / m.linkname).resolve() if (m.issym() or m.islnk()) else ziel_m
                if not (ziel_m.is_relative_to(ziel) and link.is_relative_to(ziel)):
                    raise Abbruch(f"Ungültiger Pfad im Archiv: {m.name}")
            t.extractall(ziel)


def installiere_cadcraft(ja: bool = False, version: str = CADCRAFT_VERSION) -> Path:
    vorhanden = cadcraft_cli()
    if vorhanden:
        print(f"CADCraft:      schon da – {vorhanden}")
        return vorhanden
    datei = cadcraft_datei(version)
    basis = f"https://github.com/{CADCRAFT_REPO}/releases/download/v{version}"
    ziel = programme_ordner() / f"cadcraft-{version}"
    print(f"CADCraft {version} (Open Source, MIT/Apache, Download ca. 60 MB) wird von "
          f"github.com/{CADCRAFT_REPO} geladen:")
    print(f"  {datei}  →  {ziel}")
    if not _ja("Herunterladen und installieren?", ja):
        raise Abbruch("CADCraft nicht installiert.")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp = ziel.parent / f".laden-{datei}"
    try:
        _laden(f"{basis}/{datei}", tmp)
        summen = ziel.parent / ".SHA256SUMS.txt"
        _laden(f"{basis}/SHA256SUMS.txt", summen)
        soll = next((z.split()[0].lower() for z in summen.read_text(encoding="utf-8").splitlines()
                     if z.strip().endswith(datei)), None)
        summen.unlink(missing_ok=True)
        ist = hashlib.sha256(tmp.read_bytes()).hexdigest()
        if not soll or soll != ist:
            raise Abbruch(f"Prüfsumme von {datei} stimmt nicht – Download verworfen.")
        if ziel.exists():
            shutil.rmtree(ziel)
        ziel.mkdir(parents=True)
        _sicher_entpacken(tmp, ziel)
    finally:
        tmp.unlink(missing_ok=True)
    clis = sorted(ziel.rglob(_exe("cadcraft-cli")))
    if not clis:
        raise Abbruch(f"cadcraft-cli nicht im Paket {datei} gefunden.")
    if SYSTEM != "Windows":
        for p in ziel.rglob("cadcraft*"):
            if p.is_file():
                p.chmod(p.stat().st_mode | 0o111)
    print(f"CADCraft:      installiert – {clis[0]}")
    if SYSTEM == "Darwin":
        print(f"               Oberfläche zum Bearbeiten (optional): cadcraft-{version}-macos-universal.dmg "
              f"von https://github.com/{CADCRAFT_REPO}/releases")
    return clis[0]


def installiere_qelectrotech(ja: bool = False) -> Path | None:
    vorhanden = qelectrotech_pfad()
    if vorhanden:
        print(f"QElectroTech:  schon da – {vorhanden}")
        return vorhanden
    if SYSTEM == "Windows" and shutil.which("winget"):
        befehl = ["winget", "install", "--id", "QElectroTech.QElectroTech", "-e",
                  "--accept-source-agreements", "--accept-package-agreements"]
    else:                                            # macOS: kein Homebrew-Cask, nur DMG von der Webseite
        print("QElectroTech:  bitte selbst installieren – " + (
            "Linux: Paket „qelectrotech“ der Distribution (z. B. sudo apt install qelectrotech) oder Flatpak "
            "org.qelectrotech.QElectroTech" if SYSTEM == "Linux" else QET_WEB))
        return None
    print("QElectroTech (Open Source, GPL) wird installiert mit: " + " ".join(befehl))
    if not _ja("Installieren?", ja):
        raise Abbruch("QElectroTech nicht installiert.")
    r = subprocess.run(befehl)
    if r.returncode != 0:
        raise Abbruch(f"Installation fehlgeschlagen (Code {r.returncode}) – manuell von {QET_WEB}")
    pfad = qelectrotech_pfad()
    print(f"QElectroTech:  {pfad or 'installiert (Pfad nach Neustart des Terminals sichtbar)'}")
    return pfad


def installiere_pakete(ja: bool = False) -> bool:
    fehlt = fehlende_pakete()
    if not fehlt:
        print("Pakete:        schon da")
        return True
    req = Path(__file__).resolve().parents[2] / "requirements.txt"
    venv = sys.prefix != sys.base_prefix
    befehl = [sys.executable, "-m", "pip", "install", *([] if venv else ["--user"]),
              "--disable-pip-version-check", "-q"]
    befehl += ["-r", str(req)] if req.exists() else fehlt
    print(f"Python-Pakete ({', '.join(fehlt)}) werden mit pip installiert.")
    if not _ja("Installieren?", ja):
        raise Abbruch("Pakete nicht installiert.")
    r = subprocess.run(befehl)
    if r.returncode != 0 and SYSTEM != "Windows":     # PEP 668 (Debian/Ubuntu, Homebrew-Python)
        r = subprocess.run(befehl + ["--break-system-packages"])
    if r.returncode != 0:
        raise Abbruch("pip install ist fehlgeschlagen.")
    if not venv:                    # neu angelegter User-Ordner steht erst nach Neustart im Pfad
        import site
        site.addsitedir(site.getusersitepackages())
    importlib.invalidate_caches()
    return True


INSTALLIERER = {"pakete": installiere_pakete, "cadcraft": installiere_cadcraft,
                "qelectrotech": installiere_qelectrotech}
