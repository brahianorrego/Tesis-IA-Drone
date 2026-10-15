# Diagnóstico del Word del proyecto de grado

Revisión del archivo `Proyecto de grado Dron IA.docx` (89 páginas, 2026-10-12) contra la carta al comité, el repositorio y
la plantilla APA de la USB (`Plantilla_APA_TesisUSBCo_2022_v.6.docx`). Todo lo de esta tabla ya está marcado en la copia
intervenida con rojo, verde, amarillo o turquesa.

## 1. Inconsistencias encontradas

| # | Dónde | Problema | Qué se hizo en la copia |
|---|---|---|---|
| 1 | Introducción, planteamiento, justificación, alcances, 1.7.3, 1.9.3, 2.1.2, 2.1.10 | Dice Raspberry Pi (33 menciones) | Cambiado a Jetson Orin Nano donde describe el sistema; se dejó como historia en 2.1.3–2.1.8 con una aclaración |
| 2 | Limitaciones | "Dron fijo, sin evasión" contradice "detención y ascenso" | Reescrita: el modo estático es un escenario más |
| 3 | Limitaciones | "No es validación por repeticiones" contradice el objetivo 3 | Reemplazada por la de 10 repeticiones con intervalo de confianza |
| 4 | Limitaciones | "Sin sensores adicionales" frente a cámara, estabilizador y GPS | Reescrita: sin sensores **de percepción** adicionales |
| 5 | Limitaciones | "Sin entrenamiento desde cero" frente al MLP entrenado | Reescrita: se refiere al detector |
| 6 | 2.2.6 | El MLP tenía 3 entradas y 4 salidas con evasión izquierda/derecha | Reemplazado por el decisor real: 15 entradas, una salida (CONTINUAR / DETENER_Y_ASCENDER) |
| 7 | 2.2.6, Figura 28 | El diagrama de evasión muestra izquierda/derecha y umbral 60 % | Marcado para eliminar; nuevas Figuras N2 (arquitectura) y N3 (estados) |
| 8 | 2.1.10 | TF-Luna; el sistema usa TF03. Lógica "YOLO + LiDAR deben coincidir" no es la implementada | Corregido; agregada Tabla N3 con d_safe por velocidad |
| 9 | 2.2.2, 2.2.5 | 921600 baudios, Ubuntu 20.04, cámara CSI | 115200, Ubuntu 24.04, cámara USB |
| 10 | Tabla 14 | LiDAR y MAVLink "pendientes" | Actualizados a verificados con fecha |
| 11 | Tablas 8 y 9 | Los totales no salen de los pesos de la Tabla 7 (se probaron todas las combinaciones de pesos enteros de 1 a 10) | REVISAR + Tabla N2 recalculada con pesos explícitos |
| 12 | Tabla 10 | Es una copia de la Tabla 9 (mismas filas y números) | REVISAR: rehacerla con criterios de control de vuelo |
| 13 | Tabla 9 | La matriz eligió la Raspberry Pi, que falló | Párrafo de reevaluación con datos medidos (propuesta) |
| 14 | 1.9.3, Figura 16 | La imagen dice "Raspberry Pi" y "entorno indoor" | Figura corregida (mismo dibujo, dos textos cambiados) |
| 15 | 2.1.2, Figura 18 | Dice Raspberry Pi, cámara CSI, UBEC 5 V y repite un bloque | REVISAR: rehacer |
| 16 | Figuras 21, 22, 24 | "Elaboración por Gemini" | Nota corregida + REVISAR (declarar IA o usar foto real) |
| 17 | Numeración | Dos "Figura 28"; la lista salta de 11 a 15; "Tabla 16/17" citadas con títulos 13/14; "Tabla 9/10" en vez de 8/9 | Referencias corregidas; REVISAR para actualizar índices |
| 18 | Figura 29 | Vacía | REVISAR |
| 19 | Anexos | Se citan Anexo B, Anexo C, Tablas 20–22, que no existen | Propuesta de anexos A–F |
| 20 | Referencias | Ahmed et al. (2022) y Kurunathan et al. (2022) son el mismo artículo; el DOI no resuelve; la versión de revista es de 2024 | Ahmed en rojo; Kurunathan corregido a 2024 |
| 21 | Referencias | Faltan 13 fuentes citadas; 4 referencias no se citan (Jiang, Lahmeri, Palossi, ArduPilot s. f.-b) | Agregadas las verificadas; las no citadas en rojo |
| 22 | Referencias | URL de PX4 con `?utm_source=chatgpt.com`; "PX4, 2025" frente a "(s. f.)" | Enlace limpiado; REVISAR para el año |
| 23 | 1.6.3 | "(Analog Devices, 2021)": el artículo tiene autor | Cambiado a (Brand, 2021) |
| 24 | Portada | Asesor "Magíster (MSc) en" cortado; grupo y línea sin elegir; dedicatoria de plantilla | REVISAR |
| 25 | Resumen | Iba a pasar de 250 palabras con lo nuevo | Recortado a 241 palabras |
| 26 | Conclusiones | Un párrafo que cuenta un hecho del desarrollo | Marcado; esqueleto por objetivo |
| 27 | Capítulo 3 | Vacío | Esqueleto con los resultados verificados de simulación y tablas listas para campo |
| 28 | Capítulo 2 | Anuncia un tercer bloque (validación) que no existe | Nuevo 2.3 con escenarios, el porqué de cada número y la estadística |

## 2. Presupuesto de páginas (límite de 100)

Medido con LibreOffice sobre la versión limpia (sin lo rojo). Las páginas reales en Word pueden variar ±3.

| Parte | Original | Copia limpia | Meta |
|---|---:|---:|---:|
| Preliminares (portada a listas) | 9 | 9 | 9 |
| Resumen, abstract, introducción | 4 | 4 | 4 |
| 1.1–1.4 Planteamiento a limitaciones | 7 | 7 | 7 |
| 1.5 Estado del arte | 7 | 5 | 4 |
| 1.6–1.7 Marcos teórico y conceptual | 8 | 6 | 6 |
| 1.8 Marco normativo | 3 | 3 | 3 |
| 1.9 Metodología (no se tocó el texto) | 5 | 7 | 6 |
| 2.1 Arquitectura (Pugh, QFD) | 24 | 28 | **20** (mover Tablas 2–4 a un anexo) |
| 2.2 Integración | 15 | 17 | 15 |
| 2.3 Protocolo y porqué de los números (nuevo) | 0 | 5 | 5 |
| 3 Resultados | 1 | 3 | 10 (con campo) |
| 4–5 Conclusiones y recomendaciones | 2 | 3 | 3 |
| Referencias | 2 | 4 | 4 |
| **Total sin anexos** | **87** | **101** | **96** |

La metodología creció en la copia porque tiene la figura corregida y una nota [REVISAR]; al aceptar los cambios vuelve a
unas 6 páginas.

Para llegar a la meta sin tocar la metodología: (1) mover las Tablas 2, 3 y 4 de 2.1 a un anexo (≈ 7 páginas), (2) dejar
los diagramas en tamaño moderado, y (3) confirmar con la Facultad si los anexos cuentan dentro de las 100 páginas. La
plantilla no lo dice.

## 3. Lo que pide la plantilla de la USB (68 comentarios, resumidos)

**Formato general**
- APA 7, márgenes de 2.5 cm, una sola fuente (Times New Roman 12 en este documento), interlineado 1.5, texto
  justificado, sangría de primera línea de 1.25 cm (estilo "Párr.APA").
- Títulos: nivel 1 centrado y en negrita, siempre en página nueva; nivel 2 a la izquierda en negrita; nivel 3 en
  negrita y cursiva; niveles 4 y 5 con el texto en la misma línea. Usar los botones "Nivel 1 APA"… "Nivel 5 APA".
- Encabezado: primeras palabras del título en mayúsculas sostenidas, 10 puntos, sin que pase a dos líneas (ya cumple).
- Un espacio sencillo entre párrafos; dos entre título y párrafo, párrafo e imagen, tabla y párrafo.
- Pocas cursivas y negritas; nada de subrayado; comillas "inglesas".

**Preliminares**
- Portada: nombres completos con tildes; asesor con su título más alto; el mismo año en portada, cita y referencia.
- Página legal obligatoria en 10 puntos, con la cita y la referencia APA del propio trabajo.
- Las dos imágenes del repositorio solo si autores y asesor aceptan publicar en el repositorio institucional.
- Grupo y línea de investigación de la lista oficial (si no aparecen, preguntar al asesor).
- Dedicatoria y agradecimientos: opcionales, máximo una página entre las dos.
- No borrar el salto de sección antes del resumen (es el que numera las páginas).

**Resumen y abstract**
- Entre 150 y 250 palabras cada uno: objetivo, metodología, resultados y conclusiones.
- 3 a 7 palabras clave, en minúsculas, separadas por coma. Keywords con la terminología de bases de datos.
- No usar traductores automáticos para el abstract.

**Tablas y figuras**
- Rótulo con Referencias > Insertar título: "Tabla N" o "Figura N" en negrita y el título en cursiva en la línea
  siguiente, ambos en 12 puntos y a la izquierda. Así aparecen en las listas.
- La nota va debajo: "Nota." en cursiva, todo en 10 puntos, justificado y con punto final.
- Si la tabla o figura es de autoría propia **no hace falta** escribir "Elaboración propia".
- Tablas editables (nunca una captura de pantalla de una tabla), sin todas las líneas de borde, datos de 9 a 12 puntos,
  sin partirlas entre páginas; si son muy anchas, en página horizontal.
- Toda imagen se llama "Figura" (fotos, diagramas, gráficas).
- Referencias cruzadas con Referencias > Referencia cruzada (para que el número se actualice solo).

**Citas y referencias**
- Toda cita tiene su referencia y toda referencia se cita al menos una vez.
- Recomiendan Mendeley; no mezclar métodos (Mendeley, Word o manual).
- Evitar blogs, Wikipedia y portales que no son fuentes primarias (por eso se marcaron las figuras de Medium, ResearchGate,
  visionplatform, gidahatari y Coptrz).
- Unos 75 % de redacción propia y 25 % de citas; pocas citas textuales.
- Tres o más autores: "et al." desde la primera cita.

**Estructura**
- Indispensables: resumen, abstract, introducción y referencias. Lo demás se adapta al trabajo.
- La plantilla trae "Discusión" como capítulo; en la copia se propone como sección 3.6.
- En la tabla de contenido solo va "Anexos", no "Anexo A", "Anexo B"…
- "Lista de tablas" y "Lista de figuras" no van en la tabla de contenido.
- Al final, borrar todos los comentarios (Revisar > Eliminar > Eliminar todos los comentarios del documento).

## 4. Versión 2 (2026-10-12)

### Páginas

Medido con LibreOffice sobre la vista previa limpia (en Word puede variar ±3 páginas):

| Parte | Páginas |
|---|---:|
| Preliminares a referencias (cuerpo del documento) | 1–73 |
| Contenido hasta el capítulo 5 | 1–69 |
| Anexos A a G (no cuentan en el límite de 100) | 74–110 |

Quedan unas 25 páginas libres para los resultados de banco y de campo.

### Anexos (con hipervínculo desde el texto)

| Anexo | Contenido |
|---|---|
| A | Antecedentes complementarios (León y Castro) |
| B | Diseño conceptual completo: Tablas 2–4 originales, escala de calificación, sensibilidad, reevaluación, concepto global, QFD |
| C | Inventario de componentes |
| D | Parámetros de ArduPilot y del software |
| E | Organización del código, primera versión del detector y listados (LiDAR, intervención en banco, clasificador, envolvente de reglas) |
| F | Simulación del protocolo y del clasificador (datos, matriz de confusión, curvas, mundos, condiciones degradadas, estadística) |
| G | Protocolo de campo: lista de verificación, planilla, disposición, interrupción y consentimiento |

### Figuras revisadas una por una

- Se quitaron las figuras de blogs o sin fuente académica y las que repetían información (antiguas 2, 6–9, 21, 22, 28).
- Se redibujaron con letra Times New Roman y tamaño legible (≈ 9 pt al tamaño de la página): caja negra, caja
  transparente, diagrama funcional, conexiones, arquitectura, estados y secuencia de validación. Las de la versión
  anterior decían Raspberry Pi, tenían textos ilegibles o no coincidían con el montaje real.
- La figura de metodología se dejó igual, solo con dos textos corregidos (Raspberry Pi → computadora de a bordo;
  indoor → exterior).
- La Figura 12 (detector en computador) muestra una persona y la ventana dice "Detección de Rostros": hay que
  reemplazarla por una captura del detector de personas y tener la autorización escrita de quien aparece.

### Redacción

Se instaló la skill `humanizer` (https://github.com/blader/humanizer, licencia MIT) en `.claude/skills/humanizer/` y se
aplicó a todo el documento, de la portada a los anexos. Sigue los 26 patrones de "Signs of AI writing" de Wikipedia:
contrastes "no X sino Y", cierres que repiten lo dicho, frases sentenciosas, tríadas de relleno, rayas, palabras de
moda, adornos de importancia y listados con negrita. Las 25 correcciones de esta pasada están en
`herramientas/v2/h_ediciones.py` (se ven en rojo y verde en la copia intervenida). Además:

- Se quitaron de los listados de código del Anexo E las referencias internas (CLAUDE.md, rutas de docs, "decisiones
  del arquitecto"); es solo texto de comentarios, no código.
- Se corrigió una inexactitud: las entradas del clasificador son 15 e incluyen "si hay detección".
- Un detector de IA nunca da certeza. Lo que protege es que cada frase la puedan explicar y defender los autores.

### Lo que falta (marcado `[FALTA]` en rosa en el Word)

- Portada: coautoría de Tania, título del asesor, grupo y línea de investigación, dedicatoria y agradecimientos.
- Referencias: iniciales, año y **enlace del repositorio** de las tesis de la USB (Córdoba y Ruiz; Castro y Ortega) y
  de los trabajos de Bohórquez, León y Avilés; año de la edición de OACI; datos de Meisel; fecha de la Resolución RAC 100.
- Datos del dron: masa de despegue, modos finales del interruptor, LOIT_BRK_ACCEL y GUID_TIMEOUT leídos en la
  Pixhawk, fuente del margen de 1.5 m, número de registro y certificado del piloto.
- Pruebas: resultados de banco (pasos 1 a 5), validación del clasificador con datos reales, ensayos de campo
  (Tabla 17), observaciones cualitativas, comparación campo–simulación, capturas de la Figura 16.
- Conclusiones de cada objetivo con los datos de campo, y cerrar resumen y abstract (máximo 250 palabras).

## 5. Versión 4 (2026-10-15): cambios pedidos por el tutor

| Pedido del tutor | Qué se hizo |
|---|---|
| Marcos y antecedentes en máximo 10 páginas | 1.5 a 1.8 ocupan unas 6 páginas (medido con LibreOffice, sin ecuaciones; en Word serán algo más) |
| Detalle a anexos, con nota al final de cada marco | Anexo 1 (antecedentes), Anexo 2 (marcos teórico y conceptual) y Anexo 3 (marco normativo); cada marco termina con "Para mayor información, consulte el Anexo N" |
| Antecedentes en un párrafo | Un párrafo por nivel: internacionales, nacionales y locales |
| Justificar que el tema está poco estudiado | Apartado 1.5.4, apoyado en la Tabla 18 del Anexo 1; falta documentar la búsqueda (bases, palabras clave, años) |
| Terminar los objetivos 1 y 2 | Fotos de masa (2371 g), GPS y montaje en exteriores en los anexos 4 y 6; resultados de banco y campo siguen como [FALTA] |

Además: anexos numerados por orden de mención (Anexo 1 a 9, como pide la plantilla), tablas y figuras de los anexos con numeración consecutiva, todas citadas antes de aparecer y con campo de referencia cruzada (Ctrl + clic), y figura de metodología redibujada con la letra del documento.
`herramientas/v2/verificar_refs.py` comprueba esas citas.

Equivalencia con los anexos que había propuesto el equipo: su Anexo 1 (reensamble) es el Anexo 6; sus anexos 2, 3 y 4 (detector, evasión, arquitectura del software) están en el Anexo 8.
