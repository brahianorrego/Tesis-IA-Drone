# Herramientas de la intervención del Word

Scripts que generaron la copia intervenida del documento (2026-10-12). Solo sirven sobre la versión del Word revisada ese
día, porque ubican párrafos por su posición y por su texto; sobre otra versión hay que ajustar los índices.

| Script | Qué hace |
|---|---|
| `intervenir.py` | Marca en rojo, agrega en verde y amarillo, inserta los `[REVISAR]`, las tablas y las figuras nuevas |
| `helpers.py` | Funciones para resaltar, partir textos, insertar párrafos, tablas (bordes APA) y notas (formato de la plantilla USB) |
| `aceptar.py` | Genera una vista previa "limpia": quita lo rojo y el resaltado amarillo y verde, conserva los `[REVISAR]` |

```
python intervenir.py original.docx intervenido.docx ../diagramas
python aceptar.py intervenido.docx limpia.docx
```

Requiere `python-docx` y `Pillow`. No usar el paso de "unir runs" del editor de Word de Claude antes de `intervenir.py`:
cambia la numeración automática de los párrafos.

## Versión 2 (carpeta `v2/`)

Segunda ronda (2026-10-12): texto reescrito en lenguaje más natural, anexos A a G con hipervínculos, diagramas nuevos
y formato de la plantilla USB (rótulos, notas, tablas con solo líneas horizontales, figuras pegadas a su rótulo).

| Script | Qué hace |
|---|---|
| `motor.py` | Funciones base: resaltar, insertar párrafos, rótulos con numeración automática, tablas, figuras, hipervínculos a anexos |
| `c1_inicio.py` … `c5_anexos.py` | Los cambios de cada parte: portada a justificación, marcos, arquitectura, integración y resultados, referencias y anexos |
| `construir.py` | Aplica todo y numera tablas y figuras |
| `c6_humanizar.py`, `h_ediciones.py` | Pasada de redacción con la skill humanizer: aplica cada edición en el documento (en rojo y verde en la intervenida) |
| `pulir.py` | Ajustes finales de formato comunes a las dos versiones |
| `aceptar2.py` | Vista previa limpia: quita lo rojo y los `[REVISAR]`, deja solo los `[FALTA]` |
| `pdf_uno.py` | Convierte a PDF con LibreOffice para revisar (LibreOffice no dibuja las ecuaciones; Word sí) |

```
python construir.py original.docx intervenido.docx ../diagramas <copia del repositorio en la rama v16-simulacion>
python aceptar2.py intervenido.docx limpia.docx
```
