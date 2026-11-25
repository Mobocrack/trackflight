# Recette PyInstaller de « Trackflight » (Windows : dossier Trackflight\ avec Trackflight.exe ; Mac : « Trackflight.app »).
# Fabrication : pyinstaller Trackflight.spec --noconfirm
import sys

MAC = sys.platform == "darwin"
VERSION = open("VERSION", encoding="utf-8").read().strip()

a = Analysis(
    ["trackflight.py"],
    pathex=["."],
    datas=[("ressources", "ressources"), ("VERSION", ".")],
    hiddenimports=["certifi"],
    excludes=["tkinter", "unittest", "pydoc", "PIL", "numpy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Trackflight",
    console=False,            # aucune fenêtre noire
    icon="icones/icone.icns" if MAC else "icones/icone.ico",
    argv_emulation=False,
    target_arch=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Trackflight")
if MAC:
    app = BUNDLE(
        coll,
        name="Trackflight.app",
        icon="icones/icone.icns",
        bundle_identifier="fr.trackflight.app",
        version=VERSION,
        info_plist={
            "CFBundleName": "Trackflight",
            "CFBundleDisplayName": "Trackflight",
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
