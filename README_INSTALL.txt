VIDEO BREAK PRO - PACCHETTO PROFESSIONALE (Windows)

COSA FA
- Ogni X minuti avvia una playlist (tutti i video nella cartella scelta)
- Riproduzione fullscreen tramite VLC
- A fine playlist VLC si chiude automaticamente e torni a ciò che stavi facendo
- Interfaccia grafica (UI) + Tray icon (area notifiche)
- Countdown "prossima riproduzione"
- Start/Stop + "Riproduci ora"
- Config e log salvati in %APPDATA%\VideoBreakPro\

REQUISITI
1) Windows 10/11
2) VLC Media Player installato (consigliato percorso standard)
   https://www.videolan.org/vlc/
3) Per creare l'EXE/Installer sul TUO PC: Python 3.10+ (solo per la fase di build)
   https://www.python.org/downloads/windows/

COME INSTALLARLO SU UN PC WINDOWS (2 modalità)

A) INSTALLER (consigliata, tipo “setup.exe”)
1) Estrai questo pacchetto in una cartella (es. C:\VideoBreakPro\)
2) Esegui build_exe.bat (doppio click) -> crea dist\VideoBreakPro.exe
3) Installa Inno Setup (gratis): https://jrsoftware.org/isinfo.php
4) Apri installer_inno.iss con Inno Setup e premi "Compile"
5) Troverai l'installer in installer_output\VideoBreakPro_Setup.exe
6) Ora puoi copiare VideoBreakPro_Setup.exe su QUALSIASI PC Windows e installare (senza Python)

B) PORTABLE (senza installer)
1) Esegui build_exe.bat -> crea dist\VideoBreakPro.exe
2) Copia dist\VideoBreakPro.exe e la cartella assets\ su un PC
3) Avvia VideoBreakPro.exe

NOTE IMPORTANTI
- La cartella video di default è: %APPDATA%\VideoBreakPro\videos
- Config: %APPDATA%\VideoBreakPro\config.json
- Log: %APPDATA%\VideoBreakPro\run.log

TIP
- Se VLC non è nel percorso standard, apri l'app e seleziona manualmente vlc.exe (tasto “Sfoglia”).
