# Hardware del dron

Cuadricóptero en configuración X con computadora de a bordo para la IA. Este documento describe los
componentes, cómo están conectados y los problemas de hardware que se resolvieron en el camino.

## Componentes

| Función | Componente | Notas |
|---|---|---|
| Controladora de vuelo | Pixhawk (fmuv3) con ArduPilot 4.7.0 | Quad X (`FRAME_CLASS=1`, `FRAME_TYPE=1`). Ver [pixhawk.md](pixhawk.md). |
| Computadora de a bordo | NVIDIA Jetson Orin Nano | Ubuntu 24.04, L4T R39.2.1 (JetPack 7), SO en NVMe. Ver [jetson.md](jetson.md). |
| Cámara | Webcam USB Sonix (640×480) | HFOV medido 38.9°, VFOV ≈ 29.7°. Sin filtro IR-cut. |
| Detección de personas | YOLO26n exportado a TensorRT FP16 | 9–11 ms por cuadro en la Orin, con tracking. |
| Sensor de distancia | LiDAR Benewake TF03 (versión UART) | Por convertidor USB-TTL Prolific PL2303. 100 Hz. |
| Gimbal | BaseCam SimpleBGC v1.0 (8 bits, firmware 2.2 b2) | 2 ejes activos: roll (solo estabiliza) y pitch (estabiliza y lo comanda la Jetson). Motor de yaw desactivado. |
| Radio | Emisora Futaba + receptor | CH5 = modo de vuelo, CH8 = parada de emergencia. |
| Energía | LiPo 4S + Power Module PM05-V1.0 | Buck DC-DC a 12.02 V para la Jetson. |
| GPS | Módulo GPS de la Pixhawk | El proyecto de grado es en **exteriores** (modo GUIDED con GPS). |

## Diagrama de conexiones

```
                       ┌──────────────── LiPo 4S ────────────────┐
                       │                                         │
                 Power Module PM05                          ESC + motores
                   │         │
             Pixhawk (POWER)  Buck DC-DC 12.02 V ──► Jetson Orin Nano
                                                       │
   Pixhawk TELEM2 ◄──── UART 115200 (pines 8, 10, 6) ──┤  /dev/ttyTHS1  (MAVLink)
   Pixhawk AUX1 (SERVO9) ── PWM 50 Hz ──► BaseCam entrada RC_PITCH
                                                       │
   LiDAR TF03 ── USB-TTL PL2303 ───────────────────────┤  USB  (/dev/ttyUSB0)
   BaseCam ── mini-USB (telemetría REALTIME_DATA) ─────┤  USB  (/dev/ttyACM0)
   Cámara Sonix ───────────────────────────────────────┘  USB  (/dev/video0)
```

### Cable TELEM2 ↔ Jetson ("TELEM2.2")

DF13 de 6 pines (contacto 1 = rojo) hacia un conector Dupont de 3 hembras en el header de 40 pines:

| DF13 (Pixhawk TELEM2) | Señal | Cable | Pin de la Jetson |
|---|---|---|---|
| 2 | TX de la Pixhawk | blanco | 10 (RX, UARTA) |
| 3 | RX de la Pixhawk | **rojo** (lleva datos, no 5 V) | 8 (TX, UARTA) |
| 6 | GND | negro | 6 (GND) |
| 1, 4, 5 | 5 V, CTS, RTS | cortados y aislados | — |

Se cortó el 5 V a propósito: con la batería conectada, la Pixhawk metía 5 V hacia la Jetson por el
USB (retroalimentación). Por eso el enlace de vuelo va por UART y el USB solo se usa en el banco.

### Pitch del gimbal

La Jetson ordena el ángulo con `MAV_CMD_DO_SET_SERVO(9, pwm)` y la Pixhawk genera el pulso por AUX1:

```
pwm = 1500 + θ · 500 / 45      (θ en grados, ±45° → 1000–2000 µs)
```

## Problemas de hardware resueltos

| Problema | Causa | Solución |
|---|---|---|
| La Raspberry Pi 4 no daba abasto | Falta de cómputo para YOLO | Se cambió a Jetson Orin Nano |
| Cámara MIPI-CSI con pantallas verdes y `nvargus-daemon` bloqueado | Cámara/driver CSI | Cámara USB |
| "11.8 FPS" históricos | `exposure_dynamic_framerate=1` de la cámara bajaba los FPS con poca luz (y PyTorch sin GPU) | Desactivar ese control y usar TensorRT FP16: ~30 FPS con luz |
| LiDAR TF03 no se veía | Es UART, no RS485; faltaba el driver `pl2303` en el kernel L4T | Convertidor USB-TTL y driver compilado para el kernel |
| El gimbal se reiniciaba al abrir el puerto | Línea DTR del CH9102 | `stty -F /dev/ttyACM0 -hupcl` |
| El gimbal no obedece `CMD_CONTROL` por serie | Firmware 2.2 de 8 bits | Serie solo para telemetría; el pitch se comanda por PWM |
| Los pines PWM 32/33 de la Jetson no entregan señal usable | Pinmux de L4T R39 (tristate) y salida débil | El PWM sale de AUX1 de la Pixhawk |
| La Pixhawk no entendía a la Jetson a 921600 | Imprecisión del baud del UART de la Jetson al transmitir | Enlace a 115200 |
| Cuadrícula de manchas y tinte morado en la imagen | Cámara sin filtro IR-cut | En interiores no afecta a YOLO; se evalúa un filtro IR-cut para el sol |
| LiPo sobredescargada (una celda en 1.99 V) | Horas de pruebas de banco con todo alimentado; el failsafe solo actúa armado | Batería retirada. En banco se vigila el voltaje por MAVLink (aviso a 14.4 V, desconectar a 14.0 V) |
