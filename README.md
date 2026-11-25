# Mes vols

Application pour Windows et Mac qui suit le prix de vos voyages en avion et vous prévient quand il baisse.

- Vos voyages : villes, dates (aller simple ou aller-retour, à quelques jours près), voyageurs, classe, escales, durée maximale.
- Chaque jour à 9 h (ou au démarrage de l'ordinateur), les prix sont relevés sur Kayak et Momondo, et sur Google Flights si vous ajoutez une clé gratuite [SerpApi](https://serpapi.com).
- Une notification de l'ordinateur signale les bons prix.
- Tout reste sur votre ordinateur : aucun compte, aucun serveur.

## Télécharger

Rendez-vous dans les **[versions publiées](../../releases/latest)** : le mode d'emploi d'installation y est détaillé.

## Fonctionnement

| Fichier | Rôle |
|---|---|
| `mesvols.py` | Point d'entrée (ouvrir l'app, relevé, désinstallation) |
| `serveur.py`, `ressources/app.html` | Interface locale (127.0.0.1 uniquement) |
| `releve.py`, `lecteur.py` | Relevé des prix et lecture des pages de résultats |
| `projets.py`, `villes.py` | Critères des voyages et liens de recherche |
| `installation.py` | Programmation de la recherche quotidienne (tâche Windows, agent macOS) |
| `navigateur.py`, `notif.py` | Navigateur de recherche et notifications |

Les données de l'utilisateur sont dans `%LOCALAPPDATA%\MesVols` (Windows) ou `~/Library/Application Support/MesVols` (Mac).

Les comparateurs sont consultés comme le ferait une personne, à un rythme modéré, sans contournement de leurs protections. Les sites qui refusent les navigateurs automatisés (Skyscanner, Expedia, Google Flights en direct) ne sont pas interrogés.

## Fabriquer

```
pip install pyinstaller playwright openpyxl certifi pillow
python outils/icone.py
pyinstaller MesVols.spec --noconfirm
```

Les versions Windows et Mac sont fabriquées par GitHub Actions (`.github/workflows/fabrication.yml`) à chaque étiquette `vX.Y.Z`.
