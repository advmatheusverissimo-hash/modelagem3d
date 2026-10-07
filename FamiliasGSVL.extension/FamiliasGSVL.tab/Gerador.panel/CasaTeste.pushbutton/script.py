# -*- coding: utf-8 -*-
"""Constrói a casa-teste (casa/casa_teste.json) no projeto ativo e a mobilia com as famílias GSVL."""
__title__ = "Casa\nTeste"
__doc__ = "Abra um projeto NOVO e clique: cria paredes, portas, janelas, piso, ambientes e insere os móveis de output/rfa."

import os

from gsvl_familias.casa_revit import construir
from gsvl_familias.util import Log, raiz_repo

doc = __revit__.ActiveUIDocument.Document  # noqa: F821 (injetado pelo pyRevit)

log = Log("casa_teste")
destino = construir(doc, os.path.join(raiz_repo(), "casa", "casa_teste.json"), log)
print(log.resumo())
for linha in log.linhas:
    print(linha)
