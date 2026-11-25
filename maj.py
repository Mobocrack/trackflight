"""Mise à jour intégrée : vérifie la dernière version publiée sur GitHub, la télécharge et l'installe.

Windows : télécharge l'installateur, le lance en mode silencieux (il ferme l'app, l'installe, puis la rouvre).
Mac : télécharge l'image disque de la bonne architecture, remplace l'application en place, puis la rouvre.
Seuls des fichiers servis par GitHub (dépôt Mobocrack/trackflight) sont acceptés, en HTTPS.
"""
import json
import os
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request

import chemins

DEPOT = "Mobocrack/trackflight"
API = f"https://api.github.com/repos/{DEPOT}/releases/latest"
HOTES_OK = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")
ETAT = {"actuelle": None, "derniere": None, "disponible": False, "url": None, "taille": 0,
        "verifie": 0, "en_cours": False, "progression": 0, "erreur": None}


def version():
    if os.environ.get("TRACKFLIGHT_VERSION"):  # tests
        return os.environ["TRACKFLIGHT_VERSION"]
    for chemin in (os.path.join(getattr(__import__("sys"), "_MEIPASS", ""), "VERSION"),
                   os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")):
        try:
            with open(chemin, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            continue
    return "0.0.0"


def _cle(v):
    try:
        return tuple(int(x) for x in v.lstrip("v").split(".")[:3])
    except ValueError:
        return (0, 0, 0)


def _ctx():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _fichier_voulu():
    if chemins.SYSTEME == "Windows":
        return "Trackflight-Windows-Installation.exe"
    if chemins.SYSTEME == "Darwin":
        return "Trackflight-Mac-Apple.dmg" if platform.machine() == "arm64" else "Trackflight-Mac-Intel.dmg"
    return None


def verifier(force=False):
    """Interroge GitHub (au plus une fois par heure sauf force). Met à jour ETAT et le renvoie."""
    ETAT["actuelle"] = version()
    if not force and time.time() - ETAT["verifie"] < 3600:
        return ETAT
    ETAT["verifie"] = time.time()
    try:
        req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json", "User-Agent": "Trackflight"})
        with urllib.request.urlopen(req, timeout=15, context=_ctx()) as r:
            d = json.load(r)
        nom = _fichier_voulu()
        asset = next((a for a in d.get("assets", []) if a.get("name") == nom), None)
        ETAT["derniere"] = d.get("tag_name", "").lstrip("v")
        ETAT["disponible"] = bool(asset) and _cle(ETAT["derniere"]) > _cle(ETAT["actuelle"])
        ETAT["url"] = asset["browser_download_url"] if asset else None
        ETAT["taille"] = asset.get("size", 0) if asset else 0
        ETAT["erreur"] = None
    except Exception as e:
        ETAT["erreur"] = "Impossible de vérifier les mises à jour (pas de connexion ?)."
        from releve import log
        log.warning("vérification de mise à jour : %s", e)
    return ETAT


def _telecharger(url, dest):
    if urllib.parse.urlparse(url).scheme != "https" or urllib.parse.urlparse(url).hostname not in HOTES_OK:
        raise ValueError("adresse de téléchargement inattendue")
    req = urllib.request.Request(url, headers={"User-Agent": "Trackflight"})
    with urllib.request.urlopen(req, timeout=60, context=_ctx()) as r, open(dest, "wb") as f:
        final = urllib.parse.urlparse(r.geturl()).hostname
        if final not in HOTES_OK:
            raise ValueError("redirection inattendue")
        total, lu = int(r.headers.get("Content-Length") or ETAT["taille"] or 0), 0
        while True:
            bloc = r.read(256 * 1024)
            if not bloc:
                break
            f.write(bloc)
            lu += len(bloc)
            if total:
                ETAT["progression"] = int(100 * lu / total)


def _installer_windows(fichier):
    # /SILENT : fenêtre de progression seule ; l'installateur ferme l'app, l'installe et la rouvre.
    subprocess.Popen([fichier, "/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", "/NORESTART"],
                     creationflags=0x00000008 | 0x00000200)


def _installer_mac(fichier):
    import sys
    app = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))  # .../Trackflight.app
    if not app.endswith(".app"):
        raise RuntimeError("emplacement de l'application introuvable")
    point = tempfile.mkdtemp(prefix="trackflight-")
    subprocess.run(["hdiutil", "attach", fichier, "-nobrowse", "-quiet", "-mountpoint", point], check=True)
    try:
        nouvelle = os.path.join(point, "Trackflight.app")
        provisoire = app + ".nouvelle"
        shutil.rmtree(provisoire, ignore_errors=True)
        subprocess.run(["ditto", nouvelle, provisoire], check=True)
    finally:
        subprocess.run(["hdiutil", "detach", point, "-quiet"])
    # Remplacement après la fermeture de l'app, puis réouverture (script détaché).
    script = f'sleep 2; rm -rf "{app}"; mv "{provisoire}" "{app}"; open "{app}"'
    subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True)


def installer():
    """Télécharge puis installe la nouvelle version ; l'application se ferme ensuite."""
    if ETAT["en_cours"] or not ETAT["disponible"] or not ETAT["url"]:
        return False
    ETAT.update(en_cours=True, progression=0, erreur=None)

    def job():
        try:
            dossier = tempfile.mkdtemp(prefix="trackflight-maj-")
            fichier = os.path.join(dossier, _fichier_voulu())
            _telecharger(ETAT["url"], fichier)
            if chemins.SYSTEME == "Windows":
                _installer_windows(fichier)
            elif chemins.SYSTEME == "Darwin":
                _installer_mac(fichier)
            time.sleep(1.5)
            os._exit(0)  # libère les fichiers pour l'installateur
        except Exception as e:
            ETAT.update(en_cours=False, erreur="La mise à jour a échoué. Réessayez plus tard ou installez-la depuis la page GitHub.")
            from releve import log
            log.exception("mise à jour : %s", e)
    threading.Thread(target=job, daemon=True).start()
    return True
