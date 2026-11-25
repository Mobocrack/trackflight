# Recette PyInstaller de « Mes vols » (Windows : dossier MesVols\ avec MesVols.exe ; Mac : « Mes vols.app »).
# Fabrication : pyinstaller MesVols.spec --noconfirm
import sys

MAC = sys.platform == "darwin"
VERSION = open("VERSION", encoding="utf-8").read().strip()

a = Analysis(
    ["mesvols.py"],
    pathex=["."],
    datas=[("ressources", "ressources")],
    hiddenimports=["certifi"],
    excludes=["tkinter", "unittest", "pydoc", "PIL", "numpy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="MesVols",
    console=False,            # aucune fenêtre noire
    icon="icones/icone.icns" if MAC else "icones/icone.ico",
    argv_emulation=False,
    target_arch=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MesVols")
if MAC:
    app = BUNDLE(
        coll,
        name="Mes vols.app",
        icon="icones/icone.icns",
        bundle_identifier="fr.mesvols.app",
        version=VERSION,
        info_plist={
            "CFBundleName": "Mes vols",
            "CFBundleDisplayName": "Mes vols",
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
