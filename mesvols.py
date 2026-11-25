"""Mes vols : suivi automatique des prix de vos voyages.

    Mes vols                         ouvre l'application (démarre l'interface si besoin, puis se ferme)
    Mes vols --serveur               interface seule (lancée en arrière-plan par la commande précédente)
    Mes vols --releve                relève les prix de tous les voyages actifs
    Mes vols --releve --projet <id>  relève un seul voyage
    Mes vols --releve --si-besoin    relève seulement si le dernier relevé a plus de 20 h
    Mes vols --desinstaller          retire la recherche automatique (appelé par le désinstallateur)
"""
import multiprocessing
import subprocess
import sys
import webbrowser


def ouvrir():
    """Clic sur l'icône : démarre l'interface en arrière-plan si elle ne tourne pas, ouvre la page, puis quitte.
    Un nouveau clic rouvre donc toujours la page (indispensable sur Mac)."""
    import json
    import os
    import pathlib
    import urllib.request
    import chemins  # module léger : on n'importe pas le serveur ici, pour que le clic réponde vite
    url = f"http://127.0.0.1:{chemins.PORT}/"
    try:
        with urllib.request.urlopen(url + "api/ping", timeout=1.5) as r:
            if json.load(r).get("app") == "mesvols":
                webbrowser.open(url)
                return
    except Exception:
        pass
    # Retour visuel immédiat : un écran d'ouverture qui bascule sur l'application dès qu'elle répond.
    attente = os.path.join(chemins.donnees(), "ouverture.html")
    with open(chemins.ressources("ouverture.html"), encoding="utf-8") as f:
        html = f.read().replace("__URL__", url)
    with open(attente, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(pathlib.Path(attente).as_uri())
    opts = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if chemins.SYSTEME == "Windows":
        opts["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000  # détaché, nouveau groupe, sans fenêtre
    else:
        opts["start_new_session"] = True
    subprocess.Popen(chemins.commande("--serveur"), **opts)


def main():
    args = sys.argv[1:]
    if "--releve" in args:
        import releve
        projet = args[args.index("--projet") + 1] if "--projet" in args else None
        releve.executer(projet=projet, si_besoin="--si-besoin" in args)
    elif "--serveur" in args or "--sans-navigateur" in args:
        import serveur
        serveur.lancer(ouvrir=False)
    elif "--desinstaller" in args:
        import installation
        installation.desinstaller()
    else:
        ouvrir()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
