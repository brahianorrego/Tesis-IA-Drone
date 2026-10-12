"""Abre un .docx en LibreOffice, actualiza índices y campos, y exporta a PDF (no modifica el .docx)."""
import os
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(n, v):
    p = PropertyValue()
    p.Name, p.Value = n, v
    return p


proc = subprocess.Popen(['soffice', '--headless', '--invisible', '--norestore',
                         '--accept=socket,host=localhost,port=2002;urp;'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ctx = None
for _ in range(60):
    try:
        local = uno.getComponentContext()
        res = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
        ctx = res.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
        break
    except Exception:
        time.sleep(1)
smgr = ctx.ServiceManager
desk = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
for ruta in sys.argv[1:]:
    url = uno.systemPathToFileUrl(os.path.abspath(ruta))
    doc = desk.loadComponentFromURL(url, '_blank', 0, (prop('Hidden', True),))
    doc.getTextFields().refresh()
    idx = doc.getDocumentIndexes()
    for i in range(idx.getCount()):
        idx.getByIndex(i).update()
    doc.getTextFields().refresh()
    salida = uno.systemPathToFileUrl(os.path.abspath(os.path.splitext(ruta)[0] + '.pdf'))
    doc.storeToURL(salida, (prop('FilterName', 'writer_pdf_Export'),))
    doc.close(True)
    print('PDF:', salida)
try:
    desk.terminate()
except Exception:
    pass
proc.wait(timeout=30)
