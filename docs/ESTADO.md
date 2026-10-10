# Estado del proyecto

Actualizado: 2026-10-10 (lo mantiene la skill `/cierre-sesion`).

## Resumen

Dron autónomo que busca, fija y mantiene a la vista a un sospechoso (PPO + reglas + operador humano).
El hardware está configurado y probado en banco; la IA se entrena en simulación y aún no vuela.

## Simulación y entrenamiento

- Código en la versión 10 del encargo (entorno `v8`/`v9` en el docstring): mapa LiDAR + SLAM, 10 acciones,
  `OBS_DRON = 192`, controladores PSC/ATC y gimbal modelados en `control.py`.
- **Entrenamiento master (Stable-Baselines3) en marcha**: 758.9 M pasos al 2026-10-10 08:40, 38.9 h
  acumuladas, nivel de currículo 0.16. Meta de la corrida: 1 000 M.
- Mejor referencia anterior: v9 con pesos v8 sin reentrenar → cumplida 44 %, perdido 26 %, alcanzado 15 %.
- Lo que falta medir: evaluación comparativa IA vs reglas (`evaluar.py` está desactualizado).

## Modelos (fuera de Git)

- `simulacion/modelos_master/`: 761 archivos `.zip`, 1 135 MB en total (cada uno ≈ 1.5 MB). Hay un
  checkpoint por millón de pasos más `ultimo.zip` y `base_v9.zip`.
- `simulacion/modelos/dron_politica.json`: pesos exportados para la Jetson (sí está en Git).
- Respaldo: ver "Pendientes" (aún no se ha hecho).

## Hardware

- Pixhawk (ArduPilot 4.7) ↔ Jetson por TELEM2 a 115200; pitch del gimbal por AUX1; LiDAR TF03; cámara USB.
- Batería LiPo 4S original sobredescargada: **retirada**; no volar con ella.
- Detalle en `hardware.md`, `pixhawk.md` y `jetson.md`.

## Git

- Rama de trabajo nueva: `v11-hibrido` (parte de la etiqueta `v10-master-759M`). La rama `docs/proyecto-completo-v6` sigue con el PR #2 abierto, sin fusionar.
- Todo lo local está subido a GitHub (2026-10-10); no hay commits pendientes.
- Etiqueta `v10-master-759M` creada y subida (congela el código de la V10, 759 M pasos).

## Pendientes (por prioridad)

1. Decidir el límite del gimbal: el código usa -60° y la regla dura dice -45° (D-014).
3. Respaldar `modelos_master/` fuera de Git (Google Drive o un Release de GitHub).
4. Fusionar el PR #2 a `main` (lo hace Brahian en GitHub).
5. Copiar el código de la Jetson (`~/Escritorio/dron_ia`) a `jetson/` cuando esté encendida.
6. Llevar la política a la Jetson: sus entradas deben calcularse igual que en `entorno.py`.
7. Validación sim-to-real con datos de campo; evaluar la cuadrícula de la cámara al sol.
8. Decidir si la búsqueda tras perder el objetivo queda a cargo de la IA o determinista (D-015).
