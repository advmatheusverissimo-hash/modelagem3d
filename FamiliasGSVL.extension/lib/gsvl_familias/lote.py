# -*- coding: utf-8 -*-
"""Rodar Tudo: gera todas as famílias, roda o flex test em cada uma e monta a casa-teste.

Grava um resumo curto (output/logs/lote_*.log) para colar no chat; os detalhes
ficam nos logs de cada etapa. IronPython 2.7: sem f-strings.
"""
import glob
import os

from gsvl_familias import casa_revit, flex
from gsvl_familias import spec as specmod
from gsvl_familias.construtor import _sem_acento, gerar
from gsvl_familias.util import Log, config, raiz_repo

CHAVES_PROJETO = (u"arquitet", u"architect", u"construc", u"default", u"padrao")


def template_projeto(app, log):
    """Template de projeto: o padrão do Revit (Opções) ou o .rte de arquitetura da pasta Templates."""
    try:
        padrao = app.DefaultProjectTemplate
    except Exception:
        padrao = None
    if padrao and os.path.exists(padrao):
        return padrao
    cfg = config()
    pasta = cfg.get("templates_projeto_dir") or os.path.join(
        os.path.dirname(cfg["templates_dir"].rstrip(u"\\/")), u"Templates")
    rtes = []
    for raiz, _d, arqs in os.walk(pasta):
        rtes.extend(os.path.join(raiz, a) for a in arqs if a.lower().endswith(u".rte"))
    for chave in CHAVES_PROJETO:
        for r in rtes:
            if chave in _sem_acento(os.path.basename(r)):
                return r
    if rtes:
        log.aviso(u"Nenhum template de arquitetura reconhecido; usando " + rtes[0])
        return rtes[0]
    raise IOError(u"Nenhum template de projeto (.rte) encontrado em " + pasta)


def _ordem_specs():
    """Armário primeiro (piloto escolhido), depois o resto em ordem alfabética."""
    specs = sorted(glob.glob(os.path.join(raiz_repo(), u"specs", u"*.json")))
    return sorted(specs, key=lambda c: (u"armario" not in os.path.basename(c), c))


def rodar(app, uiapp, resumo):
    """Executa tudo e escreve o resumo. Devolve o caminho do .rvt da casa (ou None)."""
    resumo.info(u"Revit {0} ({1}) | pyRevit lote".format(app.VersionNumber, app.VersionBuild))

    # 1) famílias + flex test
    for caminho in _ordem_specs():
        nome = os.path.splitext(os.path.basename(caminho))[0]
        erros_spec = specmod.validar(specmod.carregar(caminho))
        if erros_spec:
            resumo.erro(u"{0}: spec reprovada ({1} erro(s)) — rode tools/validar_specs.py".format(nome, len(erros_spec)))
            continue
        log_g = Log(u"gerar_" + nome)
        try:
            destino = gerar(app, caminho, log_g)
        except Exception as e:
            log_g.erro(u"Exceção: {0}".format(e))
            destino = None
        if not destino:
            resumo.erro(u"{0}: geração FALHOU — {1}".format(nome, log_g.resumo()))
            for linha in [l for l in log_g.linhas if l.startswith(u"[ERRO]")][:8]:
                resumo.info(u"    " + linha)
            continue
        kb = os.path.getsize(destino) / 1024.0
        (resumo.aviso if log_g.erros or log_g.avisos else resumo.info)(
            u"{0}: gerada ({1:.0f} KB) — {2}".format(nome, kb, log_g.resumo()))
        for linha in [l for l in log_g.linhas if not l.startswith(u"[INFO]")][:8]:
            resumo.info(u"    " + linha)

        log_f = Log(u"flex_" + nome)
        doc = None
        try:
            doc = app.OpenDocumentFile(destino)
            ok = flex.rodar(doc, log_f)
        except Exception as e:
            log_f.erro(u"Exceção: {0}".format(e))
            ok = False
        finally:
            if doc is not None:
                doc.Close(False)
        (resumo.info if ok else resumo.erro)(u"{0}: flex test {1} — {2}".format(
            nome, u"APROVADO" if ok else u"REPROVADO", log_f.resumo()))
        for linha in [l for l in log_f.linhas if l.startswith(u"[ERRO]")][:8]:
            resumo.info(u"    " + linha)

    # 2) casa-teste num projeto novo
    log_c = Log(u"casa_teste")
    destino_casa = None
    try:
        rte = template_projeto(app, log_c)
        log_c.info(u"Template de projeto: " + rte)
        doc = app.NewProjectDocument(rte)
        destino_casa = casa_revit.construir(doc, os.path.join(raiz_repo(), u"casa", u"casa_teste.json"), log_c)
        doc.Close(False)
    except Exception as e:
        log_c.erro(u"Exceção: {0}".format(e))
    (resumo.aviso if log_c.erros or log_c.avisos else resumo.info)(u"Casa-teste: " + log_c.resumo())
    for linha in [l for l in log_c.linhas if not l.startswith(u"[INFO]") or u"Conferência" in l][:20]:
        resumo.info(u"    " + linha)

    if destino_casa and os.path.exists(destino_casa):
        try:
            uiapp.OpenAndActivateDocument(destino_casa)
        except Exception as e:
            resumo.aviso(u"Não abri a casa automaticamente ({0}); abra {1}".format(e, destino_casa))
        return destino_casa
    return None
