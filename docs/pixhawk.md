# Configuración de la Pixhawk (ArduPilot 4.7.0)

Solo se listan los parámetros que se cambiaron o que importan para el proyecto. Antes de tocar nada se
guardó un respaldo de los 1009 parámetros originales (fuera del repositorio).

## Enlace con la Jetson

| Parámetro | Valor | Motivo |
|---|---|---|
| `SERIAL2_PROTOCOL` | MAVLink 2 | TELEM2 = enlace con la Jetson |
| `SERIAL2_BAUD` | 115 (115200) | A 460800 y 921600 la Pixhawk no entiende lo que transmite la Jetson |
| `BRD_SER2_RTSCTS` | 0 | El cable solo lleva TX, RX y GND |

## Modos de vuelo y seguridad (exteriores)

| Parámetro | Valor | Significado |
|---|---|---|
| `FLTMODE_CH` | 5 | El interruptor de 3 posiciones de CH5 elige el modo |
| `FLTMODE1` | STABILIZE | CH5 abajo (~1095 µs) |
| `FLTMODE4` | ALT_HOLD | CH5 al medio (~1515 µs) |
| `FLTMODE6` | GUIDED | CH5 arriba (~1935 µs): **la IA toma el control** |
| `RC8_OPTION` | 31 | CH8 = parada de emergencia de motores |
| `FS_THR_ENABLE` | 1 | Pérdida de radio → RTL |
| `BATT_FS_LOW_ACT` | 2 | Batería baja → RTL (umbrales 13.5 V / 13.2 V por la caída de voltaje bajo carga) |

## Gimbal (pitch por AUX1)

| Parámetro | Valor | Motivo |
|---|---|---|
| `MNT1_TYPE` | 0 | Sin librería de gimbal: ArduPilot compensaría la actitud y, sumado a la BaseCam, habría doble estabilización |
| `SERVO9_FUNCTION` | 0 | Salida libre, la maneja la Jetson con `DO_SET_SERVO` |
| `SERVO9_MIN / TRIM / MAX` | 1000 / 1500 / 2000 | ±45° del gimbal |
| `BRD_SAFETY_MASK` | 16368 | Las salidas 5–14 funcionan aunque el seguro esté puesto (para el banco) |

## Cómo comprobar el enlace

Para probar que la Pixhawk recibe a la Jetson, lo más confiable es `DO_SET_SERVO` + `COMMAND_ACK`
(o leer `SERVO_OUTPUT_RAW.servo9_raw`). Las respuestas de `PARAM_REQUEST_READ` se pierden a 115200
cuando el canal va lleno de telemetría.
