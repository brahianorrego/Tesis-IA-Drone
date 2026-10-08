# Simulación: dron vs ladrón (aprendizaje por refuerzo multiagente)

Entrena la IA de decisión del dron por refuerzo en un mundo virtual, sin datos etiquetados a mano.
El juego es el **dron contra el ladrón** (autojuego, como *Emergent Tool Use From Multi-Agent
Autocurricula*, Baker et al., ICLR 2020). El dron tiene que encontrar al sospechoso, esperar a que el
operador lo confirme y mantenerlo a la vista 30 s. El ladrón se esconde detrás de los paneles y a veces
ataca. Los peatones son obstáculos.

El dron virtual percibe el mundo igual que el real: cámara de 38.9°, YOLO con ruido y pérdidas, LiDAR
frontal, 100 ms de retraso, gimbal de pitch, y la posición, el rumbo y la altura que da la Pixhawk.
La lógica de la versión 6 (arquitectura híbrida) está descrita en el [README principal](../README.md#arquitectura-híbrida---versión-6).

## Uso (Windows)

| Qué | Cómo |
|---|---|
| Ver la simulación y las curvas de aprendizaje | doble clic en `ABRIR_VISOR.bat` → http://127.0.0.1:8765/ |
| Retomar el entrenamiento | doble clic en `CONTINUAR_ENTRENAMIENTO.bat` |
| Entrenamiento nuevo | `.venv\Scripts\python.exe -u entrenar.py --pasos 600e6` (`--desde <modelo.pt>` para partir de pesos previos) |
| Experimento comparativo (IA vs reglas) | `.venv\Scripts\python.exe evaluar.py` → `salida/evaluacion.json` |

El entorno virtual `.venv` (torch CPU + numpy) no se sube al repositorio. Para crearlo:
`py -m venv .venv` y luego `.venv\Scripts\pip install torch numpy`.

## Archivos

- `entorno.py`: el mundo vectorizado en NumPy, los sensores, la máquina de estados, el árbitro y las recompensas.
- `entrenar.py`: PPO para los dos agentes. Guarda métricas y repeticiones (`salida/`, no se sube) y modelos (`modelos/`).
- `mision.py`: misión completa para el visor (fase 1 con el piloto y bloqueo frontal, fase 2 con la IA).
- `evaluar.py`: compara la IA contra reglas escritas a mano en los mismos escenarios.
- `index.html`: visor 3D tipo estación de tierra (three.js), con la cámara FPV, la telemetría y las gráficas en vivo.
- `modelos/dron_politica.json`: pesos de la red del dron, para cargarla en la Jetson.
- `*_v2` … `*_v5`, `index_v4` … `index_v7`, `modelos_v1` … `modelos_v5`: versiones anteriores de cada experimento.
