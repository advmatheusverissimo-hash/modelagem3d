# -*- coding: utf-8 -*-
"""Valida todas as specs (ou as passadas como argumento) fora do Revit.

Uso: python tools/validar_specs.py [specs/arquivo.json ...]
Checa estrutura, nomes, eixos, expressões, faixas, tipos e se todas as caixas
mantêm dimensões positivas no padrão, em cada tipo e em todos os extremos das faixas.
"""
import glob
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "FamiliasGSVL.extension", "lib", "gsvl_familias"))
import spec as specmod  # noqa: E402  (módulo puro, sem API do Revit)


def main(arquivos):
    arquivos = arquivos or sorted(glob.glob(os.path.join(RAIZ, "specs", "*.json")))
    falhou = False
    for caminho in arquivos:
        sp = specmod.carregar(caminho)
        erros = specmod.validar(sp)
        nome = os.path.basename(caminho)
        if erros:
            falhou = True
            print("REPROVADA  {0}".format(nome))
            for e in erros:
                print("   - " + e)
        else:
            n_cen = sum(1 for _ in specmod.cenarios(sp))
            print("OK         {0}  ({1} planos, {2} caixas, {3} tipos, {4} cenários testados)".format(
                nome, len(sp["planos"]), len(sp["caixas"]), len(sp["tipos"]), n_cen))
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
