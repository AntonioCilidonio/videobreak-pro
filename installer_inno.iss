; VideoBreak Pro - Inno Setup Script
#define MyAppName "VideoBreak Pro"
#define MyAppExeName "VideoBreakPro.exe"
#define MyAppVersion "1.0.0"
#define MyPublisher "VideoBreak Pro"

[Setup]
AppId={{C8DF1A08-2D78-4F2C-8D3B-2D7E6A41E1CC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=VideoBreakPro_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea icona sul Desktop"; GroupDescription: "Opzioni:"; Flags: unchecked
Name: "startup"; Description: "Avvia VideoBreak Pro con Windows"; GroupDescription: "Opzioni:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "README_INSTALL.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "VideoBreakPro"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup
