# Decisiones de diseño

Cada decisión lleva fecha, el motivo y las alternativas descartadas. Lo más reciente abajo.
Las marcadas **ABIERTA** esperan respuesta de Brahian.

| ID | Fecha | Decisión | Motivo / alternativas |
|---|---|---|---|
| D-001 | 10-05 | Yaw lo hace solo el dron; el gimbal tiene 2 ejes (roll estabiliza, pitch se comanda) | Motor de yaw desactivado. La entrada "ángulo de paneo" se reemplazó por el ángulo de la persona respecto a la nariz |
| D-002 | 10-06 | La cámara es USB, no MIPI-CSI | La CSI daba pantallas verdes y bloqueaba `nvargus-daemon` |
| D-003 | 10-07 | Pitch del gimbal por AUX1 de la Pixhawk con `DO_SET_SERVO` | Los pines PWM 32/33 de la Jetson no dieron señal. Descartado `MNT1_TYPE=1`: doble estabilización |
| D-004 | 10-07 | Enlace Jetson–Pixhawk por TELEM2 a 115200, sin 5 V | El USB retroalimentaba 5 V; a 460800 y 921600 la Pixhawk no entendía a la Jetson |
| D-005 | 10-07 | El proyecto es en exteriores (GPS, GUIDED) | Aclaración de Brahian. Se revirtió la configuración de interiores |
| D-006 | 10-07 | La IA #2 se entrena por refuerzo en simulación | Brahian no quiere etiquetar a mano; el RL no necesita etiquetas. Inspirado en Baker et al. 2020 |
| D-007 | 10-07 | El operador humano designa al sospechoso con un clic | YOLO solo detecta "persona"; ética y técnica. Nunca cambia de objetivo solo |
| D-008 | 10-07 | Árbitro de seguridad solo ante amenaza real (< 3 m o < 8 m acercándose) | Antes el dron se trababa 2.5 s esquivando a personas lejanas |
| D-009 | 10-07 | Misión en dos fases: piloto con bloqueo frontal, IA en la zona | Alcance aclarado por Brahian; el objetivo es mantener la vista, no solo salvar el dron |
| D-010 | 10-08 | Arquitectura híbrida: reglas deterministas + política PPO | Lo predecible y auditable va en reglas; la red decide solo con el objetivo fijado |
| D-011 | 10-08 | Mapa LiDAR propio, sin usar el plano del simulador | Para que la política dependa solo de lo que el dron real puede medir |
| D-012 | 10-08 | Autoría visible en el visor | Pedido de Brahian ("Fase de Autoría") |
| D-013 | 10-08 | Pasar a Stable-Baselines3 con transferencia desde la v9 | Congelar la capa inferior (lo aprendido en 300+ M pasos) y afinar lo nuevo |
| D-014 | 10-10 | Límite del gimbal ESTRICTO: -45°..+15° (el código se ajusta a la regla) | Brahian: la BaseCam física no pasa de -45° y forzarla quema los motores. Antes el código permitía -60° y se había documentado así; se revirtió el mismo día. Cambia `entorno.py` (MIN, NADIR, TACTICO) y `control.py`; copias previas en `*_v10.py` |
| D-015 | 10-10 | Búsqueda al perder el objetivo DETERMINISTA (`PERDIDA_IA = False`) en la rama `v11-hibrido` | Brahian: la meta de la rama es la máquina de estados determinista con SLAM para rodear muros. Verificado: con False se recorren PREDECIR, INVESTIGAR, ASOMO y VENTAJA_ALTURA. Los modelos de la V10 se entrenaron con IA y hay que reentrenarlos |
| D-016 | 10-10 | Los modelos `.zip`/`.pt` no van a Git | Pesan 1.1 GB; se respaldan en Google Drive o en un Release de GitHub |
| D-017 | 10-10 | La etiqueta se llama `v10-master-759M` | Brahian eligió el nombre que coincide con el estado real (759 M pasos); `350M` no lo reflejaba |
| D-018 | 10-10 | Ciclo de mejora con informes y dos agentes (`supervisor-rl`, `implementador`) y pruebas en `simulacion/tests/` | El supervisor diagnostica sin tocar código y propone máximo 3 cambios; Brahian aprueba; el implementador aplica con pruebas |
| D-019 | 10-10 | Respaldo de modelos: Release de GitHub con lo esencial (10 archivos, 12 MB) y copia completa en Google Drive | Release `v10-master-759M`: `ultimo.zip`, `base_v9.zip`, `ladron_congelado.pt` y un checkpoint cada 100 M. Los 761 checkpoints (1,1 GB) los copia Brahian a mano a Drive |
