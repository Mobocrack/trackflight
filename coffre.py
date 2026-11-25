"""Coffre à clés Google Flights (SerpApi), chiffré par un mot de passe choisi par la personne.

Le coffre range des clés prêtées par d'autres personnes, avec leur accord (« Axel », « Frère »…).
La clé active reste dans les réglages de l'app : le coffre ne sert qu'à l'échanger, quand quelqu'un
est devant l'écran pour taper le mot de passe. La recherche automatique n'ouvre jamais le coffre.

Chiffrement (bibliothèque « PyCryptodome », autonome, sans OpenSSL ; rien d'inventé) :
- une clé de données aléatoire de 256 bits chiffre le contenu (AES-256-GCM) ;
- cette clé de données est elle-même chiffrée deux fois : avec une clé tirée du mot de passe
  (scrypt), et avec une clé tirée du code de secours (scrypt), affiché une seule fois à la création.
Sans le mot de passe ni le code de secours, le fichier est illisible, même copié ailleurs.
"""
import base64
import json
import os
import secrets

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt as _scrypt

import chemins

FICHIER = os.path.join(chemins.donnees(), "coffre.json")
VERSION = 1
SCRYPT = {"n": 2 ** 17, "r": 8, "p": 1}  # environ 128 Mo et une fraction de seconde par essai : freine les essais en série
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O ni 1/I : plus facile à recopier
MDP_MIN = 8


class CoffreErreur(Exception):
    """Erreur expliquée en français, affichable telle quelle."""


def _b64(b):
    return base64.b64encode(b).decode("ascii")


def _octets(s):
    return base64.b64decode(s.encode("ascii"))


def _deriver(secret, sel, n=SCRYPT["n"], r=SCRYPT["r"], p=SCRYPT["p"]):
    return _scrypt(secret.encode("utf-8"), sel, key_len=32, N=n, r=r, p=p)


# AES-256-GCM. Format : texte chiffré suivi de l'étiquette d'authenticité (16 octets), comme la norme le prévoit.
def _sceller(cle, donnees, contexte):
    nonce = os.urandom(12)
    c = AES.new(cle, AES.MODE_GCM, nonce=nonce)
    c.update(contexte)
    texte, etiquette = c.encrypt_and_digest(donnees)
    return {"nonce": _b64(nonce), "texte": _b64(texte + etiquette)}


def _ouvrir(cle, boite, contexte):
    brut = _octets(boite["texte"])
    c = AES.new(cle, AES.MODE_GCM, nonce=_octets(boite["nonce"]))
    c.update(contexte)
    return c.decrypt_and_verify(brut[:-16], brut[-16:])  # ValueError si la clé est fausse ou le fichier modifié


def _normaliser_code(code):
    return "".join(c for c in code.upper() if c in ALPHABET)


def nouveau_code():
    brut = "".join(secrets.choice(ALPHABET) for _ in range(20))
    return "-".join(brut[i:i + 4] for i in range(0, 20, 4))


def existe():
    return os.path.exists(FICHIER)


def _lire():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            c = json.load(f)
    except FileNotFoundError:
        raise CoffreErreur("Aucun coffre sur cet ordinateur.")
    except (OSError, ValueError):
        raise CoffreErreur("Le fichier du coffre est abîmé.")
    if c.get("version") != VERSION:
        raise CoffreErreur("Ce coffre vient d'une autre version de Trackflight.")
    return c


def _ecrire(c):
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=1)
    os.replace(tmp, FICHIER)  # écriture d'un bloc : jamais de coffre à moitié écrit
    try:
        os.chmod(FICHIER, 0o600)
    except OSError:
        pass


def _verrous(dek, mdp=None, code=None, ancien=None):
    """Chiffre la clé de données avec le mot de passe et/ou le code de secours."""
    v = dict(ancien or {})
    if mdp is not None:
        sel = os.urandom(16)
        v["mdp"] = {"sel": _b64(sel), **SCRYPT, **_sceller(_deriver(mdp, sel), dek, b"mdp")}
    if code is not None:
        sel = os.urandom(16)
        v["secours"] = {"sel": _b64(sel), **SCRYPT, **_sceller(_deriver(_normaliser_code(code), sel), dek, b"secours")}
    return v


def creer(mdp):
    """Crée un coffre vide. Renvoie le code de secours (à noter : il n'est affiché qu'une fois)."""
    if existe():
        raise CoffreErreur("Un coffre existe déjà sur cet ordinateur.")
    if len(mdp or "") < MDP_MIN:
        raise CoffreErreur(f"Choisissez un mot de passe d'au moins {MDP_MIN} caractères.")
    dek, code = secrets.token_bytes(32), nouveau_code()
    _ecrire({"version": VERSION, "verrous": _verrous(dek, mdp=mdp, code=code),
             "contenu": _sceller(dek, b"[]", b"contenu")})
    return code


def _dek(c, mdp=None, code=None):
    try:
        if mdp:
            v = c["verrous"]["mdp"]
            return _ouvrir(_deriver(mdp, _octets(v["sel"]), v["n"], v["r"], v["p"]), v, b"mdp")
        if code:
            v = c["verrous"]["secours"]
            return _ouvrir(_deriver(_normaliser_code(code), _octets(v["sel"]), v["n"], v["r"], v["p"]), v, b"secours")
    except (KeyError, ValueError):
        pass
    raise CoffreErreur("Mot de passe incorrect." if mdp else "Code de secours incorrect.")


def lire(mdp=None, code=None):
    """Renvoie la liste des clés [{nom, cle}] (déchiffrée en mémoire seulement)."""
    c = _lire()
    dek = _dek(c, mdp, code)
    try:
        return json.loads(_ouvrir(dek, c["contenu"], b"contenu"))
    except (KeyError, ValueError):
        raise CoffreErreur("Le fichier du coffre a été abîmé ou modifié : il ne peut plus être lu.")


def enregistrer(mdp, cles):
    c = _lire()
    dek = _dek(c, mdp)
    c["contenu"] = _sceller(dek, json.dumps(cles).encode("utf-8"), b"contenu")
    _ecrire(c)


def nouveau_mdp(nouveau, mdp=None, code=None):
    """Change le mot de passe (avec l'ancien, ou avec le code de secours en cas d'oubli).
    Avec le code de secours, un nouveau code est créé et renvoyé (l'ancien ne sert plus)."""
    if len(nouveau or "") < MDP_MIN:
        raise CoffreErreur(f"Choisissez un mot de passe d'au moins {MDP_MIN} caractères.")
    c = _lire()
    dek = _dek(c, mdp, code)
    nouveau_code_secours = nouveau_code() if code else None
    c["verrous"] = _verrous(dek, mdp=nouveau, code=nouveau_code_secours, ancien=c["verrous"])
    _ecrire(c)
    return nouveau_code_secours


def supprimer():
    """Efface le coffre (en cas de perte du mot de passe ET du code : les clés se retrouvent sur serpapi.com)."""
    try:
        os.remove(FICHIER)
    except FileNotFoundError:
        pass
