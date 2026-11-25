"""Programme la recherche quotidienne (9 h) et son rattrapage à l'ouverture de session.

Windows : une tâche planifiée de l'utilisateur (aucun droit administrateur).
Mac : un agent de lancement dans ~/Library/LaunchAgents.
Réinscrite automatiquement si l'application a été déplacée ou mise à jour.
"""
import json
import os
import plistlib
import subprocess

import chemins

TACHE = "Trackflight - recherche quotidienne"
AGENT = "fr.trackflight.releve"
# Ancien nom de l'application (« Mes vols », version 1.0) : retiré à l'installation de Trackflight.
TACHE_ANCIENNE = "Mes vols - recherche quotidienne"
AGENT_ANCIEN = "fr.mesvols.releve"
FICHIER = os.path.join(chemins.donnees(), "installation.json")
SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_PS_INSTALLER = r"""
$a = New-ScheduledTaskAction -Execute $env:MV_EXE -Argument $env:MV_ARGS
$t1 = New-ScheduledTaskTrigger -Daily -At 09:00
$t2 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$t2.Delay = 'PT5M'
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $env:MV_TACHE -Action $a -Trigger @($t1, $t2) -Settings $s -Description 'Relève les prix de vos voyages (application Trackflight).' -Force | Out-Null
"""


def _commande():
    cmd = chemins.commande("--releve", "--si-besoin")
    return cmd[0], cmd[1:]


def _plist():
    return os.path.expanduser(f"~/Library/LaunchAgents/{AGENT}.plist")


def retirer_ancien():
    """Retire la recherche programmée par l'ancienne version « Mes vols »."""
    try:
        if chemins.SYSTEME == "Windows":
            subprocess.run(["schtasks", "/Delete", "/TN", TACHE_ANCIENNE, "/F"], capture_output=True, creationflags=SANS_FENETRE)
        elif chemins.SYSTEME == "Darwin":
            ancien = os.path.expanduser(f"~/Library/LaunchAgents/{AGENT_ANCIEN}.plist")
            if os.path.exists(ancien):
                subprocess.run(["launchctl", "unload", ancien], capture_output=True)
                os.remove(ancien)
    except OSError:
        pass


def installer(force=False):
    """Inscrit la recherche quotidienne. Renvoie (ok, message)."""
    retirer_ancien()
    exe, args = _commande()
    if "/AppTranslocation/" in exe:
        # macOS lance les apps téléchargées depuis un emplacement temporaire : la programmation y serait perdue.
        return False, "Glissez « Trackflight » dans le dossier Applications, puis rouvrez-la depuis là."
    signature = {"exe": exe, "args": args}
    try:
        with open(FICHIER, encoding="utf-8") as f:
            deja = json.load(f)
    except (OSError, ValueError):
        deja = None
    if deja == signature and not force and est_installee():
        return True, "déjà programmée"
    try:
        if chemins.SYSTEME == "Windows":
            arg_txt = " ".join(f'"{a}"' if " " in a else a for a in args)
            env = dict(os.environ, MV_EXE=exe, MV_ARGS=arg_txt, MV_TACHE=TACHE)
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_INSTALLER], env=env,
                               capture_output=True, text=True, timeout=60, creationflags=SANS_FENETRE)
            if r.returncode:
                return False, (r.stderr or r.stdout).strip()[-300:]
        elif chemins.SYSTEME == "Darwin":
            os.makedirs(os.path.dirname(_plist()), exist_ok=True)
            with open(_plist(), "wb") as f:
                plistlib.dump({"Label": AGENT, "ProgramArguments": [exe, *args], "RunAtLoad": True,
                               "StartCalendarInterval": {"Hour": 9, "Minute": 0},
                               "StandardErrorPath": os.path.join(chemins.donnees(), "planificateur.err")}, f)
            subprocess.run(["launchctl", "unload", _plist()], capture_output=True)
            r = subprocess.run(["launchctl", "load", _plist()], capture_output=True, text=True)
            if r.returncode:
                return False, r.stderr.strip()[-300:]
        else:
            return False, "programmation automatique non prise en charge sur ce système"
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    with open(FICHIER, "w", encoding="utf-8") as f:
        json.dump(signature, f)
    return True, "programmée"


def est_installee():
    if chemins.SYSTEME == "Windows":
        r = subprocess.run(["schtasks", "/Query", "/TN", TACHE], capture_output=True, creationflags=SANS_FENETRE)
        return r.returncode == 0
    if chemins.SYSTEME == "Darwin":
        return os.path.exists(_plist())
    return False


def desinstaller():
    try:
        if chemins.SYSTEME == "Windows":
            subprocess.run(["schtasks", "/Delete", "/TN", TACHE, "/F"], capture_output=True, creationflags=SANS_FENETRE)
        elif chemins.SYSTEME == "Darwin" and os.path.exists(_plist()):
            subprocess.run(["launchctl", "unload", _plist()], capture_output=True)
            os.remove(_plist())
        if os.path.exists(FICHIER):
            os.remove(FICHIER)
        return True
    except OSError:
        return False
