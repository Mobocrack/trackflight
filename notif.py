"""Notifications de l'ordinateur (Windows ou Mac), sans rien à installer.
Le titre et le message sont passés en paramètres, jamais insérés dans le code exécuté."""
import os
import subprocess

import chemins

SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_PS = r"""
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $xml.GetElementsByTagName('text')
$null = $t.Item(0).AppendChild($xml.CreateTextNode($env:MV_TITRE))
$null = $t.Item(1).AppendChild($xml.CreateTextNode($env:MV_MESSAGE))
$n = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe').Show($n)
"""


def envoyer(titre, message):
    """Affiche une notification. Renvoie True si elle a pu être envoyée."""
    try:
        if chemins.SYSTEME == "Windows":
            env = dict(os.environ, MV_TITRE=titre[:120], MV_MESSAGE=message[:600])
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", _PS],
                               env=env, capture_output=True, timeout=30, creationflags=SANS_FENETRE)
            return r.returncode == 0
        if chemins.SYSTEME == "Darwin":
            r = subprocess.run(["osascript", "-e", "on run argv", "-e",
                                "display notification (item 2 of argv) with title (item 1 of argv) sound name \"Glass\"",
                                "-e", "end run", titre[:120], message[:600]], capture_output=True, timeout=30)
            return r.returncode == 0
        r = subprocess.run(["notify-send", titre, message], capture_output=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
