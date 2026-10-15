"""Pasada de redacción con la skill humanizer (blader/humanizer, 26 patrones de 'Signs of AI writing').

Cada edición es (fragmento_viejo, fragmento_nuevo). Se busca en el texto vigente del párrafo (sin lo marcado en rojo):
- si el fragmento está en texto nuevo (verde o amarillo), se cambia en su sitio;
- si está en texto original, el viejo queda en rojo y el nuevo en verde (se ve en la copia intervenida).
Una edición con nuevo = '' borra el fragmento. Si un párrafo queda vacío, se quita.
"""
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

import copy

from docx.text.run import Run

from motor import ROJO, VERDE

W_T = qn('w:t')
EDICIONES = []


def _hl(r):
    rpr = r.find(qn('w:rPr'))
    h = rpr.find(qn('w:highlight')) if rpr is not None else None
    return h.get(qn('w:val')) if h is not None else None


def _vigente(M, p):
    """[(run, inicio, fin, color)] de los runs directos del párrafo, en coordenadas del texto completo."""
    segs, pos = [], 0
    for r in p.findall(qn('w:r')):
        t = M._rt(r)
        segs.append((r, pos, pos + len(t), _hl(r)))
        pos += len(t)
    return segs


def aplicar(M, ediciones=None):
    ediciones = EDICIONES if ediciones is None else ediciones
    body = M.d.element.body
    fallos = []
    for viejo, nuevo in ediciones:
        hallados = []
        for p in body.iter(qn('w:p')):
            segs = _vigente(M, p)
            idx = []
            vig = []
            for r, a, b, c in segs:
                if c in ('red', 'cyan'):
                    continue
                t = M._rt(r)
                for k, ch in enumerate(t):
                    vig.append(ch)
                    idx.append(a + k)
            texto = ''.join(vig)
            i = texto.find(viejo)
            if i >= 0:
                a, b = idx[i], idx[i + len(viejo) - 1] + 1
                if b - a == len(viejo):
                    hallados.append((p, a, b))
        if len(hallados) != 1:
            fallos.append((len(hallados), viejo[:80]))
            continue
        p, a, b = hallados[0]
        M._split(p, b)
        M._split(p, a)
        tocados = [(r, c) for r, x, y, c in _vigente(M, p) if x >= a and y <= b and y > x]
        colores = {c for _, c in tocados}
        if colores <= {'yellow', 'green'} and colores:
            primero = tocados[0][0]
            for r, _ in tocados[1:]:
                p.remove(r)
            ts = primero.findall(W_T)
            if nuevo:
                ts[0].text = nuevo
                ts[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                for t in ts[1:]:
                    primero.remove(t)
            else:
                p.remove(primero)
            if not ''.join(t.text or '' for t in p.iter(W_T)).strip() and p.find('.//' + qn('w:drawing')) is None and p.getparent().tag != qn('w:tc'):
                p.getparent().remove(p)
        elif colores == {None}:
            _marcar_y_agregar(M, p, a, b, nuevo, tocados)
        else:
            fallos.append(('mezcla', viejo[:80]))
    return fallos


def _marcar_y_agregar(M, p, a, b, nuevo, tocados):
    ult = None
    for r, _ in tocados:
        Run(r, None).font.highlight_color = ROJO
        ult = r
    if nuevo:
        rpr = copy.deepcopy(ult.find(qn('w:rPr'))) if ult.find(qn('w:rPr')) is not None else None
        if rpr is not None:
            for e in rpr.findall(qn('w:highlight')):
                rpr.remove(e)
        M.texto(Paragraph(p, M.d._body), nuevo, VERDE, after=ult, rpr=rpr)
