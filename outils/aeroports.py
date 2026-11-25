"""Construit ressources/aeroports.json à partir de la base OurAirports (domaine public, ourairports.com).

Garde les aéroports qui ont des vols réguliers et un code IATA, et y ajoute les regroupements par ville
connus des comparateurs (TYO = Haneda + Narita, PAR = CDG + Orly…), avec les noms français de villes.

Usage : python outils/aeroports.py chemin/vers/airports.csv
Source : https://davidmegginson.github.io/ourairports-data/airports.csv
"""
import csv
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, ".."))
import villes  # noqa: E402  (noms français et regroupements par ville)

POIDS = {"large_airport": 3, "medium_airport": 2, "small_airport": 1}


def main(source):
    fr = {}       # code aéroport -> nom de ville en français
    metros = []   # regroupements par ville
    for pays, liste in villes.VILLES.items():
        for nom, code, aeros in liste:
            codes = aeros.split(",")
            for c in codes:
                fr[c] = nom
            if len(codes) > 1 or code not in codes:
                metros.append({"c": code, "v": nom, "a": codes})

    aeroports = []
    with open(source, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            iata = (r["iata_code"] or "").strip().upper()
            if (len(iata) != 3 or not iata.isalpha() or r["scheduled_service"] != "yes"
                    or r["type"] not in POIDS):
                continue
            ville = (r["municipality"] or "").strip()
            aeroports.append({
                "c": iata,
                "n": r["name"].strip().replace("–", "-").replace("—", "-"),  # tirets longs -> simples
                "v": fr.get(iata, ville),
                "ve": ville if fr.get(iata, ville) != ville else "",  # nom anglais conservé pour la recherche
                "p": r["iso_country"],
                "t": POIDS[r["type"]],
            })
    pays_de = {a["c"]: a["p"] for a in aeroports}
    for m in metros:
        m["p"] = next((pays_de[c] for c in m["a"] if c in pays_de), "")
        m["a"] = [c for c in m["a"] if c in pays_de]
    metros = [m for m in metros if m["p"] and len(m["a"]) > 1 or (m["p"] and m["c"] not in pays_de)]
    sortie = os.path.join(ICI, "..", "ressources", "aeroports.json")
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump({"source": "OurAirports (domaine public)", "aeroports": aeroports, "villes": metros},
                  f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(aeroports)} aéroports, {len(metros)} regroupements par ville, "
          f"{os.path.getsize(sortie) // 1024} Ko -> {os.path.abspath(sortie)}")


if __name__ == "__main__":
    main(sys.argv[1])
