"""Construye la copia intervenida del Word. Uso: python construir.py original.docx salida.docx DIAGRAMAS REPO"""
import copy
import sys

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

import c1_inicio
import c2_marcos
import c3_arquitectura
import c4_integracion
import c5_anexos
from motor import AMARILLO, TURQ, VERDE, Motor

ENT, SAL, DIAG, REPO = sys.argv[1:5]
M = Motor(ENT)
P = M.P
movidos = {}


def reescribir(indices, textos):
    ps = [P[i] for i in indices]
    for p in ps:
        M.marcar(p)
    last = ps[-1]
    for t in textos:
        last = M.parrafo(last, '', VERDE, ppr_de=ps[0])
        M.texto(last, t, VERDE)
    return last


def mover(items, letra, clave):
    els = [M.T[it[1]]._tbl if isinstance(it, tuple) else P[it]._p for it in items]
    movidos[clave] = [copy.deepcopy(e) for e in els]
    for e in els:
        M.marcar(e)
    M.parrafo(els[-1], f'[REVISAR: este contenido se movió al Anexo {letra}]', TURQ, estilo='Párr.APA')


c1_inicio.aplicar(M, reescribir)
c2_marcos.aplicar(M, reescribir, mover, DIAG)
c3_arquitectura.aplicar(M, reescribir, mover, DIAG)
c4_integracion.aplicar(M, reescribir, mover, DIAG)
c5_anexos.aplicar(M, movidos, REPO)
mapa, faltan = M.numerar()
from pulir import pulir
pulir(M.d, quitar_vacios=False)
print('Rótulos:', mapa)
print('Claves sin resolver:', faltan or 'ninguna')

# Word actualiza la tabla de contenido y las listas al abrir
st = M.d.settings.element
if st.find(qn('w:updateFields')) is None:
    u = OxmlElement('w:updateFields')
    u.set(qn('w:val'), 'true')
    despues = {'hdrShapeDefaults', 'footnotePr', 'endnotePr', 'compat', 'docVars', 'rsids', 'mathPr', 'attachedSchema',
               'themeFontLang', 'clrSchemeMapping', 'doNotIncludeSubdocsInStats', 'doNotAutoCompressPictures',
               'forceUpgrade', 'captions', 'readModeInkLockDown', 'smartTagType', 'schemaLibrary', 'shapeDefaults',
               'doNotEmbedSmartTags', 'decimalSymbol', 'listSeparator'}
    sig = next((c for c in st if c.tag.split('}')[1] in despues), None)
    (sig.addprevious(u) if sig is not None else st.append(u))
M.d.save(SAL)
print('Listo:', SAL)
