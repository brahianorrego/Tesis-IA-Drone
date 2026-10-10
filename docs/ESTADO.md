# Estado del proyecto

Actualizado: 2026-10-10 (lo mantiene la skill `/cierre-sesion`).

## Resumen

Dron autónomo que busca, fija y mantiene a la vista a un sospechoso (PPO + reglas + operador humano).
El hardware está configurado y probado en banco; la IA se entrena en simulación y aún no vuela.

## Simulación y entrenamiento

- Rama `v11-hibrido`: gimbal estricto en **-45°..+15°** (D-014) y búsqueda tras perder el objetivo
  **determinista**, `PERDIDA_IA = False` (D-015). Probado: el gimbal toca -45,00° y nunca baja; con la
  bandera en False se recorren PREDECIR, INVESTIGAR, ASOMO y VENTAJA_ALTURA. 17 pruebas pasan.
- Código base: V10 (entorno `v8`/`v9` en el docstring): mapa LiDAR, 10 acciones, `OBS_DRON = 192`,
  controladores PSC/ATC y gimbal modelados en `control.py`. Copias previas a los cambios: `*_v10.py`.
- **Entrenamiento master (SB3) en marcha** con las reglas VIEJAS (-60° y búsqueda por IA), porque cargó
  el código antes del cambio: 766.8 M pasos, 39.6 h, nivel 0.18 (2026-10-10). Para entrenar con las reglas
  nuevas hay que pararlo y reiniciarlo (decisión de Brahian); sus modelos hay que reentrenarlos o afinarlos.
- Referencia: V9 con pesos v8 sin reentrenar → cumplida 44 %, perdido 26 %, alcanzado 15 %.
- Evaluación en escenarios fijos y resúmenes: `simulacion/herramientas/` → `simulacion/informes/`.
  Pruebas: `simulacion/tests/`. Agentes: `.claude/agents/` (`supervisor-rl`, `implementador`).

## Modelos

- `simulacion/modelos_master/` (fuera de Git): 761 `.zip`, 1 135 MB. Brahian los copia a mano a Google Drive.
- **Release `v10-master-759M`** en GitHub: 10 archivos, 12 MB (`ultimo.zip`, `base_v9.zip`,
  `ladron_congelado.pt` y un checkpoint cada 100 M pasos hasta 700 M).
- `simulacion/modelos/dron_politica.json`: pesos exportados para la Jetson (sí está en Git).

## Hardware

- Pixhawk (ArduPilot 4.7) ↔ Jetson por TELEM2 a 115200; pitch del gimbal por AUX1 (`pwm = 1500 + θ·500/45`).
- Batería LiPo 4S original sobredescargada: **retirada**; no volar con ella.
- Detalle en `hardware.md`, `pixhawk.md` y `jetson.md`.

## Git

- Rama de trabajo: `v11-hibrido`. Etiqueta `v10-master-759M` (código de la V10, 759 M pasos).
- PR #2 (`docs/proyecto-completo-v6`) abierto, sin fusionar: lo hace Brahian en GitHub.

## Pendientes (por prioridad)

1. Reforzar la máquina de estados determinista con el mapa LiDAR (SLAM) para rodear los muros.
2. Decidir cuándo parar el entrenamiento viejo y reentrenar con las reglas nuevas (-45° y búsqueda determinista).
3. Brahian: copiar `modelos_master/` (1,1 GB) a Google Drive.
4. Ciclo de mejora: pasar `informes/resumen_*` y `barrido_*` a `supervisor-rl` y decidir sus cambios.
5. Fusionar el PR #2 a `main`.
6. Copiar el código de la Jetson (`~/Escritorio/dron_ia`) a `jetson/` cuando esté encendida.
7. Llevar la política a la Jetson: sus entradas deben calcularse igual que en `entorno.py`.
8. Validación sim-to-real con datos de campo; evaluar la cuadrícula de la cámara al sol.
