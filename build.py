"""
build.py — reliable one-command builder for timerY
Run with:  python build.py
"""
import subprocess
import sys
import os
import shutil
import importlib.util


def find_data_folder(package_name, data_folder_name):
    """
    Locate a native-data folder that lives next to a package's install dir.
    e.g. _sounddevice_data sits next to sounddevice/
         libvosk.dll / vosk DLLs sit inside vosk/
    """
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        raise RuntimeError(f"Cannot find package: {package_name}")

    pkg_dir    = os.path.dirname(spec.origin)          # .../site-packages/vosk
    parent_dir = os.path.dirname(pkg_dir)              # .../site-packages/

    # Check next to the package first, then inside it
    for candidate in (
        os.path.join(parent_dir, data_folder_name),
        os.path.join(pkg_dir,    data_folder_name),
    ):
        if os.path.isdir(candidate):
            return candidate

    return None   # caller decides what to do


# ── locate _sounddevice_data ──────────────────────────────────────────────
sd_data = find_data_folder("sounddevice", "_sounddevice_data")
if sd_data is None:
    raise RuntimeError(
        "Could not find _sounddevice_data.\n"
        "Run:  python -c \"import sounddevice; print(sounddevice.__file__)\"\n"
        "and look for _sounddevice_data in that folder or its parent."
    )
print(f"[build] sounddevice data : {sd_data}")

# ── locate vosk package dir (contains libvosk.dll) ───────────────────────
vosk_spec = importlib.util.find_spec("vosk")
if vosk_spec is None:
    raise RuntimeError("Cannot find vosk package.")
vosk_dir = os.path.dirname(vosk_spec.origin)
print(f"[build] vosk package dir : {vosk_dir}")

# ── clean old build artifacts ─────────────────────────────────────────────
for folder in ("build", "dist"):
    if os.path.isdir(folder):
        shutil.rmtree(folder)
        print(f"[build] removed old {folder}/")

# ── separator (Windows = semicolon, Mac/Linux = colon) ───────────────────
S = ";" if sys.platform == "win32" else ":"

# ── PyInstaller command ───────────────────────────────────────────────────
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onedir",
    "--noconfirm",
    "--noconsole",
    "--name", "timerY",
    "--icon", f"assets{os.sep}clock_icon.ico",

    # ── data folders ──────────────────────────────────────────────────────
    "--add-data", f"assets{S}assets",
    "--add-data", f"model{S}model",
    "--add-data", f"{sd_data}{S}_sounddevice_data",   # PortAudio DLL
    "--add-data", f"{vosk_dir}{S}vosk",               # libvosk.dll + *.so

    # ── force-collect all binaries (.dll/.pyd/.so) for both libs ─────────
    "--collect-binaries", "sounddevice",
    "--collect-binaries", "vosk",

    # ── hidden imports ────────────────────────────────────────────────────
    "--hidden-import", "vosk",
    "--hidden-import", "sounddevice",
    "--hidden-import", "cffi",
    "--hidden-import", "win32com.client",
    "--hidden-import", "pythoncom",

    "ui.py",
]

print(f"\n[build] starting PyInstaller...\n")
result = subprocess.run(cmd)
sys.exit(result.returncode)