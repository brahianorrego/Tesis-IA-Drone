"""Motor para intervenir el Word del proyecto de grado.

Colores (resaltado):
  rojo      -> sobra o está mal (se borra en la versión limpia)
  verde     -> reemplaza al rojo que tiene justo antes
  amarillo  -> texto nuevo
  turquesa  -> [REVISAR: ...] explicación de una corrección (solo en la versión intervenida)
  rosado    -> [FALTA: ...] algo que hay que agregar (aparece en las dos versiones)
"""
import copy
import re

import docx
from docx.enum.text import WD_COLOR_INDEX as WC
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph
from docx.text.run import Run

ROJO, AMARILLO, VERDE, TURQ, ROSA = WC.RED, WC.YELLOW, WC.BRIGHT_GREEN, WC.TURQUOISE, WC.PINK
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'


class Motor:
    def __init__(self, ruta):
        self.d = docx.Document(ruta)
        self.P = list(self.d.paragraphs)
        self.T = list(self.d.tables)
        self.body = self.d.element.body
        self.claves = {}          # elemento de rótulo -> clave
        self.lista_ppr = self.P[188]._p.pPr
        self.nota_ppr = self.P[213]._p.pPr
        self.cap_tabla = self.P[501]._p
        self.cap_figura = self.P[488]._p
        self.bm_id = 9000

    # ------------------------------------------------------------ runs
    @staticmethod
    def _t(texto):
        t = OxmlElement('w:t')
        t.text = texto
        t.set(XML_SPACE, 'preserve')
        return t

    def run(self, p, texto, color, bold=False, italic=False, size=None, font=None, after=None, rpr=None):
        r = OxmlElement('w:r')
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        r.append(self._t(texto))
        if after is not None:
            after.addnext(r)
        else:
            p._p.append(r)
        ru = Run(r, p)
        if color is not None:
            ru.font.highlight_color = color
        if bold:
            ru.font.bold = True
        if italic:
            ru.font.italic = True
        if size:
            ru.font.size = Pt(size)
        if font:
            ru.font.name = font
            rfonts = r.find(qn('w:rPr')).find(qn('w:rFonts'))
            for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
                rfonts.set(qn(a), font)
        return r

    def hipervinculo(self, p, texto, ancla, color, size=None, after=None):
        h = OxmlElement('w:hyperlink')
        h.set(qn('w:anchor'), ancla)
        h.set(qn('w:history'), '1')
        r = OxmlElement('w:r')
        rpr = OxmlElement('w:rPr')
        rs = OxmlElement('w:rStyle')
        rs.set(qn('w:val'), 'Hipervnculo')
        rpr.append(rs)
        r.append(rpr)
        r.append(self._t(texto))
        h.append(r)
        if after is not None:
            after.addnext(h)
        else:
            p._p.append(h)
        ru = Run(r, p)
        if color is not None:
            ru.font.highlight_color = color
        if size:
            ru.font.size = Pt(size)
        return h

    # Los anexos se numeran por orden de primera mención (plantilla USB: Anexo 1, Anexo 2...). La clave interna es una letra.
    ANEXO_NUM = {'A': 1, 'H': 2, 'I': 3, 'G': 4, 'B': 5, 'C': 6, 'D': 7, 'E': 8, 'F': 9}
    PARTES = re.compile(r'(\[REVISAR:[^\]]*\]|\[FALTA:[^\]]*\]|Anexo [A-I]\b|\*[^*]+\*)')

    def texto(self, p, texto, color, bold=False, italic=False, size=None, font=None, after=None, enlaces=True,
              rpr=None):
        """Agrega texto con marcas: [REVISAR: ..] turquesa, [FALTA: ..] rosado, *cursiva*, Anexo X enlazado."""
        last = after
        for parte in self.PARTES.split(texto):
            if not parte:
                continue
            if parte.startswith('[REVISAR:'):
                last = self.run(p, parte, TURQ, bold=True, size=size, after=last, rpr=rpr)
            elif parte.startswith('[FALTA:'):
                last = self.run(p, parte, ROSA, bold=True, size=size, after=last, rpr=rpr)
            elif enlaces and re.fullmatch(r'Anexo [A-I]', parte):
                last = self.hipervinculo(p, f'Anexo {self.ANEXO_NUM[parte[-1]]}', 'Anexo_' + parte[-1], color,
                                         size=size, after=last)
            elif parte.startswith('*') and parte.endswith('*') and len(parte) > 2:
                last = self.run(p, parte[1:-1], color, bold=bold, italic=True, size=size, font=font, after=last,
                                rpr=rpr)
            else:
                last = self.run(p, parte, color, bold=bold, italic=italic, size=size, font=font, after=last,
                                rpr=rpr)
        return last

    # ------------------------------------------------------------ marcar
    def marcar(self, el, color=ROJO):
        """Resalta todos los runs de un párrafo o tabla."""
        x = el._p if isinstance(el, Paragraph) else (el._tbl if hasattr(el, '_tbl') else el)
        for r in x.iter(qn('w:r')):
            Run(r, None).font.highlight_color = color
        if color == ROJO and x.tag == qn('w:p') and x.xpath('.//w:drawing'):
            r = OxmlElement('w:r')
            r.append(self._t(' [figura eliminada o reemplazada]'))
            x.append(r)
            Run(r, None).font.highlight_color = ROJO

    # ------------------------------------------------------------ párrafos nuevos
    def _nuevo_p(self, ancla_el, ppr=None, antes=False):
        p = OxmlElement('w:p')
        if ppr is not None:
            c = copy.deepcopy(ppr)
            for e in c.findall(qn('w:sectPr')):
                c.remove(e)
            for e in c.findall(qn('w:rPr')):
                c.remove(e)
            p.append(c)
        if antes:
            ancla_el.addprevious(p)
        else:
            ancla_el.addnext(p)
        return p

    def _el(self, a):
        if isinstance(a, Paragraph):
            return a._p
        if hasattr(a, '_tbl'):
            return a._tbl
        return a

    def parrafo(self, ancla, texto='', color=AMARILLO, estilo='Párr.APA', ppr_de=None, bold=False, italic=False,
                size=None, alineacion=None, antes=False, sangria0=False, salto_pagina=False):
        ppr = ppr_de._p.pPr if isinstance(ppr_de, Paragraph) else ppr_de
        p_el = self._nuevo_p(self._el(ancla), ppr, antes=antes)
        p = Paragraph(p_el, self.d._body)
        if ppr is None and estilo:
            p.style = self.d.styles[estilo]
        if alineacion is not None:
            p.alignment = alineacion
        if sangria0:
            p.paragraph_format.first_line_indent = Cm(0)
        if salto_pagina:
            p.paragraph_format.page_break_before = True
        if texto:
            self.texto(p, texto, color, bold=bold, italic=italic, size=size)
        return p

    def vineta(self, ancla, texto, color=AMARILLO):
        return self.parrafo(ancla, texto, color, ppr_de=self.lista_ppr)

    def reemplazar_parrafo(self, p, nuevo, color=VERDE):
        """Párrafo completo: el viejo en rojo y el nuevo (mismo formato) en verde justo después."""
        self.marcar(p)
        q = self.parrafo(p, '', color, ppr_de=p)
        self.texto(q, nuevo, color)
        return q

    # ------------------------------------------------------------ reemplazo dentro de un párrafo
    @staticmethod
    def _rt(r):
        out = []
        for c in r:
            if c.tag == qn('w:t'):
                out.append(c.text or '')
            elif c.tag == qn('w:tab'):
                out.append('\t')
            elif c.tag in (qn('w:br'), qn('w:cr')):
                out.append('\n')
        return ''.join(out)

    @staticmethod
    def _clen(c):
        if c.tag == qn('w:t'):
            return len(c.text or '')
        if c.tag in (qn('w:tab'), qn('w:br'), qn('w:cr')):
            return 1
        return 0

    def _split(self, p_el, k):
        pos = 0
        for r in p_el.findall(qn('w:r')):
            t = self._rt(r)
            a, b = pos, pos + len(t)
            if a < k < b:
                off = k - a
                rpr = r.find(qn('w:rPr'))
                der = OxmlElement('w:r')
                if rpr is not None:
                    der.append(copy.deepcopy(rpr))
                q, mover = 0, []
                for c in [c for c in r if c.tag != qn('w:rPr')]:
                    L = self._clen(c)
                    if mover:
                        mover.append(c)
                    elif q + L <= off:
                        pass
                    elif c.tag == qn('w:t') and q < off < q + L:
                        txt = c.text
                        c.text = txt[:off - q]
                        c.set(XML_SPACE, 'preserve')
                        der.append(self._t(txt[off - q:]))
                        mover.append(None)
                    else:
                        mover.append(c)
                    q += L
                for c in mover:
                    if c is not None:
                        der.append(c)
                r.addnext(der)
                return
            pos = b

    def reemplazar(self, p, viejo, nuevo=None, color=VERDE):
        x = p._p if isinstance(p, Paragraph) else p
        full = ''.join(self._rt(r) for r in x.findall(qn('w:r')))
        i = full.find(viejo)
        if i < 0:
            raise KeyError(f'no está: {viejo!r} en {full[:70]!r}')
        f = i + len(viejo)
        self._split(x, f)
        self._split(x, i)
        pos, ult = 0, None
        for r in x.findall(qn('w:r')):
            t = self._rt(r)
            if pos >= i and pos + len(t) <= f and t:
                Run(r, None).font.highlight_color = ROJO
                ult = r
            pos += len(t)
        if nuevo:
            par = Paragraph(x, self.d._body)
            rpr = copy.deepcopy(ult.find(qn('w:rPr'))) if ult.find(qn('w:rPr')) is not None else None
            if rpr is not None:
                for e in rpr.findall(qn('w:highlight')):
                    rpr.remove(e)
            self.texto(par, nuevo, color, after=ult, rpr=rpr)

    # ------------------------------------------------------------ rótulos, notas, tablas, figuras
    def rotulo(self, ancla, tipo, clave, titulo, color=AMARILLO, antes=False):
        """Rótulo APA con campo SEQ (Tabla o Figura) para que entre en las listas."""
        base = self.cap_tabla if tipo == 'Tabla' else self.cap_figura
        p = copy.deepcopy(base)
        for e in list(p):
            if e.tag in (qn('w:bookmarkStart'), qn('w:bookmarkEnd'), qn('w:proofErr')):
                p.remove(e)
        runs = p.findall(qn('w:r'))
        fin = [r for r in runs if r.find(qn('w:fldChar')) is not None and
               r.find(qn('w:fldChar')).get(qn('w:fldCharType')) == 'end'][0]
        quitar = False
        for r in runs:
            if quitar:
                p.remove(r)
            if r is fin:
                quitar = True
        for r in p.iter(qn('w:r')):
            for e in r.findall(qn('w:lastRenderedPageBreak')):
                r.remove(e)
        r = OxmlElement('w:r')
        r.append(OxmlElement('w:br'))
        r.append(self._t(titulo))
        p.append(r)
        if antes:
            self._el(ancla).addprevious(p)
        else:
            self._el(ancla).addnext(p)
        for r in p.iter(qn('w:r')):
            Run(r, None).font.highlight_color = color
        self.claves[p] = (tipo, clave)
        return Paragraph(p, self.d._body)

    def rotulo_anexo(self, ancla, etiqueta, titulo, color=AMARILLO):
        """Rótulo de tabla o figura de anexo: 'Tabla B1' o 'Figura F1' (la clave es lo que sigue a la etiqueta) usa el
        mismo campo SEQ que el cuerpo; 'Listado E1' queda como texto."""
        m = re.match(r'(Tabla|Figura) (\w+)$', etiqueta)
        if m:
            return self.rotulo(ancla, m.group(1), m.group(1)[0].lower() + m.group(2), titulo, color)
        p = self.parrafo(ancla, '', color, estilo='Normal')
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.first_line_indent = Cm(0)
        p.alignment = 0
        self.run(p, etiqueta, color, bold=True)
        r = OxmlElement('w:r')
        r.append(OxmlElement('w:br'))
        r.append(self._t(titulo))
        p._p.append(r)
        ru = Run(r, p)
        ru.font.italic = True
        ru.font.highlight_color = color
        return p

    def nota(self, ancla, texto, color=AMARILLO):
        p_el = self._nuevo_p(self._el(ancla), self.nota_ppr)
        p = Paragraph(p_el, self.d._body)
        if texto.startswith('Nota.'):
            texto = texto[5:].lstrip()
        self.run(p, 'Nota.', color, italic=True, size=10)
        self.texto(p, ' ' + texto, color, size=10)
        return p

    def tabla(self, ancla, filas, anchos, color=AMARILLO, size=9, encabezado=True):
        t = self.d.add_table(rows=len(filas), cols=len(filas[0]))
        t.style = self.d.styles['Table Grid']
        b = OxmlElement('w:tblBorders')
        for lado, val in (('top', 'single'), ('left', 'nil'), ('bottom', 'single'), ('right', 'nil'),
                          ('insideH', 'single'), ('insideV', 'nil')):
            e = OxmlElement(f'w:{lado}')
            e.set(qn('w:val'), val)
            if val != 'nil':
                e.set(qn('w:sz'), '4')
                e.set(qn('w:color'), '000000')
            b.append(e)
        look = t._tbl.tblPr.find(qn('w:tblLook'))
        (look.addprevious(b) if look is not None else t._tbl.tblPr.append(b))
        t.autofit = False
        for j, w in enumerate(anchos):
            t.columns[j].width = Cm(w)
        for i, fila in enumerate(filas):
            for j, val in enumerate(fila):
                c = t.cell(i, j)
                c.width = Cm(anchos[j])
                par = c.paragraphs[0]
                par.style = self.d.styles['Normal']
                par.alignment = 0
                par.paragraph_format.first_line_indent = Cm(0)
                par.paragraph_format.space_after = Pt(0)
                self.texto(par, str(val), color, bold=(encabezado and i == 0), size=size)
        # que no se parta entre páginas: mantener filas juntas
        for k, fila in enumerate(t.rows):
            trPr = fila._tr.get_or_add_trPr()
            cs = OxmlElement('w:cantSplit')
            trPr.append(cs)
            if k < len(t.rows) - 1 and len(t.rows) <= 18:
                for c in fila.cells:
                    for par in c.paragraphs:
                        par.paragraph_format.keep_with_next = True
        self._el(ancla).addnext(t._tbl)
        return t._tbl

    def figura(self, ancla, img, ancho_cm=None, alto_max=18.0, ancho_max=15.5, color=None):
        from PIL import Image
        w, h = Image.open(img).size
        ancho = ancho_cm or min(ancho_max, alto_max * w / h)
        p_el = self._nuevo_p(self._el(ancla))
        p = Paragraph(p_el, self.d._body)
        p.style = self.d.styles['Normal']
        p.alignment = 1
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.first_line_indent = Cm(0)
        r = p.add_run()
        r.add_picture(img, width=Cm(ancho))
        if color is not None:
            r.font.highlight_color = color
        return p

    def codigo(self, ancla, lineas, color=AMARILLO):
        """Listado de código: Courier New 8, interlineado sencillo, sin sangría."""
        last = ancla
        for ln in lineas:
            p = self.parrafo(last, '', color, estilo='Normal')
            pf = p.paragraph_format
            pf.space_after = Pt(0)
            pf.space_before = Pt(0)
            pf.line_spacing = 1.0
            pf.first_line_indent = Cm(0)
            p.alignment = 0
            self.run(p, ln.replace('\t', '    ') if ln else ' ', color, size=8, font='Courier New')
            last = p
        return last

    def marcador(self, p, nombre):
        self.bm_id += 1
        s = OxmlElement('w:bookmarkStart')
        s.set(qn('w:id'), str(self.bm_id))
        s.set(qn('w:name'), nombre)
        e = OxmlElement('w:bookmarkEnd')
        e.set(qn('w:id'), str(self.bm_id))
        ppr = p._p.pPr
        (ppr.addnext(s) if ppr is not None else p._p.insert(0, s))
        p._p.append(e)

    # ------------------------------------------------------------ numeración final
    def numerar(self):
        """Numera los rótulos que quedan (no rojos) y reemplaza {T:clave} / {F:clave} en todo el documento."""
        cont = {'Tabla': 0, 'Figura': 0}
        mapa = {}
        self.cap_info = {}
        for p in self.body.iter(qn('w:p')):
            instr = ''.join(i.text or '' for i in p.iter(qn('w:instrText')))
            simples = [f for f in p.iter(qn('w:fldSimple')) if 'SEQ' in (f.get(qn('w:instr')) or '')]
            instr += ''.join(f.get(qn('w:instr')) for f in simples)
            m = re.search(r'SEQ (Tabla|Figura)', instr)
            if not m:
                continue
            runs = [r for r in p.iter(qn('w:r')) if self._rt(r).strip()]
            rojo = runs and all(self._hl(r) == 'red' for r in runs)
            if rojo:
                continue
            tipo = m.group(1)
            cont[tipo] += 1
            n = cont[tipo]
            # valor en caché del campo
            dentro = False
            for r in p.iter(qn('w:r')):
                fc = r.find(qn('w:fldChar'))
                if fc is not None and fc.get(qn('w:fldCharType')) == 'separate':
                    dentro = True
                    continue
                if fc is not None and fc.get(qn('w:fldCharType')) == 'end':
                    dentro = False
                if dentro and r.find(qn('w:t')) is not None:
                    r.find(qn('w:t')).text = str(n)
            for f in simples:
                for t in f.iter(qn('w:t')):
                    t.text = str(n)
                # rótulo APA: etiqueta y número en negrita
                for r in list(p.findall(qn('w:r')))[:1] + list(f.iter(qn('w:r'))):
                    Run(r, None).font.bold = True
            par = Paragraph(p, self.d._body)
            par.paragraph_format.keep_with_next = True
            self._formato_rotulo(p)
            if p in self.claves:
                mapa[self.claves[p][1]] = f'{tipo} {n}'
                self.cap_info[self.claves[p][1]] = (p, tipo, n)
        # marcadores en los rótulos y referencias cruzadas reales (Referencias > Referencia cruzada > solo rótulo y número)
        for clave, (p_el, tipo, n) in self.cap_info.items():
            self._marcar_rotulo(p_el, f'_Ref_{clave}')
        pat = re.compile(r'\{([TF]):(\w+)\}')
        faltan = set()
        for r in list(self.body.iter(qn('w:r'))):
            t = r.find(qn('w:t'))
            if t is None or not t.text or '{' not in t.text or not pat.search(t.text):
                continue
            partes = pat.split(t.text)          # texto, tipo, clave, texto, ...
            rpr = r.find(qn('w:rPr'))
            padre = r.getparent()
            pos = padre.index(r)
            nuevos = []
            for k in range(0, len(partes), 3):
                if partes[k]:
                    nuevos.append(self._run_texto(partes[k], rpr))
                if k + 2 < len(partes):
                    clave = partes[k + 2]
                    if clave in mapa:
                        nuevos.extend(self._campo_ref(f'_Ref_{clave}', mapa[clave], rpr))
                    else:
                        faltan.add(clave)
                        nuevos.append(self._run_texto('{%s:%s}' % (partes[k + 1], clave), rpr))
            padre.remove(r)
            for j, e in enumerate(nuevos):
                padre.insert(pos + j, e)
        return mapa, faltan

    def _run_texto(self, texto, rpr):
        r = OxmlElement('w:r')
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        r.append(self._t(texto))
        return r

    def _campo_ref(self, marcador, resultado, rpr):
        """Campo REF (referencia cruzada) con el resultado ya calculado: Word lo actualiza al abrir."""
        def fc(tipo):
            r = OxmlElement('w:r')
            if rpr is not None:
                r.append(copy.deepcopy(rpr))
            f = OxmlElement('w:fldChar')
            f.set(qn('w:fldCharType'), tipo)
            r.append(f)
            return r
        ins = OxmlElement('w:r')
        if rpr is not None:
            ins.append(copy.deepcopy(rpr))
        it = OxmlElement('w:instrText')
        it.set(XML_SPACE, 'preserve')
        it.text = f' REF {marcador} \\h '
        ins.append(it)
        return [fc('begin'), ins, fc('separate'), self._run_texto(resultado, rpr), fc('end')]

    def _marcar_rotulo(self, p, nombre):
        """Marcador que cubre 'Tabla N' / 'Figura N' (etiqueta y número) en el rótulo."""
        hijos = list(p)
        ini = next((e for e in hijos if e.tag in (qn('w:r'), qn('w:fldSimple'))), None)
        fin = None
        for e in hijos:
            if e.tag == qn('w:fldSimple'):
                fin = e
                break
            if e.tag == qn('w:r'):
                f = e.find(qn('w:fldChar'))
                if f is not None and f.get(qn('w:fldCharType')) == 'end':
                    fin = e
                    break
        if ini is None or fin is None:
            return
        for b in list(p.iter(qn('w:bookmarkStart'))):
            if b.get(qn('w:name')) == nombre:
                return
        self.bm_id += 1
        a = OxmlElement('w:bookmarkStart')
        a.set(qn('w:id'), str(self.bm_id))
        a.set(qn('w:name'), nombre)
        z = OxmlElement('w:bookmarkEnd')
        z.set(qn('w:id'), str(self.bm_id))
        ini.addprevious(a)
        fin.addnext(z)

    def _formato_rotulo(self, p):
        """Plantilla USB: 'Figura N' en negrita y el título en cursiva en la línea siguiente."""
        hijos = list(p)
        fin = None
        for k, e in enumerate(hijos):
            if e.tag == qn('w:fldSimple'):
                fin = k
            if e.tag == qn('w:r') and e.find(qn('w:fldChar')) is not None and \
                    e.find(qn('w:fldChar')).get(qn('w:fldCharType')) == 'end':
                fin = k
        if fin is None:
            return
        titulo = [e for e in hijos[fin + 1:] if e.tag == qn('w:r') and self._rt(e).strip()]
        if not titulo:
            return
        if not any(e.find(qn('w:br')) is not None for e in hijos[fin + 1:] if e.tag == qn('w:r')):
            primero = titulo[0]
            br = OxmlElement('w:br')
            rpr = primero.find(qn('w:rPr'))
            (rpr.addnext(br) if rpr is not None else primero.insert(0, br))
            t = primero.find(qn('w:t'))
            if t is not None and t.text:
                t.text = t.text.lstrip()
        for r in titulo:
            ru = Run(r, None)
            ru.font.italic = True
            ru.font.bold = False

    @staticmethod
    def _hl(r):
        rpr = r.find(qn('w:rPr'))
        h = rpr.find(qn('w:highlight')) if rpr is not None else None
        return h.get(qn('w:val')) if h is not None else None
