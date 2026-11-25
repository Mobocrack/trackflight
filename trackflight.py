"""Trackflight : suivi automatique des prix de vos voyages.

    Trackflight                         ouvre l'application dans sa fenêtre
    Trackflight --serveur               interface seule, sans fenêtre (secours et tests)
    Trackflight --releve                relève les prix de tous les voyages actifs
    Trackflight --releve --projet <id>  relève un seul voyage
    Trackflight --releve --si-besoin    relève seulement si le dernier relevé a plus de 20 h
    Trackflight --desinstaller          retire la recherche automatique (appelé par le désinstallateur)
"""
import multiprocessing
import sys


def ouvrir():
    """Clic sur l'icône. Si l'app est déjà ouverte, sa fenêtre revient au premier plan.
    Sinon : serveur local + fenêtre native ; à la fermeture de la fenêtre, tout s'arrête."""
    import json
    import threading
    import urllib.request
    import chemins
    url = f"http://127.0.0.1:{chemins.PORT}/"
    try:
        with urllib.request.urlopen(url + "api/ping", timeout=1.5) as r:
            if json.load(r).get("app") == "trackflight":
                req = urllib.request.Request(url + "api/afficher", data=b"{}", method="POST",
                                             headers={"X-Trackflight": "1", "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=3) as r2:
                    if json.load(r2).get("fenetre"):
                        return
                import fenetre
                fenetre.secours(url)
                return
    except Exception:
        pass

    import fenetre
    import serveur
    srv = serveur.demarrer(surveiller_inactivite=False)
    try:
        fenetre.native(url, lambda: srv and threading.Thread(target=srv.shutdown, daemon=True).start())
    except Exception as e:
        # Composant de fenêtre absent : fenêtre « application » du navigateur, le serveur s'arrête après inactivité.
        import releve
        releve.log.warning("fenêtre native indisponible (%s), repli sur le navigateur", e)
        fenetre.secours(url)
        if srv:
            serveur.surveiller(srv)  # bloque jusqu'à 15 min d'inactivité, puis le processus se termine


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
