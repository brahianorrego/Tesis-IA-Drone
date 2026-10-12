@echo off
REM Abre el visor 3D de la simulación (dron vs persona) en el navegador.
cd /d "%~dp0"
start "Servidor del visor" /min .venv\Scripts\python.exe servidor_visor.py --puerto 8765
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8765/
