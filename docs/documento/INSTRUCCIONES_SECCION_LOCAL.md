# Instrucciones para la sesión local: desarrollo del documento del proyecto de grado

Texto para pegar al inicio de la sesión de Claude Code que corre en el computador de Brahian. Está escrito como
contexto y criterios, no como reglas cerradas: la sesión local decide cómo organizar el trabajo. Solo hay **una
regla rígida: el uso de la skill `humanizer`** (sección 3).

---

## 1. Qué se está haciendo

Proyecto de grado de Ingeniería Aeronáutica (Universidad de San Buenaventura): «Implementación experimental de un
sistema de detección y evasión mediante un modelo de inteligencia artificial para un cuadricóptero». Autores:
Brahian Orrego y Tania Sierra. Brahian no es programador: explicar en español y en lenguaje sencillo. Se escribe
«proyecto de grado», nunca «tesis», en los textos nuevos.

El trabajo ahora es **redactar y completar el documento Word** con la información real del proyecto: sistema a
bordo (Jetson Orin Nano + Pixhawk con ArduPilot 4.7), política PPO entrenada en simulación, reglas deterministas y
operador humano. El repositorio es público: no subir IPs, usuarios, contraseñas, claves ni rutas internas, y **no
subir los archivos Word**.

## 2. Qué leer primero

En el repositorio (`docs/` y `docs/documento/`):

- `CLAUDE.md`, `docs/ESTADO.md`, `docs/DECISIONES.md`, `docs/hardware.md`, `docs/pixhawk.md`, `docs/jetson.md`.
- `docs/documento/FICHA_HECHOS.md`: datos verificados con su fuente. **Un número que no esté ahí no va al
  documento**; si falta, se marca como pendiente.
- `docs/documento/GUIA_PROYECTO_DE_GRADO.md` y `DIAGNOSTICO_DOCUMENTO.md`: qué se corrigió y por qué.
- `docs/documento/diagramas/` (Mermaid `.mmd` editables y `.png`) y `docs/documento/herramientas/v2/` (los scripts
  de python-docx con los que se construyó la versión 5; sirven de punto de partida, no son obligatorios).

Fuera del repositorio, en el computador local:

- La **versión limpia v5** del Word (la última entregada) y el Word propio del equipo, por si tiene cambios nuevos.
- La **plantilla de la USB para proyectos de grado** (APA 7) con todos sus comentarios.
- La **guía del ingeniero Harold** (tareas solicitadas por el tutor).
- **Las dos carpetas de fotos**: juntarlas en una sola, quitar duplicados y revisar cada imagen una por una.

## 3. Regla rígida: skill humanizer

- Toda redacción nueva, y también **todo el documento existente de principio a fin**, pasa por la skill
  `humanizer` (`.claude/skills/humanizer/`) para que el tono suene humano y no lo detecte ningún detector de IA.
- Aplicarla párrafo por párrafo, sin saltarse portada, resumen, anexos, pies de figura ni tablas. Después de
  humanizar, releer: el sentido y los datos no cambian.
- Vigilar los vicios típicos: contrastes «no es X sino Y», cierres de una línea, tríadas forzadas, guiones por
  todas partes, adjetivos inflados, palabras de relleno, negritas como etiquetas, frases del mismo largo. Variar
  el ritmo, usar frases concretas con datos y dejar las dudas como dudas.
- Repetir la pasada al final de cada sesión sobre lo que se haya tocado.

## 4. Entrega: un solo Word

- Entregar **un único Word: la versión limpia**, con el texto ya aceptado. Nada de versión «intervenida» con
  cambios en rojo.
- Lo que falte se resalta, para que el equipo lo vea de un vistazo. Propuesta (ajustable si hay algo mejor):
  `[FALTA: qué dato o imagen]` en resaltado rosa para datos o fotos que faltan, y `[REVISAR: motivo]` en
  turquesa para lo que necesite una decisión humana. Poner en la primera página de la sesión una lista corta de
  qué significa cada color.
- Al abrir el Word, que los campos se actualicen (índices, referencias cruzadas).

## 5. Normas del documento (plantilla USB y guía del tutor)

Leer la plantilla con sus comentarios completos y seguirla. Lo esencial, para no olvidarlo:

- APA 7, Times New Roman 12, interlineado 1.5, texto justificado, citas y referencias completas.
- Tablas y figuras: rótulo («Tabla N» / «Figura N» en negrita, título en cursiva debajo), nota de fuente debajo
  (el equipo quiere «Elaboración propia» también en lo propio), tamaño de letra legible, mismo estilo y colores en
  todos. **La explicación va antes**, con referencia cruzada real de Word (Referencias > Referencia cruzada), y
  la imagen o tabla aparece después de esa cita.
- Anexos: nombrados Anexo 1, 2, 3…, citados en el texto con hipervínculo. En el índice solo entra «Anexos».
- Los marcos teórico, conceptual y normativo se reducen lo máximo posible y remiten a un anexo; los
  antecedentes **conservan los 10 originales** en el cuerpo (se pueden organizar en tabla o con imágenes y no
  llevan nota de «consulte el anexo»).
- Extensión: el documento principal, con análisis, resultados y conclusiones, debe quedar entre **100 y 120
  páginas**, sin contar anexos (interpretación por confirmar con el equipo).
- Revisar cada comentario y sugerencia de la plantilla y de la guía de Harold, y **adaptar lo que se pueda** a
  este proyecto. Lo que no aplique, dejarlo anotado con el motivo, no ignorarlo en silencio.

## 6. Las fotos

- Revisar las dos carpetas juntas y decidir qué sirve y dónde va: **cuerpo** (si aclara una explicación, p. ej.
  ensamble, instrumentos, pruebas de campo), **anexo** (inventario, ensamble por piezas, cableado, instrumentos)
  o **descartar** (borrosas, repetidas, con rostros, placas o datos personales).
- Cada foto lleva rótulo, nota de fuente y cita previa en el texto. Si una foto muestra personas, vehículos con
  placa o un lugar identificable, difuminar o pedir autorización antes de incluirla.
- Datos pendientes ya detectados: qué incluye la lectura de 2371 g de masa, modelo del GPS, y fecha y lugar de
  las fotos de campo.

## 7. Cómo trabajar (con libertad)

- Se puede reorganizar secciones, mover contenido entre cuerpo y anexos, rehacer o crear diagramas (mismo
  formato, letra y paleta) y proponer tablas nuevas, siempre que los datos salgan de la ficha de hechos o de las
  mediciones reales del equipo.
- No inventar resultados de pruebas de campo, números ni referencias. Verificar cada fuente citada y su DOI.
  Donde no haya dato, dejar `[FALTA: …]`.
- Pruebas físicas del dron: un paso a la vez, con instrucciones exactas, esperando confirmación de Brahian.
- Reglas duras del sistema (en `CLAUDE.md`) no se tocan en el texto: gimbal, geocerca, humano en el lazo,
  árbitro de seguridad. Donde el código aún no las cumple, el documento lo dice con honestidad.
- Se puede partir de los scripts de `herramientas/v2/` o editar el Word directamente; lo importante es que el
  resultado valide (abre bien en Word) y que ninguna cita de tabla, figura o anexo quede rota.
- Confirmar con Brahian antes de subir o borrar nada en Git. Commits en español, con coautoría de Claude.

## 8. Cierre de cada sesión

Resumir lo hecho y lo que falta, actualizar `docs/ESTADO.md` y `docs/BITACORA.md` (skill `/cierre-sesion`) y
entregar el Word limpio actualizado con una lista corta de pendientes que dependen del equipo (datos, fotos,
decisiones).
