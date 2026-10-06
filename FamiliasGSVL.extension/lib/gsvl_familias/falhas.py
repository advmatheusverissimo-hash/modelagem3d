# -*- coding: utf-8 -*-
"""Captura de avisos/erros do Revit durante transações (sem caixas de diálogo)."""
from Autodesk.Revit.DB import (IFailuresPreprocessor, FailureProcessingResult,
                               FailureSeverity, Transaction)


class ColetorFalhas(IFailuresPreprocessor):
    def __init__(self, log=None, prefixo=u""):
        self.log = log
        self.prefixo = prefixo
        self.avisos = []
        self.erros = []

    def PreprocessFailures(self, fa):
        tem_erro = False
        for f in fa.GetFailureMessages():
            txt = f.GetDescriptionText()
            if f.GetSeverity() == FailureSeverity.Warning:
                self.avisos.append(txt)
                if self.log:
                    self.log.aviso(self.prefixo + txt)
                fa.DeleteWarning(f)
            else:
                tem_erro = True
                self.erros.append(txt)
                if self.log:
                    self.log.erro(self.prefixo + txt)
        if tem_erro:
            return FailureProcessingResult.ProceedWithRollBack
        return FailureProcessingResult.Continue


def transacao(doc, nome, coletor):
    t = Transaction(doc, nome)
    opts = t.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(coletor)
    opts.SetClearAfterRollback(True)
    t.SetFailureHandlingOptions(opts)
    return t
