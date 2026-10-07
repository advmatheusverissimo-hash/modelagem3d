# -*- coding: utf-8 -*-
"""Gera uma família .rfa a partir de uma spec JSON da pasta specs/."""
__title__ = "Gerar\nFamília"
__context__ = "zero-doc"  # funciona com o Revit na tela inicial, sem projeto aberto
__doc__ = "Escolha uma spec JSON e gere o .rfa em output/rfa (log em output/logs)."

import os

from pyrevit import forms

from gsvl_familias.construtor import gerar
from gsvl_familias.util import Log, raiz_repo

app = __revit__.Application  # noqa: F821 (injetado pelo pyRevit)
uiapp = __revit__            # noqa: F821

caminho = forms.pick_file(file_ext="json", init_dir=os.path.join(raiz_repo(), "specs"))
if caminho:
    nome = os.path.splitext(os.path.basename(caminho))[0]
    log = Log("gerar_" + nome)
    destino = gerar(app, caminho, log)
    print(log.resumo())
    for linha in log.linhas:
        print(linha)
    if destino and forms.alert(u"Família gerada. Abrir agora?", yes=True, no=True):
        uiapp.OpenAndActivateDocument(destino)
