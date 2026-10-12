"""Versión limpia: acepta todo. Quita lo rojo y los [REVISAR], quita el resaltado amarillo y verde y deja los [FALTA]."""
import sys

import docx
from docx.oxml.ns import qn

d = docx.Document(sys.argv[1])
body = d.element.body
W = qn('w:t')


def hl(r):
    rpr = r.find(qn('w:rPr'))
    h = rpr.find(qn('w:highlight')) if rpr is not None else None
    return h.get(qn('w:val')) if h is not None else None


def texto(el):
    return ''.join(t.text or '' for t in el.iter(W))


def con_texto(el):
    return [r for r in el.iter(qn('w:r')) if ''.join(t.text or '' for t in r.iter(W)).strip()
            or r.find(qn('w:drawing')) is not None]


# 1. leyenda inicial
for p in list(body.findall(qn('w:p')))[:5]:
    body.remove(p)
# 2. tablas y filas completamente rojas
for tbl in list(body.iter(qn('w:tbl'))):
    rs = con_texto(tbl)
    if rs and all(hl(r) == 'red' for r in rs):
        tbl.getparent().remove(tbl)
        continue
    for tr in list(tbl.iter(qn('w:tr'))):
        rs = con_texto(tr)
        if rs and all(hl(r) in ('red', 'cyan') for r in rs):
            tr.getparent().remove(tr)
# 3. párrafos
for p in list(body.iter(qn('w:p'))):
    rs = list(p.iter(qn('w:r')))
    tenia = any(hl(r) in ('red', 'cyan') for r in rs)
    for r in rs:
        if hl(r) in ('red', 'cyan'):
            r.getparent().remove(r)
    if tenia:
        quedan = con_texto(p)
        if not quedan and p.getparent() is not None and p.getparent().tag != qn('w:tc'):
            p.getparent().remove(p)
    for r in p.iter(qn('w:r')):
        if hl(r) in ('yellow', 'green'):
            rpr = r.find(qn('w:rPr'))
            rpr.remove(rpr.find(qn('w:highlight')))
# 4. limpiar espacios dobles que dejan los reemplazos
for t in body.iter(W):
    if t.text and '  ' in t.text:
        t.text = t.text.replace('  ', ' ')
from pulir import pulir
pulir(d, quitar_vacios=True)
d.save(sys.argv[2])
print('Listo:', sys.argv[2])
