@echo off
REM Retoma el entrenamiento actual (entrenar_master.py) desde su ultimo punto guardado.
REM Deje esta ventana abierta mientras entrena; Ctrl+C para detener (se puede retomar despues).
cd /d "%~dp0"
.venv\Scripts\python.exe -u entrenar_master.py
pause
