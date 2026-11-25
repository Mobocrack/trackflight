"""Relevé des prix pour chaque voyage actif, historique et notifications.

Sources : Kayak et Momondo (navigateur sans interface, sans camouflage) ; Google Flights en option
avec une clé SerpApi personnelle (offre gratuite) saisie dans les réglages.
"""
import csv
import datetime as dt
import json
import logging
import os
import time
import urllib.parse
import urllib.request

import chemins
import lecteur
import navigateur
import notif
import projets as P

DONNEES = chemins.donnees()
CONFIG = os.path.join(DONNEES, "config.json")
ETAT = os.path.join(DONNEES, "etat.json")
VERROU = os.path.join(DONNEES, "releve.lock")
PROGRESSION = os.path.join(DONNEES, "progression.json")

logging.basicConfig(filename=os.path.join(DONNEES, "journal.log"), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8")
log = logging.getLogger("trackflight")

DEFAUT = {
    "sources": ["kayak", "momondo", "google"],
    "notifications": True,
    "theme": "clair",
    "accueil_vu": False,        # tutoriel de premier lancement déjà vu           # clair (par défaut), sombre ou auto (suit l'ordinateur)
    "serpapi_cle": "",          # clé gratuite sur serpapi.com (Google Flights), vide = Google ignoré
    "serpapi_max_mois": 120,
    "google_seul": False,
}
COLONNES = ["releve", "source", "date", "compagnie", "depart", "arrivee", "aeroports", "duree_min", "escales", "via",
            "autonome", "prix", "date_retour", "retour_depart", "retour_arrivee", "retour_duree_min", "retour_escales",
            "prix_total"]


def lire_json(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def ecrire_json(chemin, donnees):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)


def config():
    cfg = dict(DEFAUT)
    cfg.update({k: v for k, v in lire_json(CONFIG, {}).items() if k in DEFAUT})
    return cfg


def sauver_config(cfg):
    ecrire_json(CONFIG, {k: cfg[k] for k in DEFAUT})


# ------------------------------------------------------------------ sources
NAVIGATEUR = {"kayak": ("Kayak", P.url_kayak), "momondo": ("Momondo", P.url_momondo)}


def sources_navigateur(cfg):
    return [] if cfg["google_seul"] else [k for k in cfg["sources"] if k in NAVIGATEUR]


BLOCAGE = ("pense que vous êtes un « robot »", "page que vous vouliez consulter est à l'usage exclusif des humains",
           "Qu'est-ce qu'un robot ?")


BLOQUES = set()  # sites qui ont affiché leur page anti-robot pendant ce relevé


def bloque(page, texte):
    """Le site a affiché sa page anti-robot : on s'arrête là pour ce site (aucun contournement, jamais)."""
    return any(m in texte for m in BLOCAGE) or "robot" in (page.title() or "").lower()


def relever_navigateur(cfg, liste):
    sources = sources_navigateur(cfg)
    res = {p["id"]: [] for p in liste}
    if not sources or not liste:
        return res
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = navigateur.lancer(pw)
        ctx = nav.new_context(locale="fr-FR", viewport={"width": 1366, "height": 900})
        total = sum(len(P.dates_aller(p)) for p in liste) * len(sources)
        fait = 0
        for p in liste:
            for src in sources:
                nom, url_de = NAVIGATEUR[src]
                for date in P.dates_aller(p):
                    if src in BLOQUES:
                        fait += 1
                        continue
                    page, url, retour = ctx.new_page(), url_de(p, date), P.retour_pour(p, date)
                    ecrire_json(PROGRESSION, {"projet": p["id"], "fait": fait, "total": total,
                                              "texte": f"{nom}, {P.date_txt(date, False)}"})
                    fait += 1
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        vols, stable = [], 0
                        for _ in range(14):  # jusqu'à ~42 s : on attend que la liste se stabilise
                            page.wait_for_timeout(3000)
                            texte = page.inner_text("body")
                            if bloque(page, texte):
                                BLOQUES.add(src)
                                log.warning("[%s] %s refuse la recherche automatique (page anti-robot) : site ignoré pour ce relevé",
                                            p["id"], nom)
                                break
                            n = lecteur.lire(texte, date, retour)
                            stable = stable + 1 if n and len(n) == len(vols) else 0
                            vols = n
                            if stable >= 2:
                                break
                        for v in vols:
                            v["source"], v["lien"] = nom, url
                        log.info("[%s] %s %s : %d vols lus", p["id"], nom, date, len(vols))
                        res[p["id"]] += vols
                    except Exception as e:
                        log.exception("[%s] échec %s %s : %s", p["id"], nom, date, e)
                    finally:
                        page.close()
        nav.close()
    return res


def https_json(url):
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=60, context=ctx) as r:
        return json.load(r)


def _trajet_serpapi(segs, escales):
    dep, arr = segs[0]["departure_airport"], segs[-1]["arrival_airport"]
    jours = (dt.date.fromisoformat(arr["time"][:10]) - dt.date.fromisoformat(dep["time"][:10])).days
    return dict(depart=dep["time"][11:16], arrivee=arr["time"][11:16] + (f" +{jours}" if jours else ""),
                aeroports=f"{dep['id']}-{arr['id']}", escales=len(escales),
                via=", ".join(l.get("id", "") for l in escales),
                escale_detail=" / ".join(f"{l['duration'] // 60} h {l['duration'] % 60:02d}"
                                         for l in escales if l.get("duration")))


ERREURS_GOOGLE = []  # raisons données par SerpApi pendant ce relevé (affichées dans l'app)


def _raison_serpapi(e):
    """SerpApi explique ses refus dans le corps de la réponse (JSON « error ») : on garde ce texte, pas seulement le code HTTP."""
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        try:
            return json.loads(e.read().decode("utf-8", "replace")).get("error") or f"erreur HTTP {e.code}"
        except (OSError, ValueError, AttributeError):
            return f"erreur HTTP {e.code}"
    return str(e)


def relever_google(cfg, etat, p):
    if not (cfg["google_seul"] or "google" in cfg["sources"]) or not cfg["serpapi_cle"]:
        return []
    mois = dt.date.today().strftime("%Y-%m")
    quota = etat.setdefault("serpapi", {})
    if quota.get("mois") != mois:
        quota.update(mois=mois, n=0)
    tous, n_pass = [], P.nb_passagers(p)
    for date in P.dates_aller(p):
        if quota["n"] >= cfg["serpapi_max_mois"]:
            log.warning("SerpApi : quota mensuel atteint (%s)", quota["n"])
            break
        try:
            d = https_json("https://serpapi.com/search.json?" + urllib.parse.urlencode(P.params_serpapi(p, date, cfg["serpapi_cle"])))
            quota["n"] += 1
        except Exception as e:
            raison = _raison_serpapi(e)
            log.error("[%s] Google Flights %s : %s", p["id"], date, raison)
            ERREURS_GOOGLE.append(raison)
            continue
        if d.get("error"):
            log.error("[%s] Google Flights %s : %s", p["id"], date, d["error"])
            ERREURS_GOOGLE.append(d["error"])
            continue
        log.info("[%s] Google Flights %s : %d vols lus", p["id"], date,
                 len(d.get("best_flights", [])) + len(d.get("other_flights", [])))
        lien = d.get("search_metadata", {}).get("google_flights_url") or P.url_google(p, date)
        for f in d.get("best_flights", []) + d.get("other_flights", []):
            segs, esc = f.get("flights") or [], f.get("layovers") or []
            if not segs or not f.get("price"):
                continue
            cies = []
            for sg in segs:
                if sg.get("airline") and sg["airline"] not in cies:
                    cies.append(sg["airline"])
            brut = json.dumps(f).lower()
            total = int(f["price"])
            tous.append(dict(date=date, compagnie=", ".join(cies), **_trajet_serpapi(segs, esc),
                             duree=int(f.get("total_duration", 0)), prix=round(total / n_pass), prix_total=total,
                             autonome="self_transfer" in brut or "self-transfer" in brut, retour=None,
                             source="Google Flights", lien=lien))
    return tous


# ------------------------------------------------------------------ alertes
def cle(v):
    r = v.get("retour") or {}
    return f"{v['date']} {v['depart']} {v['compagnie']} {r.get('depart', '')}".strip()


def alertes(cfg, p, tous, etat):
    a = p["alertes"]
    meilleurs = {}
    for v in tous:
        if not P.garde(p, v):
            continue
        k = cle(v)
        if k not in meilleurs or v["prix"] < meilleurs[k]["prix"]:
            meilleurs[k] = v
    prec, deja = etat.get("prix", {}), etat.get("alertes", {})
    lignes = []
    for k, v in sorted(meilleurs.items(), key=lambda kv: kv[1]["prix"]):
        direct = v["escales"] == 0 and not (v.get("retour") or {}).get("escales")
        seuil = a["seuil_direct"] if direct else a["seuil_escale"]
        plafond = a["plafond_baisse_direct"] if direct else a["plafond_baisse_escale"]
        raison = None
        if seuil and v["prix"] < seuil and v["prix"] < deja.get(k, 10 ** 9):
            raison = f"sous {seuil} €"
        elif (a["baisse_min"] and k in prec and prec[k] - v["prix"] >= a["baisse_min"]
              and (plafond is None or v["prix"] <= plafond)):
            raison = f"baisse de {prec[k] - v['prix']} €"
        if raison:
            deja[k] = v["prix"]
            lignes.append(f"{v['prix']} € {v['compagnie']}, {P.date_txt(v['date'], False)} à {v['depart']} ({raison})")
    etat["alertes"] = deja
    etat["prix"] = {k: v["prix"] for k, v in meilleurs.items()}
    if lignes and cfg["notifications"]:
        titre = f"{p['nom']} : {len(lignes)} bon{'s' if len(lignes) > 1 else ''} prix"
        notif.envoyer(titre, "\n".join(lignes[:4]) + ("\n…" if len(lignes) > 4 else ""))
    return lignes


# ------------------------------------------------------------------ enregistrement
def enregistrer(p, vols, maintenant):
    d = P.dossier(p)
    h = os.path.join(d, "historique.csv")
    nouveau = not os.path.exists(h)
    with open(h, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if nouveau:
            w.writerow(COLONNES)
        for v in vols:
            r = v.get("retour") or {}
            w.writerow([maintenant, v["source"], v["date"], v["compagnie"], v["depart"], v["arrivee"],
                        v["aeroports"], v["duree"], v["escales"], v["via"], int(v["autonome"]), v["prix"],
                        r.get("date", ""), r.get("depart", ""), r.get("arrivee", ""), r.get("duree", ""),
                        r.get("escales", ""), v.get("prix_total", v["prix"])])
    srcs = ", ".join(sorted({v["source"] for v in vols}))
    ecrire_json(os.path.join(d, "derniers.json"), {"releve": maintenant, "sources": srcs, "vols": vols})


def prendre_verrou(attente_max=45 * 60):
    debut = time.time()
    while True:
        try:
            fd = os.open(VERROU, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(VERROU) > 45 * 60:
                    os.remove(VERROU)
                    continue
            except OSError:
                continue
            if time.time() - debut > attente_max:
                return False
            time.sleep(10)


def en_cours():
    try:
        return time.time() - os.path.getmtime(VERROU) < 45 * 60
    except OSError:
        return False


def executer(projet=None, si_besoin=False):
    """Relève les voyages actifs (ou un seul). si_besoin : seulement si le dernier relevé a plus de 20 h."""
    etat = lire_json(ETAT, {})
    if si_besoin and time.time() - etat.get("dernier_releve", 0) < 20 * 3600:
        return
    if not prendre_verrou():
        log.error("relevé abandonné : un autre relevé est bloqué")
        return
    try:
        cfg = config()
        liste = P.charger()
        actifs = [p for p in liste if (p["id"] == projet if projet else p["actif"]) and not P.valider(p) and P.dates_aller(p)]
        maintenant = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
        log.info("relevé lancé : %s", ", ".join(p["id"] for p in actifs) or "aucun voyage actif")
        nav_ok = True
        try:
            res = relever_navigateur(cfg, actifs)
        except Exception as e:  # navigateur introuvable ou impossible à ouvrir : on le dit au lieu de s'arrêter en silence
            log.exception("relevé impossible : le navigateur de recherche n'a pas pu s'ouvrir")
            ecrire_json(os.path.join(DONNEES, "derniere_erreur.json"),
                        {"quand": maintenant, "message": f"Le navigateur de recherche n'a pas pu s'ouvrir ({str(e)[:200]})."})
            res, nav_ok = {p["id"]: [] for p in actifs}, False
        total, sans_prix = 0, []
        for p in actifs:
            avant = len(ERREURS_GOOGLE)
            vols = res[p["id"]] + relever_google(cfg, etat, p)
            total += len(vols)
            if not vols:
                log.error("[%s] aucun vol lu", p["id"])
                raison = ERREURS_GOOGLE[-1] if len(ERREURS_GOOGLE) > avant else ""
                sans_prix.append(f"{p.get('nom') or p['id']}" + (f" : « {raison[:160]} »" if raison else ""))
                continue
            enregistrer(p, vols, maintenant)
            etat_p = lire_json(os.path.join(P.dossier(p), "etat.json"), {})
            n = alertes(cfg, p, vols, etat_p)
            ecrire_json(os.path.join(P.dossier(p), "etat.json"), etat_p)
            log.info("[%s] %d vols, %d alertes", p["id"], len(vols), len(n))
        if actifs and not total and nav_ok:
            if cfg["google_seul"] and ERREURS_GOOGLE:
                message = f"Google Flights a répondu : « {ERREURS_GOOGLE[-1][:200]} ». Détail dans Réglages > Journal."
            elif cfg["google_seul"]:
                message = "Google Flights n’a renvoyé aucun prix. Vérifiez votre clé SerpApi, le quota et les dates du voyage."
            elif BLOQUES:
                noms = " et ".join(NAVIGATEUR[k][0] for k in sorted(BLOQUES))
                message = (f"{noms} refuse{'nt' if len(BLOQUES) > 1 else ''} la recherche automatique. "
                           "Vous pouvez utiliser Google Flights via SerpApi dans les réglages.")
            else:
                message = "Aucun prix trouvé. Vérifiez les dates du voyage ou ouvrez un lien de recherche manuelle."
            ecrire_json(os.path.join(DONNEES, "derniere_erreur.json"),
                        {"quand": maintenant, "message": message})
        if actifs and not total and cfg["notifications"]:
            notif.envoyer("Trackflight : recherche impossible",
                          "Ouvrez Trackflight pour voir le détail de la dernière recherche.")
        if total and sans_prix:  # certains voyages ont des prix, d'autres non : on dit lesquels et pourquoi
            ecrire_json(os.path.join(DONNEES, "derniere_erreur.json"),
                        {"quand": maintenant, "message": "Aucun prix pour " + " ; ".join(sans_prix)
                         + ". Détail dans Réglages > Journal."})
        elif total:
            try:
                os.remove(os.path.join(DONNEES, "derniere_erreur.json"))
            except OSError:
                pass
        if not projet:
            etat["dernier_releve"] = time.time()
        ecrire_json(ETAT, etat)
    finally:
        for f in (VERROU, PROGRESSION):
            try:
                os.remove(f)
            except OSError:
                pass
