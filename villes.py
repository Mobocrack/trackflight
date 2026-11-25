"""Villes proposées dans le formulaire : pays -> [(ville, code de recherche, aéroports)].
Le code de recherche est le code « ville » des comparateurs (TYO = tous les aéroports de Tokyo)
ou l'aéroport lui-même. Les aéroports servent à Google Flights (SerpApi), qui ne connaît pas les codes ville.
Une ville absente peut toujours être saisie par son code d'aéroport dans le formulaire."""

VILLES = {
    "France": [("Paris", "PAR", "CDG,ORY"), ("Nice", "NCE", "NCE"), ("Lyon", "LYS", "LYS"), ("Marseille", "MRS", "MRS"),
               ("Toulouse", "TLS", "TLS"), ("Bordeaux", "BOD", "BOD"), ("Nantes", "NTE", "NTE"), ("Montpellier", "MPL", "MPL"),
               ("Bâle-Mulhouse", "BSL", "BSL"), ("Strasbourg", "SXB", "SXB"), ("Lille", "LIL", "LIL"), ("Biarritz", "BIQ", "BIQ"),
               ("Ajaccio", "AJA", "AJA"), ("Bastia", "BIA", "BIA")],
    "Outre-mer": [("La Réunion", "RUN", "RUN"), ("Guadeloupe", "PTP", "PTP"), ("Martinique", "FDF", "FDF"),
                  ("Tahiti", "PPT", "PPT"), ("Nouméa", "NOU", "NOU"), ("Cayenne", "CAY", "CAY")],
    "Japon": [("Tokyo", "TYO", "HND,NRT"), ("Osaka", "OSA", "KIX,ITM"), ("Nagoya", "NGO", "NGO"), ("Fukuoka", "FUK", "FUK"),
              ("Sapporo", "CTS", "CTS"), ("Okinawa", "OKA", "OKA"), ("Hiroshima", "HIJ", "HIJ")],
    "Corée du Sud": [("Séoul", "SEL", "ICN,GMP"), ("Busan", "PUS", "PUS")],
    "Chine": [("Pékin", "BJS", "PEK,PKX"), ("Shanghai", "SHA", "PVG,SHA"), ("Hong Kong", "HKG", "HKG")],
    "Taïwan": [("Taipei", "TPE", "TPE")],
    "Thaïlande": [("Bangkok", "BKK", "BKK,DMK"), ("Phuket", "HKT", "HKT"), ("Chiang Mai", "CNX", "CNX")],
    "Vietnam": [("Hô Chi Minh-Ville", "SGN", "SGN"), ("Hanoï", "HAN", "HAN"), ("Da Nang", "DAD", "DAD")],
    "Singapour": [("Singapour", "SIN", "SIN")],
    "Indonésie": [("Bali", "DPS", "DPS"), ("Jakarta", "JKT", "CGK")],
    "Philippines": [("Manille", "MNL", "MNL")],
    "Inde": [("Delhi", "DEL", "DEL"), ("Mumbai", "BOM", "BOM")],
    "Émirats arabes unis": [("Dubaï", "DXB", "DXB"), ("Abou Dabi", "AUH", "AUH")],
    "Qatar": [("Doha", "DOH", "DOH")],
    "Turquie": [("Istanbul", "IST", "IST,SAW"), ("Antalya", "AYT", "AYT")],
    "Royaume-Uni": [("Londres", "LON", "LHR,LGW,STN,LTN,LCY"), ("Édimbourg", "EDI", "EDI"), ("Manchester", "MAN", "MAN")],
    "Irlande": [("Dublin", "DUB", "DUB")],
    "Espagne": [("Madrid", "MAD", "MAD"), ("Barcelone", "BCN", "BCN"), ("Séville", "SVQ", "SVQ"), ("Valence", "VLC", "VLC"),
                ("Malaga", "AGP", "AGP"), ("Palma de Majorque", "PMI", "PMI"), ("Tenerife", "TCI", "TFS,TFN"), ("Ibiza", "IBZ", "IBZ")],
    "Portugal": [("Lisbonne", "LIS", "LIS"), ("Porto", "OPO", "OPO"), ("Faro", "FAO", "FAO"), ("Madère", "FNC", "FNC")],
    "Italie": [("Rome", "ROM", "FCO,CIA"), ("Milan", "MIL", "MXP,LIN,BGY"), ("Venise", "VCE", "VCE"), ("Naples", "NAP", "NAP"),
               ("Florence", "FLR", "FLR"), ("Catane", "CTA", "CTA"), ("Palerme", "PMO", "PMO")],
    "Grèce": [("Athènes", "ATH", "ATH"), ("Santorin", "JTR", "JTR"), ("Héraklion", "HER", "HER")],
    "Pays-Bas": [("Amsterdam", "AMS", "AMS")],
    "Belgique": [("Bruxelles", "BRU", "BRU,CRL")],
    "Suisse": [("Genève", "GVA", "GVA"), ("Zurich", "ZRH", "ZRH")],
    "Allemagne": [("Berlin", "BER", "BER"), ("Munich", "MUC", "MUC"), ("Francfort", "FRA", "FRA")],
    "Autriche": [("Vienne", "VIE", "VIE")],
    "Tchéquie": [("Prague", "PRG", "PRG")],
    "Hongrie": [("Budapest", "BUD", "BUD")],
    "Pologne": [("Varsovie", "WAW", "WAW"), ("Cracovie", "KRK", "KRK")],
    "Danemark": [("Copenhague", "CPH", "CPH")],
    "Suède": [("Stockholm", "STO", "ARN,BMA")],
    "Norvège": [("Oslo", "OSL", "OSL")],
    "Finlande": [("Helsinki", "HEL", "HEL")],
    "Islande": [("Reykjavik", "KEF", "KEF")],
    "Croatie": [("Dubrovnik", "DBV", "DBV"), ("Split", "SPU", "SPU")],
    "Maroc": [("Marrakech", "RAK", "RAK"), ("Casablanca", "CMN", "CMN"), ("Agadir", "AGA", "AGA")],
    "Tunisie": [("Tunis", "TUN", "TUN"), ("Djerba", "DJE", "DJE")],
    "Égypte": [("Le Caire", "CAI", "CAI")],
    "Sénégal": [("Dakar", "DSS", "DSS")],
    "Maurice": [("Maurice", "MRU", "MRU")],
    "États-Unis": [("New York", "NYC", "JFK,EWR,LGA"), ("Los Angeles", "LAX", "LAX"), ("San Francisco", "SFO", "SFO"),
                   ("Miami", "MIA", "MIA"), ("Chicago", "CHI", "ORD,MDW"), ("Las Vegas", "LAS", "LAS"),
                   ("Washington", "WAS", "IAD,DCA,BWI"), ("Boston", "BOS", "BOS"), ("Honolulu", "HNL", "HNL")],
    "Canada": [("Montréal", "YMQ", "YUL"), ("Toronto", "YTO", "YYZ,YTZ"), ("Vancouver", "YVR", "YVR"), ("Québec", "YQB", "YQB")],
    "Mexique": [("Mexico", "MEX", "MEX"), ("Cancún", "CUN", "CUN")],
    "Brésil": [("Rio de Janeiro", "RIO", "GIG,SDU"), ("São Paulo", "SAO", "GRU,CGH")],
    "Argentine": [("Buenos Aires", "BUE", "EZE,AEP")],
    "Pérou": [("Lima", "LIM", "LIM")],
    "Australie": [("Sydney", "SYD", "SYD"), ("Melbourne", "MEL", "MEL")],
    "Nouvelle-Zélande": [("Auckland", "AKL", "AKL")],
}


def chercher(code):
    """Retrouve (pays, ville, code, aéroports) à partir d'un code ville ou aéroport."""
    code = code.upper()
    for pays, villes in VILLES.items():
        for nom, c, aeros in villes:
            if code == c or code in aeros.split(","):
                return pays, nom, c, aeros
    return None


def en_json():
    return [{"pays": p, "villes": [{"nom": n, "code": c, "aeroports": a} for n, c, a in v]} for p, v in VILLES.items()]
