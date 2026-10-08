@echo off
REM Abre el visor 3D de la simulación (dron vs persona) en el navegador.
cd /d "%~dp0"
start "Servidor del visor" /min .venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8765/
