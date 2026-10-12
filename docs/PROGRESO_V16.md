# Progreso de la V16

Avance de las dos sesiones en la nube del plan `docs/PLAN_V16_REALISMO.md`. Cada fase deja una entrada: fecha, sesión,
qué se hizo, números medidos y qué sigue. Lo más reciente va abajo.

**Cómo se mide en la nube.** Los modelos `.zip` no están en Git, así que las mediciones usan la política de la V15 que sí
está en el repositorio (`simulacion/modelos/dron_politica.json`, 182 M pasos, la que va a la Jetson) **sin reentrenar**,
con `simulacion/herramientas/medir_v16.py` (partidas de 5 min de la misión V16). Sirve para comparar cada cambio con y
sin él; los números finales los dará el entrenamiento en el portátil.

---

## Fase A1 · Escenario y alturas (Sesión A, 2026-10-12)

**Qué se hizo** (`simulacion/entorno.py`, copia previa `entorno_v15b.py`):
- **Partida única**: misión completa con **2 paneles** de 4 a 6.5 m (2.6 m de alto), 0-2 civiles y el ladrón táctico
  (siempre el táctico: es el que tendrá posturas y salto). Es el "nivel" `NIVEL_V16 = 5`, fuera de los 5 niveles de la V15,
  que se conservan para comparar. Es el valor por defecto del entorno.
- **Civiles** que atraviesan la zona caminando tranquilos (1.1-1.5 m/s) de un borde al opuesto, rodeando los muros. Nacen
  a más de 9 m del dron. (Sus reacciones al ver el dron llegan en la fase A2.)
- **Alturas variables** (decisión 3): 2.5 m en el 360° de entrada, 3.0 m en tránsito y 2.0 m al inspeccionar detrás de un
  muro, **solo sin personas conocidas a menos de 8 m**. Con alguien cerca, nunca por debajo de **3.30 m** (D-043).
  "Conocida" es lo que el dron sabe: la persona que ve ahora, la que vio en los últimos 20 s y pudo seguir cerca, y el
  sospechoso designado mientras pudiera estar a menos de 8 m (corriendo a 2.5 m/s desde donde se lo vio por última vez).
- **Transiciones suaves**: la altura objetivo va en rampa (baja a 0.4 m/s, sube a 0.8 m/s y, con alguien cerca, sube a
  2.5 m/s como ArduPilot); nunca da un escalón.
- Arreglo del ladrón: con muros superpuestos, "cambiar de cubierta" elegía el mismo muro 2 de cada 3 veces; en la V16 va
  al otro muro.
- Herramientas nuevas: `herramientas/politica_json.py` (la política de la Jetson como referencia) y
  `herramientas/medir_v16.py` (medición rápida con `--set CONSTANTE=valor` para comparar con y sin un cambio).

**Hallazgo importante.** La primera versión bajaba a 2.0 m detrás del muro porque la nube de partículas ponía al ladrón
lejos; pero el ladrón táctico sigue la sombra del muro y estaba a 2-5 m sin que el dron lo viera: lo alcanzaba en 1 de
cada 2 partidas. Por eso, una vez designado el sospechoso, se lo considera "cerca" mientras pudiera haber llegado a menos
de 8 m. En la práctica las alturas bajas quedan para antes de encontrarlo (entrada, tránsito, inspección de la búsqueda
inicial) y para cuando está lejos de verdad.

**Números** (192 partidas de 5 min, política V15 sin reentrenar):

| | Con alturas variables | Sin ellas (siempre 3.30 m) |
|---|---:|---:|
| Custodia ≥ 60 s | 97.9 % | 97.4 % |
| Custodia ≥ 90 s | 79.7 % | 78.1 % |
| Rendición | 12.5 % | 7.3 % |
| Alcanzado por el ladrón | 0.5 % (1 partida) | 0 % |
| Perdido | 0 % | 1.0 % |
| Tiempo bajo 3.30 m | 1.5 % | 0.4 % |
| Bajo 3.30 m con una persona REAL a < 8 m (vista o no) | 0.5 % de ese tiempo | 0.02 % |

- Las alturas bajas no empeoran la custodia. En las corridas de depuración, los "alcanzados" que quedaron fueron antes
  de designar al sospechoso (360° de entrada a 2.5 m o verificando): el ladrón corrió hacia el dron sin que la cámara lo
  viera a tiempo. Es el riesgo que queda con lo que el dron no puede saber.
- La rendición es baja en la V16 (7-12 %) comparada con el nivel 4 de la V15 medido igual (44 %). No es un error: en esa
  medición el 30 % de los ladrones del nivel 4 era la "red del ladrón", que aquí se quedaba quieta. Con todos los ladrones
  activos el nivel 4 también baja a 20 %. La V16 usa siempre el ladrón táctico activo: es más difícil a propósito, y por
  eso la custodia es el número principal.

**Pruebas**: 6 nuevas en `tests/test_v16.py` (escenario, civiles, alturas con gente cerca, rampa, persona a 5 m durante el
360° de entrada). Total: 94 pruebas, todas pasan.

**Qué sigue**: fase A2 (posturas humanas en la física, salto con el brazo, civiles con reacciones).
