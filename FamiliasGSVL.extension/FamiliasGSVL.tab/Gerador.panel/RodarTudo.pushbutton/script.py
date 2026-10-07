# -*- coding: utf-8 -*-
"""Gera todas as famílias, roda o flex test e monta a casa-teste mobiliada."""
__title__ = "Rodar\nTudo"
__context__ = "zero-doc"  # funciona com o Revit na tela inicial, sem projeto aberto
__doc__ = ("Gera todas as specs em output/rfa, roda o flex test em cada uma, cria a casa-teste "
           "num projeto novo, insere os móveis e abre a casa. No fim, copie o resumo e cole no chat.")

from gsvl_familias import lote
from gsvl_familias.util import Log

app = __revit__.Application  # noqa: F821 (injetado pelo pyRevit)
uiapp = __revit__            # noqa: F821

resumo = Log("lote")
lote.rodar(app, uiapp, resumo)
print(u"===== RESUMO (copie daqui até o fim e cole no chat) =====")
for linha in resumo.linhas:
    print(linha)
print(resumo.resumo())
