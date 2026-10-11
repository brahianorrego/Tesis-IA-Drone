# Evaluación en escenarios fijos · v15-z330-canto

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v14_ultimo.zip`

Política determinista · 100 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 17:13

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 32.0 | 0.97 | 0.05 | 0.05 | 0.2 | 4.4 | 3.8 | -45 / 8 | 14.5 | -0.4 | 2.83 | 1.13 | 4.54 |
| cambio_brusco | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 35.4 | 0.88 | 2.32 | 2.32 | 1.1 | 1.2 | 5.2 | -45 / 4 | 14.9 | -0.2 | 1.52 | 1.56 | 2.96 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 48.8 | 0.73 | 1.22 | 1.22 | 10.0 | 2.9 | 4.3 | -45 / 3 | 17.3 | -0.1 | 0.50 | 0.49 | 1.18 |
| detras_punta | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 47.1 | 0.78 | 1.11 | 1.11 | 9.7 | 3.1 | 3.5 | -45 / 9 | 16.9 | -0.1 | 0.78 | 0.72 | 1.33 |
| detras_punta_4 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 42.7 | 0.84 | 0.99 | 0.99 | 5.9 | 3.8 | 3.7 | -45 / 4 | 16.4 | -0.1 | 0.50 | 0.77 | 1.21 |
| detras_punta_65 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 50.7 | 0.77 | 1.45 | 1.45 | 8.3 | 2.9 | 3.7 | -45 / 7 | 17.4 | -0.1 | 0.94 | 0.74 | 1.50 |
| cambia_lado | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 46.4 | 0.78 | 1.24 | 1.24 | 7.8 | 2.6 | 3.9 | -45 / 9 | 17.2 | -0.1 | 0.48 | 0.73 | 1.15 |
| debajo | 0.84 | 0.16 | 0.00 | 0.00 | 0.00 | 0.00 | 43.5 | 0.75 | 2.62 | 2.46 | 0.9 | 1.9 | 5.5 | -45 / -4 | 11.1 | -0.0 | 2.27 | 4.56 | 3.74 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.06 | 0.04 | 0.01 | 0.00 | 0.01 | 0.53 | 0.01 | 0.19 | 0.14 | 0.01 |
| cambio_brusco | 0.25 | 0.02 | 0.01 | 0.00 | 0.00 | 0.15 | 0.00 | 0.29 | 0.18 | 0.08 |
| tras_muro | 0.37 | 0.16 | 0.06 | 0.00 | 0.00 | 0.05 | 0.00 | 0.17 | 0.13 | 0.05 |
| detras_punta | 0.10 | 0.02 | 0.01 | 0.01 | 0.00 | 0.26 | 0.01 | 0.25 | 0.33 | 0.02 |
| detras_punta_4 | 0.07 | 0.01 | 0.01 | 0.01 | 0.00 | 0.10 | 0.00 | 0.25 | 0.53 | 0.02 |
| detras_punta_65 | 0.11 | 0.03 | 0.02 | 0.01 | 0.00 | 0.23 | 0.00 | 0.23 | 0.33 | 0.02 |
| cambia_lado | 0.10 | 0.11 | 0.01 | 0.01 | 0.00 | 0.06 | 0.00 | 0.14 | 0.54 | 0.02 |
| debajo | 0.30 | 0.04 | 0.01 | 0.00 | 0.00 | 0.10 | 0.00 | 0.19 | 0.22 | 0.15 |
