# Simulación: dron vs ladrón (aprendizaje por refuerzo)

Entrena la IA de decisión del dron por refuerzo en un mundo virtual, sin datos etiquetados a mano. El juego es el
**dron contra el ladrón**: el dron busca, el operador confirma con un clic quién es el sospechoso y el dron lo
mantiene a la vista mientras el ladrón se esconde detrás de los muros, se cansa y a veces ataca. Los civiles son
obstáculos y distractores.

El dron virtual percibe el mundo como el real:
- cámara de 38.9° con YOLO (ruido, pérdidas, detección parcial y 100 ms de retraso);
- LiDAR TF03 (30 m) con mapa de puntos;
- gimbal de pitch con límite duro −45°..+15°;
- la posición, el rumbo y la altura que da la Pixhawk;
- los controladores reales modelados en `control.py`.

Aquí también está el **mínimo indispensable** del comité (`minimo_tesis/`), separado y congelado.

## Uso (Windows)

| Qué | Cómo |
|---|---|
| Ver la simulación y las curvas de aprendizaje | doble clic en `ABRIR_VISOR.bat` → http://127.0.0.1:8765/ |
| Retomar el entrenamiento actual | doble clic en `CONTINUAR_ENTRENAMIENTO.bat` (`entrenar_master.py` sin argumentos) |
| Pruebas | `.venv\Scripts\python.exe -m unittest discover -s tests` |
| Resumen de un entrenamiento | `.venv\Scripts\python.exe herramientas\resumir_metricas.py` → `informes\` |
| Evaluación en escenarios fijos | `.venv\Scripts\python.exe herramientas\evaluar_politica.py --modelo <checkpoint.zip>` → `informes\` |
| Protocolo del comité (mínimo) | ver `minimo_tesis/README.md` |

El entorno virtual `.venv` no se sube al repositorio. Para crearlo: `py -m venv .venv` y
`.venv\Scripts\pip install torch numpy gymnasium stable-baselines3 scikit-learn`.

## Archivos

| Archivo o carpeta | Qué es |
|---|---|
| `entorno.py` | Mundo vectorizado en NumPy: sensores, mapa LiDAR, máquina de estados, árbitro, ladrón, civiles, rendición y recompensas (V15) |
| `control.py` | Cascada PSC/ATC de ArduPilot y PID del gimbal BaseCam |
| `entrenar_master.py` | Entrenamiento actual: PPO de Stable-Baselines3 con currículo de niveles y métricas para el visor |
| `entrenar.py` | PPO propio de las versiones 1 a 9; el master reutiliza sus utilidades |
| `mision.py` | Misión completa para el visor (fase 1 piloto con bloqueo frontal, fase 2 IA) |
| `evaluar.py` | Comparación IA vs reglas de las primeras versiones (desactualizado) |
| `index.html` | Visor 3D tipo estación de tierra (three.js) |
| `minimo_tesis/` | Mínimo indispensable: sistema, sensores, protocolo del comité, decisor IA (scikit-learn) y repeticiones |
| `herramientas/` | `resumir_metricas.py` (informe corto) y `evaluar_politica.py` (escenarios fijos) |
| `informes/` | Evaluaciones, resúmenes y diagnósticos de cada versión |
| `tests/` | Pruebas: reglas duras, entorno, niveles, V13-V15 y mínimo |
| `modelos/dron_politica.json` | Pesos de la política para la Jetson (sí se versiona) |
| `modelos_*/`, `salida*/`, `*.log` | Modelos, salidas del visor y registros (no se suben) |
| `*_vN.*`, `index_vN.html` | Versiones anteriores de cada archivo (no se editan) |
