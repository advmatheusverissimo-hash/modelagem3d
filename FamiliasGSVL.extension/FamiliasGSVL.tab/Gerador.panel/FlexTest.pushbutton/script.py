# -*- coding: utf-8 -*-
"""Flex test da família ativa (ou de um .rfa escolhido)."""
__title__ = "Flex\nTest"
__context__ = "zero-doc"  # funciona com o Revit na tela inicial, sem projeto aberto
__doc__ = "Testa todos os tipos e os extremos das faixas da spec. Não altera o arquivo."

import os

from pyrevit import forms

from gsvl_familias import flex
from gsvl_familias.util import Log, config, raiz_repo

app = __revit__.Application  # noqa: F821
doc = __revit__.ActiveUIDocument.Document if __revit__.ActiveUIDocument else None  # noqa: F821

abriu = False
if doc is None or not doc.IsFamilyDocument:
    caminho = forms.pick_file(file_ext="rfa", init_dir=os.path.join(raiz_repo(), config()["saida_rfa"]))
    doc = app.OpenDocumentFile(caminho) if caminho else None
    abriu = doc is not None

if doc is not None:
    log = Log("flex_" + os.path.splitext(doc.Title)[0])
    ok = flex.rodar(doc, log)
    print((u"APROVADA. " if ok else u"REPROVADA. ") + log.resumo())
    for linha in log.linhas:
        print(linha)
    if abriu:
        doc.Close(False)
