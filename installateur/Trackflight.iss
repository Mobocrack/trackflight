; Installateur Windows de « Trackflight » (Inno Setup 6). Aucun droit administrateur nécessaire.
#define Version GetEnv("TRACKFLIGHT_VERSION")
#if Version == ""
  #define Version "1.0.0"
#endif

[Setup]
AppId={{6E3B7C2A-8F41-4D6B-9C1E-2A7F5D3B9E10}
AppName=Trackflight
AppVersion={#Version}
AppPublisher=Trackflight
DefaultDirName={localappdata}\Programs\Trackflight
UsePreviousAppDir=no
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\sortie
OutputBaseFilename=Trackflight-Windows-Installation
SetupIconFile=..\icones\icone.ico
UninstallDisplayIcon={app}\Trackflight.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "Créer un raccourci sur le Bureau"; Flags: checkedonce

[InstallDelete]
; Ancienne version « Mes vols » : fichiers et raccourcis remplacés par Trackflight
Type: filesandordirs; Name: "{localappdata}\Programs\Mes vols"
Type: files; Name: "{autoprograms}\Mes vols.lnk"
Type: files; Name: "{autodesktop}\Mes vols.lnk"

[Files]
Source: "..\dist\Trackflight\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Trackflight"; Filename: "{app}\Trackflight.exe"
Name: "{autodesktop}\Trackflight"; Filename: "{app}\Trackflight.exe"; Tasks: bureau

[Run]
Filename: "{app}\Trackflight.exe"; Description: "Ouvrir Trackflight"; Flags: nowait postinstall

[UninstallRun]
Filename: "{app}\Trackflight.exe"; Parameters: "--desinstaller"; Flags: runhidden waituntilterminated; RunOnceId: "RetirerRecherche"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
begin
  { ferme l'ancienne application « Mes vols » si elle tourne encore, pour pouvoir la remplacer }
  if CurStep = ssInstall then
    Exec(ExpandConstant('{sys}	askkill.exe'), '/F /IM MesVols.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;
