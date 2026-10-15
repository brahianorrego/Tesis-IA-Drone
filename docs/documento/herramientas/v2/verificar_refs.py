"""Comprueba que cada tabla, figura y anexo se cita en el texto ANTES de aparecer (plantilla USB) y que usa campo REF."""
import re, sys
import docx
from docx.oxml.ns import qn
d = docx.Document(sys.argv[1])
body = d.element.body
filas = []   # (indice, tipo, texto, es_rotulo, tiene_ref)
def txt(el): return ''.join(t.text or '' for t in el.iter(qn('w:t')))
i = 0
for p in body.iter(qn('w:p')):
    t = txt(p)
    instr = ''.join(x.text or '' for x in p.iter(qn('w:instrText')))
    simples = ''.join((f.get(qn('w:instr')) or '') for f in p.iter(qn('w:fldSimple')))
    m = re.match(r'^(Tabla|Figura) (\d+)', t)
    rot = m if (m and ('SEQ' in instr or 'SEQ' in simples)) else None
    filas.append((i, t, rot.group(0) if rot else None, ' REF ' in instr))
    i += 1
ini = next(i for i, t, r, f in filas if t.strip() == 'Introducción' and i > 100)
filas = [x for x in filas if x[0] >= ini]
primera = {}
rot_pos = {}
for i, t, rot, ref in filas:
    if rot:
        rot_pos[rot] = i
for i, t, rot, ref in filas:
    if rot: continue
    for m in re.finditer(r'\b(Tabla|Figura) (\d+)\b', t):
        k = m.group(0)
        primera.setdefault(k, (i, ref))
malos, sin_cita, sin_ref = [], [], []
for k, pos in sorted(rot_pos.items(), key=lambda x: x[1]):
    if k not in primera: sin_cita.append(k)
    elif primera[k][0] > pos: malos.append((k, primera[k][0] - pos))
    elif not primera[k][1]: sin_ref.append(k)
print('rótulos', len(rot_pos))
titulos = {}
for i, t, rot, ref in filas:
    if rot: titulos[rot] = t[:70]
print('sin ninguna cita en el texto:', [(k, titulos[k]) for k in sin_cita])
print('citados DESPUÉS del rótulo:', malos)
print('primera cita sin campo REF:', sin_ref)
# anexos
anex = {}
for i, t, rot, ref in filas:
    m = re.match(r'^Anexo (\d+)\. ', t)
    if m: anex[int(m.group(1))] = i
cit = {}
for p in body.iter(qn('w:hyperlink')):
    a = p.get(qn('w:anchor')) or ''
    if a.startswith('Anexo_'): cit.setdefault(a, 0); cit[a] += 1
print('anexos:', sorted(anex), 'enlaces por anexo:', cit)
