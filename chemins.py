"""Emplacements de l'application : données de l'utilisateur, ressources embarquées, commande de relance."""
import os
import platform
import sys

NOM = "MesVols"
PORT = 8766
SYSTEME = platform.system()          # "Windows", "Darwin" (Mac) ou "Linux"
FIGEE = getattr(sys, "frozen", False)  # True dans l'application empaquetée


def donnees():
    """Dossier propre à l'utilisateur, conservé entre les mises à jour de l'application."""
    if os.environ.get("MESVOLS_DONNEES"):  # tests
        os.makedirs(os.environ["MESVOLS_DONNEES"], exist_ok=True)
        return os.environ["MESVOLS_DONNEES"]
    if SYSTEME == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    elif SYSTEME == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    d = os.path.join(base, NOM)
    os.makedirs(d, exist_ok=True)
    return d


def ressources(*morceaux):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "ressources", *morceaux)


def commande(*args):
    """Commande qui relance l'application elle-même (empaquetée ou non) avec des arguments."""
    if FIGEE:
        return [sys.executable, *args]
    return [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mesvols.py"), *args]


def executable_stable():
    """Chemin à inscrire dans le planificateur (l'app .app sur Mac, l'exe sur Windows)."""
    if FIGEE and SYSTEME == "Darwin":
        # .../Mes vols.app/Contents/MacOS/MesVols : on garde l'exécutable interne, toujours valable
        return sys.executable
    return sys.executable
