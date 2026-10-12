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
