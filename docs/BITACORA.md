# Bitácora

Registro cronológico, lo más reciente arriba. Lo agrega la skill `/cierre-sesion` al terminar cada sesión.
Fechas de 2026.

## 10 de octubre
- v11-hibrido: gimbal estricto en -45° (D-014) y búsqueda determinista `PERDIDA_IA = False` (D-015), por decisión de Brahian. Antes se había ajustado la regla al código (-60°, IA); se revirtió el mismo día. Pruebas de reglas duras actualizadas (17, pasan).
- Ciclo de mejora: agentes `supervisor-rl` e `implementador`, `resumir_metricas.py` y `evaluar_politica.py` (4 escenarios fijos); barrido de toda la V10.
- Release `v10-master-759M` en GitHub con los modelos esenciales (10 archivos, 12 MB). El entrenamiento viejo sigue corriendo con las reglas anteriores (766.8 M pasos).
- El entrenamiento master (Stable-Baselines3) sigue corriendo: 759 M pasos, 761 archivos de modelo (1.1 GB).
- Se ordenó el repositorio: `.gitignore` con modelos, salidas y secretos; `CLAUDE.md` y `docs/` nuevos.
- Se detectó que `.zip` no estaba ignorado: un `git add .` habría subido 759 checkpoints.
- Etiqueta nombrada `v10-master-759M` (la corrida ya iba en 759 M, no en 350 M).

## 8 de octubre
- Se subió al repositorio la simulación v6 y la documentación del hardware (PR #2).
- Versiones v7 a v9: mapa LiDAR, búsqueda activa tras los paneles, ladrón con saltos y campos potenciales,
  gimbal con límite duro, jerk del autopiloto, observación de 192 entradas.
- Búsqueda tras perder el objetivo a cargo de la IA (`PERDIDA_IA = True`), para compararla con la determinista.
- Se agregó la autoría de Brahian al visor (barra superior y letras 3D en el piso).
- Nace `entrenar_master.py` (SB3, transferencia de la v9, ladrón congelado en el 30 % de las partidas).

## 7 de octubre
- El proyecto de grado pasa a **exteriores** (GPS, modo GUIDED). Alcance en dos fases: piloto traslada, IA vigila.
- Pixhawk configurada: modos de vuelo por CH5, parada de emergencia en CH8, enlace TELEM2 a 115200.
- Pitch del gimbal por AUX1 (`DO_SET_SERVO`): los pines PWM de la Jetson no daban señal.
- Cámara: HFOV medido 38.9°; cuadrícula por falta de filtro IR-cut; YOLO26n en TensorRT a 90+ FPS.
- Yaw hacia la persona en `vuelo_evasion.py`. LiPo 4S sobredescargada: retirada.
- Simulación RL v1 a v5: del "dron esquiva" al "dron mantiene al ladrón a la vista" con operador humano.

## 6 de octubre
- LiDAR TF03 validado (driver `pl2303`). Gimbal de 2 ejes: lectura por USB, el control por serie no responde.
- Primera versión del repositorio y primer Pull Request (README).

## 5 de octubre
- Hardware configurado; arranca el Paso 1 de la hoja de ruta (validar el LiDAR).
