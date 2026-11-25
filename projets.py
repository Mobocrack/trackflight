"""Projets de voyage : critères enregistrés (projets.json) et liens de recherche correspondants."""
import base64
import datetime as dt
import json
import os
import re
import unicodedata
import urllib.parse

import chemins

FICHIER = os.path.join(chemins.donnees(), "projets.json")
CLASSES = {"eco": "économique", "premium": "premium", "affaires": "affaires", "premiere": "première"}
ESCALES = {"tous": "peu importe", "1": "1 escale au plus", "direct": "direct seulement"}

MODELE = {
    "id": "", "nom": "", "actif": True,
    "origine": {"code": "", "nom": "", "aeroports": ""},
    "destination": {"code": "", "nom": "", "aeroports": ""},
    "type": "aller",              # "aller" ou "ar"
    "date_aller": "", "flex": 0,  # flex : nombre de jours avant/après (0 à 3)
    "date_retour": "",
    "adultes": 1, "enfants": 0, "bebes": 0,
    "classe": "eco", "escales": "tous", "duree_max_h": None, "billets_separes": False,
    "alertes": {"seuil_escale": None, "seuil_direct": None, "baisse_min": 30,
                "plafond_baisse_escale": None, "plafond_baisse_direct": None,
                "record": True},  # « nouveau meilleur prix » : sous le plus bas jamais vu
}


# ------------------------------------------------------------------ lecture, écriture, contrôles
def slug(nom):
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40] or "projet"


def completer(p):
    """Complète un projet avec les valeurs par défaut (projets créés avec une ancienne version)."""
    q = json.loads(json.dumps(MODELE))
    for k, v in p.items():
        if isinstance(v, dict) and isinstance(q.get(k), dict):
            q[k].update(v)
        else:
            q[k] = v
    return q


PRESETS = [{
    "id": "japon-retour-2027", "nom": "Retour du Japon",
    "origine": {"code": "TYO", "nom": "Tokyo", "aeroports": "HND,NRT"},
    "destination": {"code": "PAR", "nom": "Paris", "aeroports": "CDG,ORY"},
    "type": "aller", "date_aller": "2027-01-28", "flex": 1, "duree_max_h": 21,
    "alertes": {"seuil_escale": 450, "seuil_direct": 1000, "baisse_min": 30,
                "plafond_baisse_escale": 700, "plafond_baisse_direct": 1200},
}]


def charger():
    if not os.path.exists(FICHIER):
        # Premier lancement : voyages déjà préparés (seulement si leur date n'est pas passée).
        depart = [completer(p) for p in PRESETS if p["date_aller"] >= dt.date.today().isoformat()]
        enregistrer(depart)
        return depart
    with open(FICHIER, encoding="utf-8") as f:
        return [completer(p) for p in json.load(f).get("projets", [])]


def valider(p):
    """Renvoie la liste des problèmes d'un projet (vide si tout va bien)."""
    err = []
    if not p["nom"].strip():
        err.append("Donnez un nom au projet.")
    for cote, lib in (("origine", "départ"), ("destination", "arrivée")):
        if not re.fullmatch(r"[A-Z]{3}", p[cote]["code"] or ""):
            err.append(f"Choisissez une ville de {lib} (ou un code d'aéroport à 3 lettres).")
    if p["origine"]["code"] and p["origine"]["code"] == p["destination"]["code"]:
        err.append("Le départ et l'arrivée sont identiques.")
    try:
        da = dt.date.fromisoformat(p["date_aller"])
    except (TypeError, ValueError):
        err.append("Indiquez la date de l'aller.")
        da = None
    if p["type"] == "ar":
        try:
            dr = dt.date.fromisoformat(p["date_retour"])
            if da and dr < da:
                err.append("La date de retour est avant la date d'aller.")
        except (TypeError, ValueError):
            err.append("Indiquez la date du retour.")
    if not 1 <= p["adultes"] <= 9 or p["adultes"] + p["enfants"] + p["bebes"] > 9:
        err.append("Il faut entre 1 et 9 passagers, dont au moins 1 adulte.")
    if p["bebes"] > p["adultes"]:
        err.append("Il faut un adulte par bébé.")
    if not 0 <= int(p["flex"]) <= 3:
        err.append("La souplesse sur les dates va de 0 à 3 jours.")
    return err


def enregistrer(liste):
    ids = set()
    for p in liste:
        if not p.get("id"):
            p["id"] = slug(p["nom"])
        base, n = p["id"], 2
        while p["id"] in ids:
            p["id"], n = f"{base}-{n}", n + 1
        ids.add(p["id"])
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"projets": liste}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, FICHIER)


def dossier(p):
    d = os.path.join(chemins.donnees(), "voyages", p["id"])
    os.makedirs(d, exist_ok=True)
    return d


# ------------------------------------------------------------------ dates et descriptions
def dates_aller(p):
    """Dates d'aller à relever (date ± souplesse), sans les dates déjà passées."""
    d0, auj = dt.date.fromisoformat(p["date_aller"]), dt.date.today()
    k = int(p["flex"])
    return [str(d) for d in (d0 + dt.timedelta(days=i) for i in range(-k, k + 1)) if d >= auj]


def retour_pour(p, date_aller):
    """Pour un aller-retour, le retour se décale avec l'aller pour garder la même durée de séjour."""
    if p["type"] != "ar":
        return None
    decal = dt.date.fromisoformat(date_aller) - dt.date.fromisoformat(p["date_aller"])
    return str(dt.date.fromisoformat(p["date_retour"]) + decal)


def passagers_txt(p):
    parts = [f"{p['adultes']} adulte{'s' if p['adultes'] > 1 else ''}"]
    if p["enfants"]:
        parts.append(f"{p['enfants']} enfant{'s' if p['enfants'] > 1 else ''}")
    if p["bebes"]:
        parts.append(f"{p['bebes']} bébé{'s' if p['bebes'] > 1 else ''}")
    return ", ".join(parts)


def nb_passagers(p):
    return p["adultes"] + p["enfants"] + p["bebes"]


def date_txt(d, annee=True):
    mois = "janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.".split()
    x = dt.date.fromisoformat(d)
    return f"{x.day} {mois[x.month - 1]}" + (f" {x.year}" if annee else "")


def resume(p):
    morceaux = ["Aller-retour" if p["type"] == "ar" else "Aller simple"]
    d = date_txt(p["date_aller"])
    if p["type"] == "ar":
        d = f"{date_txt(p['date_aller'], False)} → {date_txt(p['date_retour'])}"
    if int(p["flex"]):
        d += f" (± {p['flex']} j)"
    morceaux += [d, passagers_txt(p), CLASSES[p["classe"]]]
    if p["escales"] != "tous":
        morceaux.append(ESCALES[p["escales"]])
    if p["duree_max_h"]:
        morceaux.append(f"{p['duree_max_h']:g} h max")
    return " · ".join(morceaux)


# ------------------------------------------------------------------ liens de recherche
def _chemin_kayak(p, date):
    r = retour_pour(p, date)
    morceaux = [f"{p['origine']['code']}-{p['destination']['code']}", date] + ([r] if r else [])
    if p["classe"] != "eco":
        morceaux.append({"premium": "premium", "affaires": "business", "premiere": "first"}[p["classe"]])
    enfants = ["8"] * p["enfants"] + ["1L"] * p["bebes"]
    if p["adultes"] > 1 or enfants:
        morceaux.append(f"{p['adultes']}adults")
    if enfants:
        morceaux.append("children-" + "-".join(enfants))
    filtres = []
    if p["escales"] == "direct":
        filtres.append("stops=0")
    if p["duree_max_h"]:
        filtres.append(f"legdur=-{int(float(p['duree_max_h']) * 60)}")
    q = "?sort=price_a" + ("&fs=" + ";".join(filtres) if filtres else "")
    return "/".join(morceaux) + q


def url_kayak(p, date):
    return "https://www.kayak.fr/flights/" + _chemin_kayak(p, date)


def url_momondo(p, date):
    return "https://www.momondo.fr/flight-search/" + _chemin_kayak(p, date)


def _varint(n):
    out = b""
    while True:
        b, n = n & 0x7F, n >> 7
        if n:
            out += bytes([b | 0x80])
        else:
            return out + bytes([b])


def _champ(num, val):
    if isinstance(val, int):
        return _varint(num << 3) + _varint(val)
    if isinstance(val, str):
        val = val.encode()
    return _varint(num << 3 | 2) + _varint(len(val)) + val


def url_google(p, date):
    """URL Google Flights (paramètre tfs encodé comme le fait le site) : à ouvrir à la main."""
    def trajet(d, de, vers):
        b = _champ(2, d)
        if p["escales"] != "tous":
            b += _champ(5, 0 if p["escales"] == "direct" else 1)
        return b + _champ(13, _champ(2, de)) + _champ(14, _champ(2, vers))
    o, d = p["origine"]["code"], p["destination"]["code"]
    info = _champ(3, trajet(date, o, d))
    r = retour_pour(p, date)
    if r:
        info += _champ(3, trajet(r, d, o))
    for _ in range(p["adultes"]):
        info += _champ(8, 1)
    for _ in range(p["enfants"]):
        info += _champ(8, 2)
    for _ in range(p["bebes"]):
        info += _champ(8, 4)
    info += _champ(9, {"eco": 1, "premium": 2, "affaires": 3, "premiere": 4}[p["classe"]])
    info += _champ(19, 1 if r else 2)
    tfs = urllib.parse.quote(base64.b64encode(info).decode())
    return f"https://www.google.com/travel/flights/search?tfs={tfs}&hl=fr&gl=FR&curr=EUR"


def params_serpapi(p, date, cle):
    r = retour_pour(p, date)
    q = dict(engine="google_flights",
             departure_id=p["origine"]["aeroports"] or p["origine"]["code"],
             arrival_id=p["destination"]["aeroports"] or p["destination"]["code"],
             outbound_date=date, type="1" if r else "2", currency="EUR", hl="fr", gl="fr",
             adults=str(p["adultes"]), children=str(p["enfants"]), infants_on_lap=str(p["bebes"]),
             travel_class={"eco": "1", "premium": "2", "affaires": "3", "premiere": "4"}[p["classe"]],
             stops={"tous": "0", "direct": "1", "1": "2"}[p["escales"]], api_key=cle)
    if r:
        q["return_date"] = r
    return q


def liens(p):
    """Liens « chercher soi-même » affichés sur la page du projet."""
    out = []
    for d in dates_aller(p) or [p["date_aller"]]:
        j = date_txt(d, False)
        out += [(f"Google Flights {j}", url_google(p, d)), (f"Kayak {j}", url_kayak(p, d)), (f"Momondo {j}", url_momondo(p, d))]
    return out


def garde(p, v):
    """Le vol respecte-t-il les critères du projet ?"""
    trajets = [v] + ([v["retour"]] if v.get("retour") else [])
    if p["duree_max_h"] and any(t["duree"] > float(p["duree_max_h"]) * 60 for t in trajets):
        return False
    if p["escales"] == "direct" and any(t["escales"] for t in trajets):
        return False
    if p["escales"] == "1" and any(t["escales"] > 1 for t in trajets):
        return False
    if v["autonome"] and not p["billets_separes"]:
        return False
    return True
