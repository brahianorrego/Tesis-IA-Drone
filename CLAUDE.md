# CLAUDE.md

Guía para Claude Code en este repositorio. Estado actual del trabajo: @docs/ESTADO.md

## Qué es este proyecto

Proyecto de grado de Ingeniería Aeronáutica: un cuadricóptero autónomo que **mantiene a la vista a un
sospechoso** (caso de uso policial) en exteriores, con GPS. Corre en una Jetson Orin Nano y le da órdenes
a una Pixhawk (ArduPilot 4.7) por MAVLink. Autor: Brahian Andrés Orrego Osorio (@brahianorrego). Tania
redacta el documento académico.

La IA de decisión es una **política PPO entrenada por refuerzo en simulación** (dron contra ladrón, por
autojuego), con reglas deterministas alrededor y un operador humano que confirma al sospechoso.

## Convenciones

- Se escribe **"proyecto de grado"**, nunca "tesis", en todos los textos nuevos (README, docs, informes).
  Excepciones: el nombre del repositorio (`Tesis-IA-Drone`) y comentarios antiguos dentro del código,
  que no se tocan.
- Documentación, commits y respuestas en español. Brahian no es programador: explicar en lenguaje sencillo.
- Pedir confirmación antes de lo que no se pueda deshacer (push, etiquetas remotas, borrados, merge).
- Pruebas físicas: un paso a la vez, con instrucciones exactas, esperando confirmación.
- **No cambiar la lógica de los scripts** salvo que se pida. Antes de reescribir un archivo, dejar copia
  `_vN` (así se ha trabajado hasta ahora).
- El repositorio es **público**: no subir IPs, usuarios, contraseñas, claves ni rutas internas.

## Reglas duras del sistema (no negociables)

1. **Gimbal: nunca por debajo de -45°.** Es el límite real de la BaseCam (±45°) y del mapeo PWM de AUX1
   (`pwm = 1500 + θ·500/45`). ⚠ El código actual NO lo cumple: `entorno.py` y `control.py` usan -60°..+15°
   (ver D-014 en docs/DECISIONES.md). No arreglar sin que Brahian lo decida.
2. **Geocerca:** el dron no sale de la arena (`ARENA = 25 m` en simulación). Salir = misión fallida y
   recompensa `R_GEOCERCA = -5`. En el dron real la geocerca la fija ArduPilot.
3. **Búsqueda determinista al perder el objetivo** (meta de la rama `v11-hibrido`): investigar la última
   posición → asomo/barrido de 360° → ventaja de altura → recién ahí "perdido". ⚠ Hoy `PERDIDA_IA = True`
   en `entorno.py` deja esa búsqueda a la política; con `False` vuelve el protocolo determinista.
4. **Humano en el lazo:** la IA nunca decide quién es el sospechoso. Lo confirma el operador con un clic
   y nunca cambia de objetivo por su cuenta.
5. **Árbitro de seguridad:** solo autoriza evadir ante amenaza real (persona a < 3 m, o a < 8 m
   acercándose). El bloqueo frontal por LiDAR (< 3 m) y la parada de emergencia (CH8) mandan sobre la IA.
6. La red **no estabiliza nada**: la estabilidad la dan los PID de ArduPilot y del gimbal.

## Mapa de archivos

| Ruta | Qué es |
|---|---|
| `README.md` | Visión general, misión, arquitectura híbrida, historial de versiones |
| `docs/` | `ESTADO.md` (dónde vamos), `BITACORA.md`, `DECISIONES.md`, `hardware.md`, `pixhawk.md`, `jetson.md` |
| `jetson/` | Código de a bordo (pendiente de copiar desde la Jetson) |
| `.claude/skills/cierre-sesion/` | Skill para cerrar cada sesión (resumen, docs, commit) |
| `simulacion/entorno.py` | Mundo vectorizado en NumPy: sensores, mapa LiDAR, máquina de estados, ladrón táctico, recompensas |
| `simulacion/control.py` | Modelo de los controladores reales: cascada PSC/ATC de ArduPilot y PID del gimbal BaseCam |
| `simulacion/entrenar_master.py` | Entrenamiento actual: PPO de Stable-Baselines3 con transferencia desde la v9 |
| `simulacion/entrenar.py` | PPO propio en torch (versiones v1–v9) y utilidades que reutiliza el master |
| `simulacion/mision.py` | Misión completa para el visor (fase 1 piloto + fase 2 IA) |
| `simulacion/evaluar.py` | Comparación IA vs reglas (desactualizado: revisar antes de usar) |
| `simulacion/index.html` | Visor 3D tipo estación de tierra (three.js) |
| `simulacion/*_vN.*` | Versiones anteriores de cada archivo (no editar) |
| `simulacion/modelos/dron_politica.json` | Pesos de la política para la Jetson (sí se versiona) |
| `simulacion/modelos_master/` | Modelos SB3 (`ultimo.zip`, `base_v9.zip`, un checkpoint por millón de pasos). **No va a Git** |

`parche_master_humanos.py` se mencionó en un encargo pero **no existe** en el repositorio.

## Comandos (Windows, desde `simulacion\`)

```
:: entrenar (retoma modelos_master\ultimo.zip)
.venv\Scripts\python.exe -u entrenar_master.py --continuar

:: primera vez desde una política propia
.venv\Scripts\python.exe -u entrenar_master.py --base modelos\ultimo.pt --pasos 1e9

:: visor 3D en http://127.0.0.1:8765/
ABRIR_VISOR.bat

:: comprobar que el entorno importa
.venv\Scripts\python.exe -c "import entorno"

:: evaluar (IA vs reglas): revisar antes, usa claves de versiones viejas
.venv\Scripts\python.exe evaluar.py --partidas 2000
```

- Con el entrenamiento en marcha, `modelos_master\ultimo.zip` y `salida\` cambian a cada rato: no copiarlos
  ni moverlos sin pararlo antes.
- `CONTINUAR_ENTRENAMIENTO.bat` sigue llamando al `entrenar.py` viejo; el master se lanza a mano.
- No hay tests automáticos. Para validar un cambio: importar `entorno`, correr unos pasos y mirar el visor.
- El `.venv` no está en Git. Si falta: `py -m venv .venv` e instalar `torch numpy gymnasium stable-baselines3`.

## Git

- Rama principal `main`. Se trabaja en ramas y se sube con Pull Request.
- Etiqueta `v10-master-759M` congela el estado de la V10 (759 M pasos); rama `v11-hibrido` para el trabajo nuevo.
- Los modelos `.zip`/`.pt`, `salida*/`, logs, `.venv` y secretos están en `.gitignore`.
- Commits en español y con coautoría de Claude al final del mensaje.
- Para cerrar una sesión usar la skill `/cierre-sesion`.
