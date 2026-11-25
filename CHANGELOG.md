# Journal des versions

## 1.3.1 (25/11/2026)

- Correctif : la 1.3.0 ne démarrait pas sur les Mac Intel sous un macOS antérieur à la version 15. La bibliothèque de chiffrement « cryptography » n'est plus publiée prête à l'emploi pour Mac Intel : recompilée par GitHub, elle embarquait une copie d'OpenSSL exigeant macOS 15. Le coffre utilise désormais PyCryptodome (même chiffrement AES-256-GCM et scrypt, autonome, compatible dès macOS 10.9) ; un coffre créé avec la 1.3.0 reste lisible.
- Fabrication : contrôle automatique qui refuse de publier une version Mac dont un fichier exige un macOS plus récent que macOS 11.

## 1.3.0 (25/11/2026)

- Nouveau : coffre à clés (Réglages > Google Flights > Coffre à clés). Livré vide, il range les clés prêtées par d'autres personnes, avec leur accord. Chiffré (AES-256-GCM) par un mot de passe choisi par la personne, avec un code de secours affiché une seule fois en cas d'oubli. La clé active reste dans l'app : le coffre ne s'ouvre que pour échanger de clé.
- Clé épuisée : l'app le repère (message de SerpApi ou limite mensuelle), prévient par une notification, puis propose à l'ouverture d'utiliser une autre clé du coffre. L'échange se fait seulement sur décision de l'utilisateur, jamais tout seul.
- Le compteur de recherches mensuelles est propre à chaque clé.
- Nouveau : alerte « Nouveau meilleur prix », active par défaut : notification dès que le meilleur prix d'un voyage passe sous le plus bas déjà vu (nouveau vol ou baisse lente).
- Nouveau : heure de la recherche quotidienne réglable (Réglages > Recherche automatique), 9 h par défaut.
- Nouveau : badge sur les vols dont une escale demande une autorisation de voyage (ESTA États-Unis, AVE Canada, ETA Royaume-Uni), avec le coût indicatif au survol. Information seulement : ces vols restent proposés.
- Nouveau : logo de la compagnie à côté de son nom (fourni par Google Flights).

## 1.2.5 (25/11/2026)

- Nouveau : « Repère Google Flights » sur la page d'un voyage : prix bas, habituel ou élevé pour ce trajet, fourchette de prix habituelle par personne, et courbe des prix des dernières semaines vue par Google. Ces informations arrivent avec chaque recherche Google Flights, sans en consommer davantage.

## 1.2.4 (25/11/2026)

- Alertes plus claires : les montants sont indiqués « par personne » (le prix d'un billet), avec le total pour le groupe quand il y a plusieurs voyageurs (par exemple « 600 € par personne, soit 1 800 € pour vos 3 voyageurs »), dans le questionnaire et dans la fiche de modification.

## 1.2.3 (25/11/2026)

- Nouveau : Réglages > Journal des recherches, affiché en temps réel (les plus récentes en haut, erreurs en rouge) avec un bouton « Copier ». Les clés et le dossier personnel y sont masqués.
- Google Flights : la vraie raison d'un refus est gardée (par exemple « aéroport inconnu », « aucun résultat ») au lieu de « HTTP Error 400 », et affichée dans l'app.
- Quand un voyage n'a aucun prix alors que d'autres en ont, l'app dit lequel et pourquoi.
- Journal : une ligne par date interrogée sur Google Flights.

## 1.2.2 (25/11/2026)

- Google Flights par une clé SerpApi gratuite : saisie simplifiée dans les réglages (boutons « Coller » et « Vérifier et enregistrer »), vérification de la clé sans consommer de recherche.
- Sur Mac, une clé validée active « Utiliser seulement Google Flights » : Kayak et Momondo refusent la recherche automatique sur Mac, et le navigateur de recherche (150 Mo) n'est plus téléchargé pour rien.
- La page anti-robot de Kayak et Momondo est reconnue : la recherche s'arrête tout de suite et l'app l'explique, au lieu de chercher plusieurs minutes sans résultat.
- Toute erreur de recherche est écrite dans le journal et affichée dans l'app (auparavant, une erreur de navigateur passait inaperçue).
- Téléchargement du navigateur de recherche plus fiable : un téléchargement interrompu n'est plus compté comme réussi ; un échec s'affiche au lieu de « En cours » sans fin.
- Liens de recherche manuelle quand un voyage n'a pas encore de prix.
- Guide : numéro de version, état de la clé Google Flights, mots en gras qui ne passent plus à la ligne.
- Page de téléchargement : ouverture de l'app sur macOS 15 et plus, et sur macOS 14 et avant.

## 1.2.1 (25/11/2026)

- Bouton d'ouverture des réglages de notifications ; fabrication Mac Apple sur macOS 15 ; mise à jour Mac avec repli Intel (Rosetta).

## 1.2.0 (25/11/2026)

- Mise à jour intégrée, guide de démarrage, thème clair par défaut.

## 1.1.0 (25/11/2026)

- Nouveau nom Trackflight, vraie fenêtre, création de voyage par étapes, recherche d'aéroports, voyage Japon pré-rempli.

## 1.0.0 (25/11/2026)

- Première version, sous le nom « Mes vols ».
