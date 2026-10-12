"""Ajustes finales de formato según la plantilla USB (APA 7), comunes a las dos versiones."""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

W = qn('w:t')


def _texto(el):
    return ''.join(t.text or '' for t in el.iter(W))


def _estilo(p):
    ppr = p.find(qn('w:pPr'))
    s = ppr.find(qn('w:pStyle')) if ppr is not None else None
    return s.get(qn('w:val')) if s is not None else ''


def _keep_next(p):
    ppr = p.find(qn('w:pPr'))
    if ppr is None:
        ppr = OxmlElement('w:pPr')
        p.insert(0, ppr)
    if ppr.find(qn('w:keepNext')) is None:
        kn = OxmlElement('w:keepNext')
        # keepNext va justo después de pStyle
        s = ppr.find(qn('w:pStyle'))
        (s.addnext(kn) if s is not None else ppr.insert(0, kn))


def _vacio(p):
    return (p.tag == qn('w:p') and not _texto(p).strip() and p.find('.//' + qn('w:drawing')) is None
            and p.find('.//' + qn('w:sectPr')) is None and p.find('.//' + qn('w:br')) is None)


def bordes_apa(tbl):
    """Solo líneas horizontales: arriba, entre filas y abajo (plantilla USB)."""
    tblpr = tbl.find(qn('w:tblPr'))
    viejo = tblpr.find(qn('w:tblBorders'))
    if viejo is not None:
        tblpr.remove(viejo)
    b = OxmlElement('w:tblBorders')
    for lado, val, sz in (('top', 'single', '8'), ('left', 'nil', '0'), ('bottom', 'single', '8'),
                          ('right', 'nil', '0'), ('insideH', 'single', '4'), ('insideV', 'nil', '0')):
        e = OxmlElement(f'w:{lado}')
        e.set(qn('w:val'), val)
        e.set(qn('w:sz'), sz)
        e.set(qn('w:space'), '0')
        e.set(qn('w:color'), 'auto')
        b.append(e)
    sig = None
    for nombre in ('w:shd', 'w:tblLayout', 'w:tblCellMar', 'w:tblLook', 'w:tblCaption', 'w:tblDescription'):
        sig = tblpr.find(qn(nombre))
        if sig is not None:
            break
    (sig.addprevious(b) if sig is not None else tblpr.append(b))
    for tcpr in tbl.iter(qn('w:tcPr')):
        for e in tcpr.findall(qn('w:tcBorders')):
            tcpr.remove(e)


def pulir(d, quitar_vacios):
    body = d.element.body
    hijos = list(body)
    # 1. desde la Introducción: tablas con bordes APA
    inicio = next((k for k, e in enumerate(hijos) if e.tag == qn('w:p') and _texto(e).strip() == 'Introducción'
                   and _estilo(e).startswith('Ttulo')), 0)
    for e in hijos[inicio:]:
        for tbl in ([e] if e.tag == qn('w:tbl') else []):
            bordes_apa(tbl)
    # 2. rótulos de figura: sin párrafos vacíos entre el rótulo y la imagen, y todo pegado
    for k, e in enumerate(list(body)):
        if e.tag != qn('w:p') or e.getparent() is None:
            continue
        t = _texto(e).strip()
        if not (t.startswith('Figura ') or t.startswith('Tabla ')) or len(t) > 250:
            continue
        if not (_estilo(e).startswith('Descripci') or e.find('.//' + qn('w:fldSimple')) is not None
                or 'SEQ' in ''.join(x.text or '' for x in e.iter(qn('w:instrText')))):
            continue
        _keep_next(e)
        sig = e.getnext()
        while sig is not None and _vacio(sig):
            nxt = sig.getnext()
            if quitar_vacios:
                body.remove(sig)
            else:
                _keep_next(sig)
            sig = nxt
        if sig is not None and sig.tag == qn('w:p') and sig.find('.//' + qn('w:drawing')) is not None:
            _keep_next(sig)
