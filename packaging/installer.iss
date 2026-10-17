#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

[Setup]
AppId={{D004EF3B-63BD-4160-90EF-FB4C3BA8D6F5}
AppName=Spare My Eyes
AppVersion={#AppVersion}
AppPublisher=Spare My Eyes contributors
DefaultDirName={autopf}\Spare My Eyes
DefaultGroupName=Spare My Eyes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=SpareMyEyes-Setup-{#AppVersion}
SetupIconFile=SpareMyEyes.ico
UninstallDisplayIcon={app}\SpareMyEyes.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=force

[Tasks]
Name: "startup"; Description: "Start Spare My Eyes when I sign in to Windows"; GroupDescription: "Startup:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\SpareMyEyes\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Spare My Eyes"; Filename: "{app}\SpareMyEyes.exe"
Name: "{autodesktop}\Spare My Eyes"; Filename: "{app}\SpareMyEyes.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "SpareMyEyes"; ValueType: none; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SpareMyEyes"; ValueData: """{app}\SpareMyEyes.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\SpareMyEyes.exe"; Description: "Start Spare My Eyes now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM SpareMyEyes.exe /F"; Flags: runhidden; RunOnceId: "StopSpareMyEyes"
