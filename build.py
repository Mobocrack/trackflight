"""Pages de l'application (accueil, voyage) et export Excel, à partir des relevés enregistrés."""
import csv
import json
import os

import chemins
import projets as P

COMPAGNIES = {
    "Air China": "https://www.airchina.com.cn/", "Qatar Airways": "https://www.qatarairways.com/",
    "Air France": "https://wwws.airfrance.fr/", "ANA": "https://www.ana.co.jp/", "JAL": "https://www.jal.co.jp/",
    "Japan Airlines": "https://www.jal.co.jp/", "China Eastern": "https://www.ceair.com/",
    "Turkish Airlines": "https://www.turkishairlines.com/", "Korean Air": "https://www.koreanair.com/",
    "Vietnam Airlines": "https://www.vietnamairlines.com/", "Emirates": "https://www.emirates.com/",
    "Etihad": "https://www.etihad.com/", "Cathay Pacific": "https://www.cathaypacific.com/",
    "British Airways": "https://www.britishairways.com/", "SWISS": "https://www.swiss.com/",
    "Lufthansa": "https://www.lufthansa.com/", "KLM": "https://www.klm.fr/", "TAP": "https://www.flytap.com/",
    "Transavia": "https://www.transavia.com/", "easyJet": "https://www.easyjet.com/", "Iberia": "https://www.iberia.com/",
    "Vueling": "https://www.vueling.com/", "Ryanair": "https://www.ryanair.com/", "Finnair": "https://www.finnair.com/",
}


def lien_compagnie(nom):
    for k, v in COMPAGNIES.items():
        if nom.lower().startswith(k.lower()):
            return v
    return ""


def fmt_duree(m):
    return f"{m // 60} h {m % 60:02d}"


def lire_json(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def derniers(p):
    return lire_json(os.path.join(P.dossier(p), "derniers.json"), None)


# Escales qui demandent une autorisation de voyage, même en simple correspondance (pour un passeport français).
# Montants vérifiés en novembre 2026 ; ils changent : l'app renvoie toujours au site officiel.
FORMALITES = {
    "US": {"court": "ESTA requis", "long": "Escale aux États-Unis : ESTA obligatoire, même en correspondance (environ 40 $ par personne)"},
    "CA": {"court": "AVE Canada requise", "long": "Escale au Canada : AVE (eTA) obligatoire (7 $ CA par personne)"},
    "GB": {"court": "ETA Royaume-Uni", "long": "Escale au Royaume-Uni : ETA souvent exigée, même en correspondance (20 £ par personne)"},
}
_PAYS = None


def pays_aeroport(code):
    global _PAYS
    if _PAYS is None:
        try:
            with open(chemins.ressources("aeroports.json"), encoding="utf-8") as f:
                _PAYS = {a["c"]: a["p"] for a in json.load(f)["aeroports"]}
        except (OSError, ValueError, KeyError):
            _PAYS = {}
    return _PAYS.get(code.strip().upper())


def formalites(v):
    """Autorisations nécessaires pour les escales du vol (aller et retour)."""
    codes = [c for t in (v, v.get("retour") or {}) for c in str(t.get("via") or "").split(",") if c.strip()]
    pays = []
    for c in codes:
        p = pays_aeroport(c)
        if p in FORMALITES and p not in pays:
            pays.append(p)
    return [FORMALITES[p] for p in pays]


def consolider(p, vols):
    """Un vol = même date, mêmes horaires, mêmes escales (et même retour). On garde le meilleur prix."""
    out = {}
    for v in vols:
        r = v.get("retour") or {}
        k = (v["date"], v["depart"], v["arrivee"], v["via"], r.get("depart"), r.get("arrivee"))
        obs = {"source": v.get("source", "Kayak"), "prix": v["prix"], "lien": v.get("lien") or P.url_kayak(p, v["date"])}
        cur = out.get(k)
        if cur is None:
            cur = out[k] = dict(v, retour=v.get("retour"), obs=[])
        elif len(v["compagnie"]) > len(cur["compagnie"]):
            cur["compagnie"] = v["compagnie"]
        cur["obs"].append(obs)
    res = []
    for v in out.values():
        v["formalites"] = formalites(v)
        best = min(v["obs"], key=lambda o: o["prix"])
        v.update(prix=best["prix"], source=best["source"], lien=best["lien"],
                 prix_max=max(o["prix"] for o in v["obs"]), site=lien_compagnie(v["compagnie"]),
                 ok=P.garde(p, v), prix_total=v.get("prix_total", v["prix"]))
        res.append(v)
    res.sort(key=lambda v: (not v["ok"], v["prix"]))
    return res


def historique(p):
    h = os.path.join(P.dossier(p), "historique.csv")
    if not os.path.exists(h):
        return []
    par = {}
    with open(h, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            try:
                v = {"duree": int(r["duree_min"]), "escales": int(r["escales"]), "autonome": r["autonome"] == "1",
                     "retour": None}
                if r.get("retour_duree_min"):
                    v["retour"] = {"duree": int(r["retour_duree_min"]), "escales": int(r["retour_escales"] or 0)}
                prix = int(r["prix"])
            except (TypeError, ValueError, KeyError):
                continue
            if not P.garde(p, v):
                continue
            e = par.setdefault(r["releve"], {"escale": None, "direct": None})
            k = "direct" if v["escales"] == 0 and not (v["retour"] or {}).get("escales") else "escale"
            if e[k] is None or prix < e[k][0]:
                e[k] = (prix, r["compagnie"])
    return [dict(releve=k, machine="", escale=v["escale"], direct=v["direct"]) for k, v in par.items()]


def _injecter(modele, donnees):
    with open(chemins.ressources(modele), encoding="utf-8") as f:
        tpl = f.read()
    return tpl.replace("/*__DATA__*/null", json.dumps(donnees, ensure_ascii=False).replace("</", "<\\/"))


def _projet_public(p):
    return {"id": p["id"], "nom": p["nom"], "actif": p["actif"], "type": p["type"],
            "origine": p["origine"], "destination": p["destination"], "resume": P.resume(p),
            "date_aller": p["date_aller"], "date_retour": p["date_retour"],
            "duree_max_h": p["duree_max_h"], "passagers": P.nb_passagers(p), "passagers_txt": P.passagers_txt(p)}


def donnees_voyage(p):
    """Tout ce que l'interface affiche pour un voyage (None s'il n'a pas encore été relevé)."""
    d = derniers(p)
    if not d:
        return None
    champs = ("date", "compagnie", "depart", "arrivee", "aeroports", "duree", "escales", "via", "escale_detail",
              "prix", "prix_total", "prix_max", "source", "lien", "site", "autonome", "ok", "retour", "obs",
              "formalites", "logo")
    vols = consolider(p, d["vols"])
    return {"projet": _projet_public(p), "releve": d["releve"], "sources": d.get("sources", "Kayak"),
            "histo": historique(p), "vols": [{k: v.get(k) for k in champs} for v in vols], "liens": P.liens(p),
            "repere": repere_google(p)}


def repere_google(p):
    """Repère de Google Flights enregistré au dernier relevé (None s'il n'y en a pas)."""
    try:
        with open(os.path.join(P.dossier(p), "google_repere.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def resume_projet(p):
    d = derniers(p)
    info = _projet_public(p)
    if d:
        ok = [v for v in consolider(p, d["vols"]) if v["ok"]]
        if ok:
            b = min(ok, key=lambda v: v["prix"])
            info["meilleur"] = {k: b[k] for k in ("prix", "prix_total", "compagnie", "date", "duree", "escales", "via")}
        info["releve"] = d["releve"]
    return info





# ---------------------------------------------------------------- Excel
def excel(p):
    """Fabrique le fichier Excel d'un voyage et renvoie son chemin (None sans relevé)."""
    from openpyxl import Workbook  # chargé seulement à l'export : l'application démarre plus vite
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    BLEU = "0F1B2D"
    F_ENTETE = Font(bold=True, color="FFFFFF")
    P_ENTETE = PatternFill("solid", fgColor=BLEU)
    P_VERT = PatternFill("solid", fgColor="E4F3EA")
    LIEN = Font(color="1F4FBF", underline="single")
    BORD = Border(bottom=Side(style="thin", color="DCE1E9"))
    d = derniers(p)
    if not d:
        return None
    vols = consolider(p, d["vols"])
    wb = Workbook()
    ws = wb.active
    ws.title = "Vols"
    ws["A1"] = f"{p['nom']} : {p['origine']['nom'] or p['origine']['code']} → {p['destination']['nom'] or p['destination']['code']}"
    ws["A1"].font = Font(bold=True, size=14, color=BLEU)
    ws["A2"] = f"{P.resume(p)}. Relevé du {d['releve']} ({d.get('sources', '')}). Vert = respecte vos critères. Prix par personne."
    ws["A2"].font = Font(italic=True, color="5B6779")
    ar = p["type"] == "ar"
    titres = ["Aller", "Compagnie", "Départ", "Arrivée", "Aéroports", "Durée", "Escales", "Via"]
    larg = [12, 28, 9, 11, 11, 9, 8, 12]
    if ar:
        titres += ["Retour", "Départ", "Arrivée", "Durée", "Escales"]
        larg += [12, 9, 11, 9, 8]
    titres += ["Prix / pers. (€)", "Total (€)", "Source", "Rechercher", "Site compagnie"]
    larg += [14, 11, 16, 12, 15]
    for i, (t, w) in enumerate(zip(titres, larg), 1):
        c = ws.cell(row=4, column=i, value=t)
        c.font, c.fill = F_ENTETE, P_ENTETE
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = w
    for r, v in enumerate(vols, 5):
        vals = [v["date"], v["compagnie"], v["depart"], v["arrivee"], v["aeroports"], fmt_duree(v["duree"]),
                v["escales"], v["via"] or "direct"]
        if ar:
            rt = v.get("retour") or {}
            vals += [rt.get("date", ""), rt.get("depart", ""), rt.get("arrivee", ""),
                     fmt_duree(rt["duree"]) if rt.get("duree") else "", rt.get("escales", "")]
        vals += [v["prix"], v["prix_total"], v["source"]]
        for i, x in enumerate(vals, 1):
            c = ws.cell(row=r, column=i, value=x)
            c.border = BORD
            if v["ok"]:
                c.fill = P_VERT
        for col, url, txt in ((len(vals) + 1, v["lien"], "Ouvrir"), (len(vals) + 2, v["site"], "Site officiel")):
            if url:
                c = ws.cell(row=r, column=col, value=txt)
                c.hyperlink, c.font = url, LIEN
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(titres))}{max(5, len(vols) + 4)}"
    ws = wb.create_sheet("Historique")
    for i, t in enumerate(["Relevé", "Meilleur avec escale (€)", "Compagnie", "Meilleur direct (€)", "Compagnie"], 1):
        c = ws.cell(row=1, column=i, value=t)
        c.font, c.fill = F_ENTETE, P_ENTETE
        ws.column_dimensions[get_column_letter(i)].width = 22
    for r, hh in enumerate(historique(p), 2):
        for i, x in enumerate([hh["releve"], *(hh["escale"] or ("", "")), *(hh["direct"] or ("", ""))], 1):
            ws.cell(row=r, column=i, value=x)
    chemin = os.path.join(P.dossier(p), f"{p['id']}.xlsx")
    wb.save(chemin)
    return chemin
