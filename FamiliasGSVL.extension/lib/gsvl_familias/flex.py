# -*- coding: utf-8 -*-
"""Flex test: percorre tipos e extremos das faixas e registra erros/avisos.

Nada é salvo: tudo roda dentro de um TransactionGroup que é desfeito no final.
"""
import glob
import os

from Autodesk.Revit.DB import TransactionGroup, TransactionStatus

from gsvl_familias import spec as specmod
from gsvl_familias.falhas import ColetorFalhas, transacao
from gsvl_familias.util import mm, raiz_repo


def spec_da_familia(doc):
    """Acha a spec cujo nome_arquivo bate com o nome do .rfa."""
    nome = os.path.splitext(os.path.basename(doc.PathName or doc.Title))[0]
    for caminho in glob.glob(os.path.join(raiz_repo(), "specs", "*.json")):
        sp = specmod.carregar(caminho)
        if sp.get("nome_arquivo") == nome:
            return sp
    return None


def _casos(fm, sp):
    """Lista de (descrição, {param: valor_mm}) por tipo."""
    if sp is None:
        return [(u"atual", {})]
    casos = [(u"valores do tipo", {})]
    params = specmod.params_comprimento(sp)
    for p in params:
        if p.get("formula"):
            continue
        casos.append((u"{0}=min".format(p["nome"]), {p["nome"]: p["faixa"][0]}))
        casos.append((u"{0}=max".format(p["nome"]), {p["nome"]: p["faixa"][1]}))
    casos.append((u"todos=min", dict((p["nome"], p["faixa"][0]) for p in params if not p.get("formula"))))
    casos.append((u"todos=max", dict((p["nome"], p["faixa"][1]) for p in params if not p.get("formula"))))
    return casos


def rodar(doc, log):
    if not doc.IsFamilyDocument:
        log.erro(u"O documento ativo não é uma família")
        return False
    fm = doc.FamilyManager
    sp = spec_da_familia(doc)
    log.info(u"Família: {0} | spec: {1}".format(doc.Title, sp["nome_arquivo"] if sp else u"(não encontrada)"))
    casos = _casos(fm, sp)
    tipos = list(fm.Types)
    falhas_total = 0

    tg = TransactionGroup(doc, u"Flex test")
    tg.Start()
    try:
        for tipo in tipos:
            for desc, valores in casos:
                rotulo = u"[{0} | {1}] ".format(tipo.Name, desc)
                col = ColetorFalhas(log, rotulo)
                t = transacao(doc, u"flex", col)
                t.Start()
                try:
                    fm.CurrentType = tipo
                    for nome, v in valores.items():
                        fm.Set(fm.get_Parameter(nome), mm(v))
                    doc.Regenerate()
                    status = t.Commit()
                except Exception as e:
                    if t.HasStarted() and not t.HasEnded():
                        t.RollBack()
                    log.erro(rotulo + u"exceção: {0}".format(e))
                    falhas_total += 1
                    continue
                if status != TransactionStatus.Committed or col.erros:
                    falhas_total += 1
                    log.erro(rotulo + u"FALHOU ({0})".format(status))
                else:
                    log.info(rotulo + u"ok")
    finally:
        tg.RollBack()

    if doc.PathName and os.path.exists(doc.PathName):
        kb = os.path.getsize(doc.PathName) / 1024.0
        (log.aviso if kb > 500 else log.info)(u"Tamanho do arquivo: {0:.0f} KB (meta < 500 KB)".format(kb))
    log.info(u"Casos com falha: {0}".format(falhas_total))
    return falhas_total == 0
