@echo off
rem Open the Sherlock GUI page in a browser. Works even if auto-open failed.
rem Order: Chrome (64/32) -> Edge (64/32) -> system default handler.
rem Set SHERLOCK_GUI_PORT to match a custom port; default is 8766.
setlocal
if "%SHERLOCK_GUI_PORT%"=="" (set "PORT=8766") else (set "PORT=%SHERLOCK_GUI_PORT%")
set "URL=http://127.0.0.1:%PORT%/"

if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" goto chrome64
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" goto chrome86
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" goto chromeLocal
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" goto edge64
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" goto edge86
if exist "%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe" goto edgeLocal
goto default

:chrome64
start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" %URL%
goto done

:chrome86
start "" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" %URL%
goto done

:chromeLocal
start "" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" %URL%
goto done

:edge64
start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" %URL%
goto done

:edge86
start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" %URL%
goto done

:edgeLocal
start "" "%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe" %URL%
goto done

:default
start "" %URL%

:done
endlocal
