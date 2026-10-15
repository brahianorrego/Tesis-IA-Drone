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


AZUL_BORDE = '44546A'
AZUL_ENCABEZADO = 'DCE6F1'


def bordes_apa(tbl):
    """Estilo único de tablas: cuadrícula completa, encabezado con el mismo color de los diagramas, tabla centrada."""
    tblpr = tbl.find(qn('w:tblPr'))
    viejo = tblpr.find(qn('w:tblBorders'))
    if viejo is not None:
        tblpr.remove(viejo)
    b = OxmlElement('w:tblBorders')
    for lado in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{lado}')
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), '4')
        e.set(qn('w:space'), '0')
        e.set(qn('w:color'), AZUL_BORDE)
        b.append(e)
    sig = None
    for nombre in ('w:shd', 'w:tblLayout', 'w:tblCellMar', 'w:tblLook', 'w:tblCaption', 'w:tblDescription'):
        sig = tblpr.find(qn(nombre))
        if sig is not None:
            break
    (sig.addprevious(b) if sig is not None else tblpr.append(b))
    # centrada
    jc = tblpr.find(qn('w:jc'))
    if jc is None:
        jc = OxmlElement('w:jc')
        # jc va después de tblW/tblLayout? el esquema la acepta antes de tblBorders
        b.addprevious(jc)
    jc.set(qn('w:val'), 'center')
    for tcpr in tbl.iter(qn('w:tcPr')):
        for e in tcpr.findall(qn('w:tcBorders')):
            tcpr.remove(e)
    filas = tbl.findall(qn('w:tr'))
    if not filas:
        return
    ncol = len(filas[0].findall(qn('w:tc')))
    tam = '20' if ncol <= 4 else '18'          # 10 pt o 9 pt (la plantilla pide 9 a 12)
    for r in tbl.iter(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        if rpr is None:
            rpr = OxmlElement('w:rPr')
            r.insert(0, rpr)
        for nombre in ('w:sz', 'w:szCs'):
            e = rpr.find(qn(nombre))
            if e is None:
                e = OxmlElement(nombre)
                rpr.append(e)
            e.set(qn('w:val'), tam)
    # encabezado: negrita y color; se repite en cada página
    for tc in filas[0].findall(qn('w:tc')):
        tcpr = tc.find(qn('w:tcPr'))
        if tcpr is None:
            tcpr = OxmlElement('w:tcPr')
            tc.insert(0, tcpr)
        for e in tcpr.findall(qn('w:shd')):
            tcpr.remove(e)
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), AZUL_ENCABEZADO)
        # shd va después de tcW / gridSpan / vMerge / tcBorders y antes de noWrap / tcMar / vAlign
        pos = None
        for nombre in ('w:noWrap', 'w:tcMar', 'w:textDirection', 'w:tcFitText', 'w:vAlign', 'w:hideMark'):
            pos = tcpr.find(qn(nombre))
            if pos is not None:
                break
        (pos.addprevious(shd) if pos is not None else tcpr.append(shd))
        for r in tc.iter(qn('w:r')):
            rpr = r.find(qn('w:rPr'))
            if rpr.find(qn('w:b')) is None:
                rpr.insert(0, OxmlElement('w:b'))
    trpr = filas[0].find(qn('w:trPr'))
    if trpr is None:
        trpr = OxmlElement('w:trPr')
        filas[0].insert(0, trpr)
    if trpr.find(qn('w:tblHeader')) is None:
        trpr.append(OxmlElement('w:tblHeader'))


def _roja(p):
    """Párrafo cuyo contenido (texto o dibujos) está todo marcado en rojo (se va en la versión limpia)."""
    runs = [r for r in p.iter(qn('w:r')) if _texto(r).strip() or r.find('.//' + qn('w:drawing')) is not None]
    if not runs:
        return False
    for r in runs:
        rpr = r.find(qn('w:rPr'))
        h = rpr.find(qn('w:highlight')) if rpr is not None else None
        if h is None or h.get(qn('w:val')) != 'red':
            return False
    return True


def _siguiente_no_vacio(e):
    s = e.getnext()
    while s is not None and s.tag == qn('w:p') and (_vacio(s) or _roja(s)):
        s = s.getnext()
    return s


def notas_elaboracion_propia(d):
    """Toda figura y tabla lleva una nota de fuente: si no la tiene, se agrega 'Nota. Elaboración propia.'"""
    import copy
    body = d.element.body
    modelo = next((p for p in body.iter(qn('w:p')) if _texto(p).startswith('Nota.') and p.find(qn('w:pPr')) is not None), None)
    n = 0
    for p in list(body.iter(qn('w:p'))):
        t = _texto(p).strip()
        if not (t.startswith('Figura ') or t.startswith('Tabla ')) or len(t) > 250:
            continue
        instr = ''.join(x.text or '' for x in p.iter(qn('w:instrText'))) + ''.join(
            (f.get(qn('w:instr')) or '') for f in p.iter(qn('w:fldSimple')))
        if 'SEQ' not in instr:
            continue
        runs = [r for r in p.iter(qn('w:r')) if _texto(r).strip()]
        if runs and all((r.find(qn('w:rPr')) is not None and r.find(qn('w:rPr')).find(qn('w:highlight')) is not None
                         and r.find(qn('w:rPr')).find(qn('w:highlight')).get(qn('w:val')) == 'red') for r in runs):
            continue
        es_fig = t.startswith('Figura ')
        s = _siguiente_no_vacio(p)
        if s is None:
            continue
        if es_fig:
            if s.tag != qn('w:p') or s.find('.//' + qn('w:drawing')) is None:
                continue
            ancla = s
        else:
            if s.tag != qn('w:tbl'):
                continue
            ancla = s
        despues = _siguiente_no_vacio(ancla)
        if despues is not None and despues.tag == qn('w:p') and _texto(despues).strip().startswith('Nota'):
            continue
        q = OxmlElement('w:p')
        if modelo is not None:
            q.append(copy.deepcopy(modelo.find(qn('w:pPr'))))
        for texto, cursiva in (('Nota.', True), (' Elaboración propia.', False)):
            r = OxmlElement('w:r')
            rpr = OxmlElement('w:rPr')
            if cursiva:
                rpr.append(OxmlElement('w:i'))
            h = OxmlElement('w:highlight')
            h.set(qn('w:val'), 'yellow')
            sz = OxmlElement('w:sz')
            sz.set(qn('w:val'), '20')
            rpr.append(sz)
            rpr.append(h)
            r.append(rpr)
            tt = OxmlElement('w:t')
            tt.text = texto
            tt.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            r.append(tt)
            q.append(r)
        ancla.addnext(q)
        n += 1
    return n


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
