@echo off
REM QS-Testsuite Hausraster unter Windows mit FreeCADCmd
setlocal
cd /d "%~dp0"

if defined FREECADCMD (
  set "FCCMD=%FREECADCMD%"
) else if exist "%ProgramFiles%\FreeCAD 1.1\bin\FreeCADCmd.exe" (
  set "FCCMD=%ProgramFiles%\FreeCAD 1.1\bin\FreeCADCmd.exe"
) else if exist "%ProgramFiles%\FreeCAD 1.0\bin\FreeCADCmd.exe" (
  set "FCCMD=%ProgramFiles%\FreeCAD 1.0\bin\FreeCADCmd.exe"
) else (
  echo FreeCADCmd.exe nicht gefunden. Bitte FREECADCMD auf die volle EXE-Pfad setzen.
  exit /b 1
)

echo Starte "%FCCMD%" run_qs_audit.py
"%FCCMD%" "%~dp0run_qs_audit.py"
echo Ergebnisse liegen in "%~dp0out\report.md" und report.json
