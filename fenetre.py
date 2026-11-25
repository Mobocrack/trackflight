"""Fenêtre de l'application : une vraie fenêtre native (WebView2 sur Windows, WebKit sur Mac), sans barre
d'adresse ni onglets, avec sa propre icône dans la barre des tâches ou le Dock.

Repli si le composant système manque : fenêtre « application » d'Edge ou de Chrome, sinon le navigateur."""
import os
import subprocess
import webbrowser

import chemins

FENETRE = {"w": None}


def native(url, a_la_fermeture):
    """Ouvre la fenêtre native et bloque jusqu'à sa fermeture. Lève une exception si c'est impossible."""
    import webview
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True   # « Voir l'offre » s'ouvre dans le navigateur
    webview.settings["ALLOW_DOWNLOADS"] = False
    w = webview.create_window("Trackflight", url, width=1240, height=820, min_size=(390, 600),
                              background_color="#F5F5F7", text_select=True)
    FENETRE["w"] = w
    w.events.closed += a_la_fermeture
    webview.start(private_mode=False, storage_path=os.path.join(chemins.donnees(), "fenetre"))


def montrer():
    """Ramène la fenêtre au premier plan (nouveau clic sur l'icône alors que l'app est ouverte)."""
    w = FENETRE["w"]
    if not w:
        return False
    try:
        w.restore()
        w.show()
        return True
    except Exception:
        return False


def edge():
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            chemin = os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")
            if os.path.exists(chemin):
                return chemin
    return None


def secours(url):
    """Fenêtre « application » d'Edge (Windows) ou de Chrome (Mac), sinon onglet du navigateur."""
    try:
        if chemins.SYSTEME == "Windows" and edge():
            subprocess.Popen([edge(), f"--app={url}", "--window-size=1240,820"])
            return
        if chemins.SYSTEME == "Darwin" and os.path.isdir("/Applications/Google Chrome.app"):
            subprocess.Popen(["open", "-na", "Google Chrome", "--args", f"--app={url}"])
            return
    except OSError:
        pass
    webbrowser.open(url)
