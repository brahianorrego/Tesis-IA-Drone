"""Versión limpia: quita lo rojo, quita el resaltado amarillo y verde, conserva los [REVISAR] en turquesa."""
import sys
import docx
from docx.oxml.ns import qn

d = docx.Document(sys.argv[1])
body = d.element.body


def hl(r):
    rpr = r.find(qn('w:rPr'))
    h = rpr.find(qn('w:highlight')) if rpr is not None else None
    return h.get(qn('w:val')) if h is not None else None


for p in list(body.iter(qn('w:p'))):
    runs = list(p.iter(qn('w:r')))
    if not runs:
        continue
    rojos = [r for r in runs if hl(r) == 'red']
    if rojos and len(rojos) == len(runs):
        p.getparent().remove(p)
        continue
    for r in rojos:
        r.getparent().remove(r)
    for r in p.iter(qn('w:r')):
        if hl(r) in ('yellow', 'green'):
            rpr = r.find(qn('w:rPr'))
            rpr.remove(rpr.find(qn('w:highlight')))
# leyenda inicial (5 primeros párrafos amarillos) ya sin resaltado: quitar
for p in list(body.findall(qn('w:p')))[:5]:
    body.remove(p)
d.save(sys.argv[2])
