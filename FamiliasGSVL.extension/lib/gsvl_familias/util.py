# -*- coding: utf-8 -*-
"""Utilitários: caminhos do repositório, config, unidades e log."""
import codecs
import datetime
import json
import os

MM_POR_PE = 304.8


def mm(valor_mm):
    """mm -> pés (unidade interna do Revit)."""
    return float(valor_mm) / MM_POR_PE


def raiz_repo():
    # .../familias-revit/FamiliasGSVL.extension/lib/gsvl_familias/util.py
    aqui = os.path.abspath(__file__)
    for _ in range(4):
        aqui = os.path.dirname(aqui)
    return aqui


def config():
    with codecs.open(os.path.join(raiz_repo(), "config.json"), "r", "utf-8-sig") as f:
        return json.loads(f.read())


def pasta(rel):
    p = os.path.join(raiz_repo(), rel)
    if not os.path.isdir(p):
        os.makedirs(p)
    return p


class Log(object):
    """Grava em output/logs/<nome>_<data>.log e mantém as linhas em memória."""

    def __init__(self, nome):
        cfg = config()
        carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.caminho = os.path.join(pasta(cfg["saida_logs"]), "{0}_{1}.log".format(nome, carimbo))
        self.linhas = []
        self.erros = 0
        self.avisos = 0

    def _w(self, nivel, msg):
        linha = u"[{0}] {1}".format(nivel, msg)
        self.linhas.append(linha)
        with codecs.open(self.caminho, "a", "utf-8") as f:
            f.write(linha + u"\n")

    def info(self, msg):
        self._w("INFO", msg)

    def aviso(self, msg):
        self.avisos += 1
        self._w("AVISO", msg)

    def erro(self, msg):
        self.erros += 1
        self._w("ERRO", msg)

    def resumo(self):
        return u"{0} erro(s), {1} aviso(s). Log: {2}".format(self.erros, self.avisos, self.caminho)
