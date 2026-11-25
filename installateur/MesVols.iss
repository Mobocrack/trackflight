; Installateur Windows de « Mes vols » (Inno Setup 6). Aucun droit administrateur nécessaire.
#define Version GetEnv("MESVOLS_VERSION")
#if Version == ""
  #define Version "1.0.0"
#endif

[Setup]
AppId={{6E3B7C2A-8F41-4D6B-9C1E-2A7F5D3B9E10}
AppName=Mes vols
AppVersion={#Version}
AppPublisher=Mes vols
DefaultDirName={localappdata}\Programs\Mes vols
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\sortie
OutputBaseFilename=MesVols-Windows-Installation
SetupIconFile=..\icones\icone.ico
UninstallDisplayIcon={app}\MesVols.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "Créer un raccourci sur le Bureau"; Flags: checkedonce

[Files]
Source: "..\dist\MesVols\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Mes vols"; Filename: "{app}\MesVols.exe"
Name: "{autodesktop}\Mes vols"; Filename: "{app}\MesVols.exe"; Tasks: bureau

[Run]
Filename: "{app}\MesVols.exe"; Description: "Ouvrir Mes vols"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\MesVols.exe"; Parameters: "--desinstaller"; Flags: runhidden waituntilterminated; RunOnceId: "RetirerRecherche"
