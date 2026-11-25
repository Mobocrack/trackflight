"""Lecture des pages de résultats Kayak / Momondo (même moteur), aller simple ou aller-retour."""
import re

RX_TRAJET = re.compile(
    r"(\d\d:\d\d)\s*\S\s*(\d\d:\d\d)(\+\d)?\n"      # horaires
    r"([A-Z]{3})[^\n]*\n-\n([A-Z]{3})[^\n]*\n"       # aéroports
    r"(direct|\d escales?)\n"                         # escales
    r"(.*?)"                                          # détail des escales
    r"(\d+)h (\d+)min\n",                             # durée du trajet
    re.S)
RX_PRIX = re.compile(r"\n(\d[\d\u202f\xa0 ]*)\xa0?€\n")
RX_TOTAL = re.compile(r"(\d[\d\u202f\xa0 ]*)\xa0?€ au total")
RX_VIA = re.compile(r"^\s*([A-Z]{3})\s*$", re.M)
RX_ESCALE = re.compile(r"Escale de (\d+)h (\d+)min")
SEPARATEUR = "Aller aux détails du résultat\n"


def _nombre(s):
    return int(re.sub(r"\D", "", s))


def _trajet(m):
    detail = m.group(7)
    return dict(
        depart=m.group(1),
        arrivee=m.group(2) + (f" {m.group(3)}" if m.group(3) else ""),
        aeroports=f"{m.group(4)}-{m.group(5)}",
        escales=0 if m.group(6) == "direct" else int(m.group(6)[0]),
        via=", ".join(RX_VIA.findall(detail)),
        escale_detail=" / ".join(f"{h} h {int(mi):02d}" for h, mi in RX_ESCALE.findall(detail)),
        duree=int(m.group(8)) * 60 + int(m.group(9)),
    )


def lire(texte, date, date_retour=None):
    """Renvoie une liste de vols. Pour un aller-retour, le trajet retour est dans v["retour"].
    v["prix"] est le prix par personne, v["prix_total"] celui de tous les passagers."""
    vols = []
    for bloc in texte.split(SEPARATEUR)[1:]:
        trajets = list(RX_TRAJET.finditer(bloc))
        attendus = 2 if date_retour else 1
        if len(trajets) < attendus:
            continue
        trajets = trajets[:attendus]
        fin = trajets[-1].end()
        compagnie = bloc[fin:].split("\n", 1)[0].strip()
        mp = RX_PRIX.search(bloc, fin - 1)
        if not mp or not compagnie:
            continue
        prix = _nombre(mp.group(1))
        mt = RX_TOTAL.search(bloc, mp.start())
        aller = _trajet(trajets[0])
        v = dict(date=date, compagnie=compagnie, **aller, prix=prix,
                 prix_total=_nombre(mt.group(1)) if mt and mt.start() - mp.end() < 40 else prix,
                 autonome="correspondance autonome" in bloc.lower(), retour=None)
        if date_retour:
            v["retour"] = dict(date=date_retour, **_trajet(trajets[1]))
        vols.append(v)
    return vols
