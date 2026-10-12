@echo off
REM Retoma el entrenamiento desde el último punto guardado (modelos\ultimo.pt).
REM Deje esta ventana abierta mientras entrena; Ctrl+C para detener (se puede retomar después).
cd /d "%~dp0"
.venv\Scripts\python.exe -u entrenar.py --continuar --pasos 600e6
pause
