"""Navigateur utilisé pour lire Kayak et Momondo (sans interface, sans aucun camouflage).

Windows : Microsoft Edge, présent sur tous les PC. Mac : Google Chrome s'il est installé,
sinon un Chromium téléchargé une seule fois dans le dossier de l'application (~150 Mo)."""
import logging
import os
import subprocess
import threading
import time

import chemins

log = logging.getLogger("trackflight")

DOSSIER = os.path.join(chemins.donnees(), "navigateur")
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", DOSSIER)
CHROME_MAC = "/Applications/Google Chrome.app"
ETAT = {"en_cours": False, "erreur": None, "essai": 0}
REESSAI = 10 * 60  # après un échec, nouveau téléchargement automatique au plus toutes les 10 minutes


def chrome_mac():
    """Google Chrome installé sur le Mac (TRACKFLIGHT_SANS_CHROME=1 : on fait comme s'il n'y était pas, pour les tests)."""
    return (chemins.SYSTEME == "Darwin" and os.path.isdir(CHROME_MAC)
            and not os.environ.get("TRACKFLIGHT_SANS_CHROME"))


def chromium_present():
    """Chromium téléchargé en entier : Playwright pose INSTALLATION_COMPLETE à la fin de chaque téléchargement réussi.
    Un dossier sans ce fichier vient d'un téléchargement interrompu et ne compte pas."""
    if not os.path.isdir(DOSSIER):
        return False
    return any(n.startswith("chromium") and os.path.isfile(os.path.join(DOSSIER, n, "INSTALLATION_COMPLETE"))
               for n in os.listdir(DOSSIER))


def pret():
    if chemins.SYSTEME == "Windows":
        return True
    if chrome_mac():
        return True
    return chromium_present()


def installer():
    """Télécharge Chromium pour Playwright (bloquant). Renvoie True si tout s'est bien passé."""
    from playwright._impl._driver import compute_driver_executable, get_driver_env
    ETAT.update(en_cours=True, erreur=None, essai=time.time())
    log.info("téléchargement du navigateur de recherche dans %s", DOSSIER)
    try:
        exe = compute_driver_executable()
        cmd = [*exe] if isinstance(exe, (tuple, list)) else [exe]
        for f in cmd:  # le pilote embarqué doit rester exécutable (copie, décompression, quarantaine)
            if os.path.isfile(f) and not os.access(f, os.X_OK):
                log.warning("pilote non exécutable, correction des droits : %s", f)
                os.chmod(f, 0o755)
        env = dict(get_driver_env(), PLAYWRIGHT_BROWSERS_PATH=DOSSIER)
        r = subprocess.run([*cmd, "install", "chromium"], env=env, capture_output=True, text=True, timeout=30 * 60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode or not chromium_present():
            ETAT["erreur"] = ((r.stderr or r.stdout).strip() or f"code {r.returncode}")[-300:]
            log.error("téléchargement du navigateur impossible (code %s) : %s", r.returncode, (r.stderr or r.stdout)[-2000:])
            return False
        log.info("navigateur de recherche prêt")
        return True
    except Exception as e:
        ETAT["erreur"] = str(e)[-300:]
        log.exception("téléchargement du navigateur impossible")
        return False
    finally:
        ETAT["en_cours"] = False


def installer_en_fond(forcer=False):
    """Lance le téléchargement en arrière-plan. Après un échec, on ne réessaie tout seul qu'au bout de 10 minutes
    (forcer=True : demande explicite de l'utilisateur)."""
    if pret() or ETAT["en_cours"]:
        return
    if ETAT["erreur"] and not forcer and time.time() - ETAT["essai"] < REESSAI:
        return
    threading.Thread(target=installer, daemon=True).start()


def lancer(pw):
    """Ouvre le navigateur sans interface adapté à l'ordinateur."""
    essais = [{}]
    if chemins.SYSTEME == "Windows":
        essais = [{"channel": "msedge"}, {"channel": "chrome"}, {}]
    elif chrome_mac():
        chrome = {"channel": "chrome"}
        essais = [{}, chrome] if chromium_present() else [chrome, {}]
    derniere = None
    for opts in essais:
        try:
            return pw.chromium.launch(headless=True, **opts)
        except Exception as e:
            log.warning("navigateur %s impossible à ouvrir : %s", opts.get("channel", "chromium"), str(e)[:500])
            derniere = e
    if not chromium_present() and installer():
        return pw.chromium.launch(headless=True)
    raise derniere
