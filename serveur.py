"""Interface de l'application : petit serveur local (127.0.0.1 seulement) affiché dans le navigateur.

Il s'arrête tout seul 15 minutes après la fermeture de la dernière page. Un second lancement de
l'application rouvre simplement la page déjà active.
"""
import json
import os
import subprocess
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import build
import chemins
import installation
import maj
import navigateur
import notif
import projets as P
import releve
import villes

PORT = chemins.PORT
INACTIVITE = 15 * 60
ETAT = {"derniere_activite": time.time(), "proc": None, "installation": None}
VERROU = threading.Lock()
PING = "<script>setInterval(()=>fetch('/api/ping').catch(()=>{}),60000)</script></body>"


def progression():
    return releve.lire_json(releve.PROGRESSION, None) if releve_actif() else None


def releve_actif():
    proc = ETAT["proc"]
    return (proc is not None and proc.poll() is None) or releve.en_cours()


def etat_app():
    return {"navigateur_pret": navigateur.pret(), "navigateur_prepa": navigateur.ETAT["en_cours"],
            "navigateur_erreur": navigateur.ETAT["erreur"], "releve_en_cours": releve_actif(),
            "installation": ETAT["installation"]}


def nettoyer(p):
    p = P.completer(p)
    for k in ("adultes", "enfants", "bebes", "flex"):
        p[k] = int(p[k] or 0)
    p["duree_max_h"] = float(p["duree_max_h"]) if p["duree_max_h"] not in (None, "") else None
    for k in ("seuil_escale", "seuil_direct", "baisse_min", "plafond_baisse_escale", "plafond_baisse_direct"):
        v = p["alertes"].get(k)
        p["alertes"][k] = int(v) if v not in (None, "") else None
    for cote in ("origine", "destination"):
        p[cote]["code"] = (p[cote]["code"] or "").strip().upper()
    if p["type"] != "ar":
        p["date_retour"] = ""
    p["nom"] = p["nom"].strip()
    return p


def page_html(texte):
    return texte.replace("</body>", PING, 1).encode("utf-8")


class Gestionnaire(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _envoyer(self, code, corps, type_="application/json; charset=utf-8", entetes=None):
        data = corps if isinstance(corps, bytes) else json.dumps(corps, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (entetes or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _hote_ok(self):
        return self.headers.get("Host", "") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")

    def do_GET(self):
        ETAT["derniere_activite"] = time.time()
        if not self._hote_ok():
            return self._envoyer(403, {"erreur": "Accès refusé."})
        chemin = self.path.split("?")[0]
        if chemin == "/api/ping":
            return self._envoyer(200, {"app": "trackflight"})
        if chemin == "/":
            with open(chemins.ressources("app.html"), encoding="utf-8") as f:
                html = f.read().replace('<html lang="fr">', f'<html lang="fr" data-theme="{releve.config()["theme"]}">', 1)
                return self._envoyer(200, page_html(html), "text/html; charset=utf-8")
        if chemin == "/api/donnees":
            cfg = releve.config()
            liste = P.charger()
            return self._envoyer(200, {
                "projets": liste, "villes": villes.en_json(),
                "resumes": {p["id"]: build.resume_projet(p) for p in liste},
                "statut": {"en_cours": releve_actif(), "progression": progression()},
                "reglages": {"serpapi": bool(cfg["serpapi_cle"]), "notifications": cfg["notifications"],
                             "serpapi_max_mois": cfg["serpapi_max_mois"], "dossier": chemins.donnees(),
                             "programmee": installation.est_installee(), "app": etat_app(),
                             "theme": cfg["theme"], "version": maj.version(), "maj": maj.ETAT,
                             "systeme": chemins.SYSTEME, "accueil_vu": cfg["accueil_vu"]}})
        if chemin == "/api/statut":
            return self._envoyer(200, {"en_cours": releve_actif(), "progression": progression(), "app": etat_app(),
                                       "maj": maj.ETAT})
        if chemin.startswith("/api/voyage/"):
            pid = chemin[len("/api/voyage/"):].strip("/")
            p = next((x for x in P.charger() if x["id"] == pid), None)
            d = build.donnees_voyage(p) if p else None
            return self._envoyer(200, d or {"vide": True})
        if chemin == "/api/aeroports":
            with open(chemins.ressources("aeroports.json"), "rb") as f:
                return self._envoyer(200, f.read(), "application/json; charset=utf-8",
                                     {"Cache-Control": "max-age=86400"})
        if chemin.startswith("/excel/"):
            pid = chemin[len("/excel/"):].strip("/")
            p = next((x for x in P.charger() if x["id"] == pid), None)
            fichier = build.excel(p) if p else None
            if not fichier:
                return self._envoyer(404, "Pas encore de relevé pour ce voyage.".encode("utf-8"), "text/plain; charset=utf-8")
            with open(fichier, "rb") as f:
                return self._envoyer(200, f.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     {"Content-Disposition": f'attachment; filename="{pid}.xlsx"'})
        self._envoyer(404, "Page introuvable.".encode("utf-8"), "text/plain; charset=utf-8")

    def _redirect(self, url):
        self.send_response(303)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        ETAT["derniere_activite"] = time.time()
        # Un autre site ne peut pas envoyer cet en-tête sans autorisation (que ce serveur ne donne jamais).
        if not self._hote_ok() or self.headers.get("X-Trackflight") != "1":
            return self._envoyer(403, {"erreur": "Accès refusé."})
        try:
            n = int(self.headers.get("Content-Length", 0))
            corps = json.loads(self.rfile.read(min(n, 1_000_000)) or b"{}")
        except ValueError:
            return self._envoyer(400, {"erreur": "Requête illisible."})
        chemin = self.path.split("?")[0]

        if chemin == "/api/projets":
            try:
                liste = [nettoyer(p) for p in corps.get("projets", [])]
            except (TypeError, ValueError, AttributeError):
                return self._envoyer(400, {"erreur": "Un champ contient une valeur invalide."})
            erreurs = {p.get("id") or f"nouveau-{i}": P.valider(p) for i, p in enumerate(liste)}
            erreurs = {k: v for k, v in erreurs.items() if v}
            if erreurs:
                return self._envoyer(400, {"erreur": "Certains champs sont à corriger.", "details": erreurs})
            P.enregistrer(liste)
            return self._envoyer(200, {"ok": True, "projets": liste,
                                       "resumes": {p["id"]: build.resume_projet(p) for p in liste}})

        if chemin == "/api/relever":
            with VERROU:
                if releve_actif():
                    return self._envoyer(409, {"erreur": "Une recherche est déjà en cours, patientez."})
                if not navigateur.pret():
                    navigateur.installer_en_fond()
                    return self._envoyer(409, {"erreur": "Préparation du navigateur en cours (première utilisation). Réessayez dans quelques minutes."})
                args = ["--releve"] + (["--projet", str(corps["id"])] if corps.get("id") else [])
                ETAT["proc"] = subprocess.Popen(chemins.commande(*args), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return self._envoyer(200, {"ok": True})

        if chemin == "/api/reglages":
            cfg = releve.config()
            if "serpapi_cle" in corps and str(corps["serpapi_cle"]).strip():
                cfg["serpapi_cle"] = str(corps["serpapi_cle"]).strip()
            if corps.get("effacer_serpapi"):
                cfg["serpapi_cle"] = ""
            if "notifications" in corps:
                cfg["notifications"] = bool(corps["notifications"])
            if "accueil_vu" in corps:
                cfg["accueil_vu"] = bool(corps["accueil_vu"])
            if corps.get("theme") in ("clair", "sombre", "auto"):
                cfg["theme"] = corps["theme"]
            releve.sauver_config(cfg)
            return self._envoyer(200, {"ok": True, "serpapi": bool(cfg["serpapi_cle"]), "notifications": cfg["notifications"]})

        if chemin == "/api/maj":
            if corps.get("installer"):
                if not maj.installer():
                    return self._envoyer(409, {"erreur": "Aucune mise à jour à installer pour le moment."})
                return self._envoyer(200, {"ok": True})
            return self._envoyer(200, maj.verifier(force=True))

        if chemin == "/api/afficher":
            import fenetre
            return self._envoyer(200, {"fenetre": fenetre.montrer()})

        if chemin == "/api/excel":
            p = next((x for x in P.charger() if x["id"] == corps.get("id")), None)
            fichier = build.excel(p) if p else None
            if not fichier:
                return self._envoyer(404, {"erreur": "Pas encore de prix pour ce voyage."})
            dest = vers_telechargements(fichier, p["nom"])
            ouvrir_fichier(dest)
            return self._envoyer(200, {"ok": True, "chemin": dest})

        if chemin == "/api/ouvrir-reglages":
            # Ouvre la page des notifications de l'ordinateur (adresses système fixes, aucune saisie utilisée).
            try:
                if chemins.SYSTEME == "Windows":
                    os.startfile("ms-settings:notifications")
                elif chemins.SYSTEME == "Darwin":
                    r = subprocess.run(["open", "x-apple.systempreferences:com.apple.Notifications-Settings.extension"])
                    if r.returncode:
                        subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.notifications"])
                return self._envoyer(200, {"ok": True})
            except OSError:
                return self._envoyer(500, {"erreur": "Impossible d'ouvrir les réglages."})

        if chemin == "/api/test-notif":
            ok = notif.envoyer("Trackflight", "Les notifications fonctionnent. Vous serez prévenu quand un prix vous intéresse.")
            return self._envoyer(200 if ok else 502, {"ok": ok})

        self._envoyer(404, {"erreur": "Action inconnue."})


def vers_telechargements(fichier, nom):
    import re
    import shutil
    dossier = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(dossier):
        dossier = os.path.expanduser("~")
    base = re.sub(r'[\\/:*?"<>|]+', " ", f"Trackflight - {nom}").strip()
    dest, n = os.path.join(dossier, base + ".xlsx"), 2
    while os.path.exists(dest):
        dest, n = os.path.join(dossier, f"{base} ({n}).xlsx"), n + 1
    shutil.copyfile(fichier, dest)
    return dest


def ouvrir_fichier(chemin):
    try:
        if chemins.SYSTEME == "Windows":
            os.startfile(chemin)
        elif chemins.SYSTEME == "Darwin":
            subprocess.Popen(["open", chemin])
    except OSError:
        pass


def deja_lance():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/ping", timeout=2) as r:
            return json.load(r).get("app") == "trackflight"
    except Exception:
        return False


def surveiller(serveur):
    while True:
        time.sleep(30)
        if time.time() - ETAT["derniere_activite"] > INACTIVITE and not releve_actif():
            serveur.shutdown()
            return


def preparer():
    if os.environ.get("TRACKFLIGHT_SANS_INSTALLATION"):  # tests
        maj.verifier(force=True)
        return
    ok, msg = installation.installer()
    ETAT["installation"] = None if ok else msg
    navigateur.installer_en_fond()
    while True:  # mises à jour : au démarrage, puis toutes les 6 heures tant que l'app est ouverte
        maj.verifier(force=True)
        time.sleep(6 * 3600)


def demarrer(surveiller_inactivite=True):
    """Démarre le serveur dans un fil d'exécution et le renvoie (None si le port est déjà pris)."""
    try:
        serveur = ThreadingHTTPServer(("127.0.0.1", PORT), Gestionnaire)
    except OSError:
        return None
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    threading.Thread(target=preparer, daemon=True).start()
    if surveiller_inactivite:
        threading.Thread(target=surveiller, args=(serveur,), daemon=True).start()
    return serveur


def lancer(ouvrir=True):
    url = f"http://127.0.0.1:{PORT}/"
    if deja_lance():
        if ouvrir:
            webbrowser.open(url)
        return
    try:
        serveur = ThreadingHTTPServer(("127.0.0.1", PORT), Gestionnaire)
    except OSError:
        return  # déjà lancé par ailleurs
    threading.Thread(target=preparer, daemon=True).start()
    threading.Thread(target=surveiller, args=(serveur,), daemon=True).start()
    if ouvrir:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
