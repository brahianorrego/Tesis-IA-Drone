# Jetson Orin Nano: software y puesta a punto

## Sistema

- Ubuntu 24.04, L4T R39.2.1 (JetPack 7), sistema operativo en NVMe.
- Entorno Python 3.12 (`~/dron_env`): torch 2.14 + CUDA 13, ultralytics 8.4, TensorRT 10.16,
  OpenCV 4.6, pyserial, pymavlink 2.4, Jetson.GPIO.
- Para la inferencia se usa TensorRT. El PyTorch instalado funciona en la Orin, aunque no está
  compilado oficialmente para su arquitectura (CC 8.7).

## Puertos

| Dispositivo | Puerto | Velocidad |
|---|---|---|
| Pixhawk (vuelo) | `/dev/ttyTHS1` (UARTA, pines 8 y 10) | 115200 |
| Pixhawk (banco) | USB, ruta `/dev/serial/by-id/usb-ArduPilot_fmuv3_…` | — |
| LiDAR TF03 | `/dev/ttyUSB0` (PL2303) | 115200, 100 Hz |
| Gimbal BaseCam | `/dev/ttyACM0` (CH9102) | 115200, protocolo `>` |
| Cámara | `/dev/video0` | 640×480 |

`config.py` usa las rutas `by-id` para que los puertos no cambien de nombre al reconectar.

## Código de a bordo (`~/Escritorio/dron_ia/`)

| Archivo | Qué hace |
|---|---|
| `config.py` | Todos los parámetros (puertos, HFOV, ganancias, umbrales) |
| `percepcion.py` | Cámara + YOLO TensorRT con tracking; ajusta los controles de la cámara al abrirla |
| `lidar_tf.py` | Lectura del TF03 |
| `gimbal_basecam.py` | Telemetría de la BaseCam (REALTIME_DATA) |
| `sensores.py`, `comun.py` | Fusión de sensores y utilidades |
| `vuelo_evasion.py` | Lazo principal: percepción → árbitro → MAVLink (GUIDED con velocidades y `yaw_rate` hacia la persona) |
| `grabar_dataset.py`, `entrenar_mlp.py` | Grabación de datos y clasificador MLP (primera versión de la IA de decisión) |
| `visor_web.py`, `capturar_patron.py`, `correccion_camara.py` | Visor web de la cámara y corrección del patrón fijo del sensor |

> El código de la Jetson se copiará a la carpeta [`jetson/`](../jetson/) del repositorio la próxima vez
> que la Jetson esté encendida y en red.

## Puesta a punto (lo que hubo que hacer)

1. **Driver `pl2303`** para el adaptador del LiDAR: se compila e instala en
   `/lib/modules/$(uname -r)/extra`. Hay que repetirlo si se actualiza el kernel.
2. **Permisos de puertos serie:** el usuario debe estar en el grupo `dialout`.
3. **ModemManager desactivado**, porque interfiere con los puertos serie.
4. **Gimbal:** `stty -F /dev/ttyACM0 -hupcl` evita que la placa se reinicie al abrir el puerto (se
   pierde al reconectar el USB). Tras abrir el puerto, la placa tarda unos 10 s en enviar datos válidos.
5. **Cámara:** `exposure_dynamic_framerate=0` y `power_line_frequency=2` (60 Hz). No usar el zoom
   digital, porque cambia el HFOV.
6. **YOLO:** el `.engine` de TensorRT se genera en la propia Jetson (FP16, unos 7 minutos), porque no
   es portable entre equipos.
7. **Pines PWM del header:** se probaron los pines 32 y 33 (incluso corrigiendo el overlay de pinmux),
   pero no dieron una señal usable. El PWM del gimbal sale de la Pixhawk.
