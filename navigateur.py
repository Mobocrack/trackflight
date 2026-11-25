"""Navigateur utilisé pour lire Kayak et Momondo (sans interface, sans aucun camouflage).

Windows : Microsoft Edge, présent sur tous les PC. Mac : Google Chrome s'il est installé,
sinon un Chromium téléchargé une seule fois dans le dossier de l'application (~150 Mo)."""
import os
import subprocess
import threading

import chemins

DOSSIER = os.path.join(chemins.donnees(), "navigateur")
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", DOSSIER)
CHROME_MAC = "/Applications/Google Chrome.app"
ETAT = {"en_cours": False, "erreur": None}


def chromium_present():
    return os.path.isdir(DOSSIER) and any(n.startswith("chromium") for n in os.listdir(DOSSIER))


def pret():
    if chemins.SYSTEME == "Windows":
        return True
    if chemins.SYSTEME == "Darwin" and os.path.isdir(CHROME_MAC):
        return True
    return chromium_present()


def installer():
    """Télécharge Chromium pour Playwright (bloquant). Renvoie True si tout s'est bien passé."""
    from playwright._impl._driver import compute_driver_executable, get_driver_env
    ETAT.update(en_cours=True, erreur=None)
    try:
        exe = compute_driver_executable()
        cmd = [*exe] if isinstance(exe, (tuple, list)) else [exe]
        env = dict(get_driver_env(), PLAYWRIGHT_BROWSERS_PATH=DOSSIER)
        r = subprocess.run([*cmd, "install", "chromium"], env=env, capture_output=True, text=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode:
            ETAT["erreur"] = (r.stderr or r.stdout)[-300:]
        return r.returncode == 0
    except Exception as e:
        ETAT["erreur"] = str(e)
        return False
    finally:
        ETAT["en_cours"] = False


def installer_en_fond():
    if not pret() and not ETAT["en_cours"]:
        threading.Thread(target=installer, daemon=True).start()


def lancer(pw):
    """Ouvre le navigateur sans interface adapté à l'ordinateur."""
    essais = []
    if chemins.SYSTEME == "Windows":
        essais = [{"channel": "msedge"}, {"channel": "chrome"}]
    elif chemins.SYSTEME == "Darwin" and os.path.isdir(CHROME_MAC):
        essais = [{"channel": "chrome"}]
    essais.append({})
    derniere = None
    for opts in essais:
        try:
            return pw.chromium.launch(headless=True, **opts)
        except Exception as e:
            derniere = e
    if not chromium_present() and installer():
        return pw.chromium.launch(headless=True)
    raise derniere
