# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Tesis de grado en Ingeniería Aeronáutica: sistema experimental de detección de personas y evasión de obstáculos para un cuadricóptero en exteriores (con GPS; antes era en interiores), con IA preentrenada y sensores de proximidad. Brahian (@brahianorrego) lleva hardware, electrónica y código; Tania redacta el documento académico.

Contenido: `README.md` (visión general), `docs/` (hardware, Pixhawk, Jetson), `simulacion/` (entorno de RL, entrenamiento PPO y visor 3D) y `jetson/` (código de a bordo, pendiente de copiar desde la Jetson). No hay tests automáticos; la simulación se ejecuta con el `.venv` de `simulacion/` (ver `simulacion/README.md`).

## Arquitectura

Lazo Percepción → Decisión → Control, corriendo en una NVIDIA Jetson Orin Nano:

- **Percepción:** YOLO sobre cámara USB (tracking con `model.track(persist=True)`, exportado a TensorRT `.engine` con `half=True`), LiDAR Benewake TF03 versión UART vía convertidor USB-TTL, y ángulo del gimbal BaseCam (Serial API por mini-USB).
- **Decisión:** arquitectura híbrida. Reglas deterministas (máquina de estados de búsqueda/verificación/pérdida, árbitro de seguridad, seguimiento con banda muerta) más una política PPO entrenada por refuerzo en `simulacion/` (pesos en `simulacion/modelos/dron_politica.json`), que decide solo con el objetivo fijado. La primera versión era un `MLPClassifier` de Scikit-Learn (`decision.pkl`) entrenado con datos etiquetados; se reemplazó por el RL para no depender de etiquetas a mano.
- **Control:** Pixhawk con ArduPilot 4.7 vía MAVLink (TELEM2 a 115200 baud ↔ `/dev/ttyTHS1` de la Jetson, pines 8 y 10; el USB retroalimenta 5 V). El piloto pasa a GUIDED con la posición 3 del interruptor de CH5 para cederle el control a la IA; CH8 es la parada de emergencia. Un "Árbitro de Seguridad" en código tiene la última palabra.
- **Pitch del gimbal:** PWM desde AUX1 de la Pixhawk (SERVO9) con `MAV_CMD_DO_SET_SERVO`, pwm = 1500 + θ·500/45. Los pines PWM del header de la Jetson no dieron una señal usable.
- ROS 2 / Nav2 se descartaron a propósito: la evasión es solo frontal (frenar/ascender).

**Ejes:** Yaw lo controla solo el dron (motor yaw del gimbal desactivado). Roll lo estabiliza el gimbal. Pitch lo estabiliza el gimbal y además lo comanda la Jetson.

## Restricciones de hardware conocidas

- La Jetson se alimenta con un buck DC-DC a 12.02 V después del Power Module PM05.
- La cámara MIPI-CSI se descartó (pantallas verdes, bloqueaba `nvargus-daemon`).
- Failsafe de batería en ArduPilot: 13.5 V / 13.2 V.
- El TF03 es UART, no RS485: no conectarlo directo a los GPIO.

## Forma de trabajo

- Documentación y commits en español.
- En pruebas físicas: un paso a la vez, con instrucciones exactas, y esperar confirmación antes de seguir.
- `main` es la rama principal; se trabaja en ramas y se sube a `origin` (github.com/brahianorrego/Tesis-IA-Drone).
