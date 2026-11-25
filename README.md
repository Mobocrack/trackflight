# Trackflight

Application pour Windows et Mac qui suit le prix de vos voyages en avion et vous prévient quand il baisse.

- Vos voyages : villes, dates (aller simple ou aller-retour, à quelques jours près), voyageurs, classe, escales, durée maximale.
- Chaque jour à 9 h (ou au démarrage de l'ordinateur), les prix sont relevés sur Kayak et Momondo (Windows), et sur Google Flights avec une clé gratuite [SerpApi](https://serpapi.com) (indispensable sur Mac, où Kayak et Momondo refusent la recherche automatique).
- Une notification de l'ordinateur signale les bons prix.
- Tout reste sur votre ordinateur : aucun compte, aucun serveur.

## Télécharger

Rendez-vous dans les **[versions publiées](../../releases/latest)** : le mode d'emploi d'installation y est détaillé.

## Fonctionnement

| Fichier | Rôle |
|---|---|
| `trackflight.py` | Point d'entrée (ouvrir l'app, relevé, désinstallation) |
| `serveur.py`, `ressources/app.html` | Interface locale (127.0.0.1 uniquement) |
| `releve.py`, `lecteur.py` | Relevé des prix et lecture des pages de résultats |
| `projets.py`, `villes.py` | Critères des voyages et liens de recherche |
| `installation.py` | Programmation de la recherche quotidienne (tâche Windows, agent macOS) |
| `navigateur.py`, `notif.py` | Navigateur de recherche et notifications |
| `coffre.py` | Coffre à clés chiffré (AES-256-GCM, mot de passe et code de secours dérivés par scrypt) |

Les données de l'utilisateur sont dans `%LOCALAPPDATA%\Trackflight` (Windows) ou `~/Library/Application Support/Trackflight` (Mac).

Les comparateurs sont consultés à un rythme modéré, sans aucun contournement de leurs protections : si un site affiche sa page anti-robot, la recherche s'arrête pour ce site. Les sites qui refusent les navigateurs automatisés (Skyscanner, Expedia, Google Flights en direct) ne sont pas interrogés.

## Fabriquer

```
pip install pyinstaller playwright openpyxl certifi pillow pywebview cryptography
python outils/icone.py
pyinstaller Trackflight.spec --noconfirm
```

Les versions Windows et Mac sont fabriquées par GitHub Actions (`.github/workflows/fabrication.yml`) à chaque étiquette `vX.Y.Z`.

Historique des versions : [CHANGELOG.md](CHANGELOG.md). La clé SerpApi de chacun reste dans ses réglages locaux, jamais dans ce dépôt.
