# -*- coding: utf-8 -*-
"""Leitura e validação de specs JSON.

Python puro, compatível com IronPython 2.7 (pyRevit) e Python 3 (validador).
Não importa nada da API do Revit.
"""
import codecs
import json
import itertools

TIPOS_PARAM = ("comprimento", "simnao", "material", "texto")
EIXOS = ("x", "y", "z")
DETALHES = ("coarse", "medium", "fine")
REFERENCIAS = ("Left", "Right", "Front", "Back", "Top", "Bottom",
               "CenterLeftRight", "CenterFrontBack", "CenterElevation",
               "StrongReference", "WeakReference", "NotAReference")
# planos especiais vindos do template
ESPECIAIS = {"@centro_x": "x", "@centro_y": "y", "@nivel": "z"}


def carregar(caminho):
    with codecs.open(caminho, "r", "utf-8-sig") as f:
        return json.loads(f.read())


def params_comprimento(spec):
    return [p for p in spec["parametros"] if p["tipo"] == "comprimento"]


def params_livres(spec):
    """Parâmetros de comprimento sem fórmula (os que o usuário controla)."""
    return [p for p in params_comprimento(spec) if not p.get("formula")]


def aplicar_formulas(spec, valores):
    """Recalcula, na ordem da spec, os parâmetros de comprimento com fórmula."""
    v = dict(valores)
    for p in params_comprimento(spec):
        if p.get("formula"):
            v[p["nome"]] = avaliar(p["formula"], v)
    return v


def valores_padrao(spec):
    base = dict((p["nome"], float(p["padrao"])) for p in params_comprimento(spec))
    return aplicar_formulas(spec, base)


def avaliar(expr, valores):
    """Avalia expressão em mm usando os parâmetros como variáveis."""
    return float(eval(expr, {"__builtins__": {}}, dict(valores)))


def posicoes_planos(spec, valores):
    """Retorna {nome_plano: (eixo, pos_mm)} incluindo os especiais."""
    pos = {"@centro_x": ("x", 0.0), "@centro_y": ("y", 0.0), "@nivel": ("z", 0.0)}
    for pl in spec["planos"]:
        pos[pl["nome"]] = (pl["eixo"], avaliar(pl["pos"], valores))
    return pos


def validar(spec):
    """Retorna lista de erros (vazia = ok)."""
    erros = []
    for chave in ("nome_arquivo", "templates", "parametros", "planos", "cotas", "caixas", "tipos"):
        if chave not in spec:
            erros.append("Falta a chave '{0}'".format(chave))
    if erros:
        return erros

    nomes_param = set()
    por_tipo = {}
    for p in spec["parametros"]:
        if p.get("tipo") not in TIPOS_PARAM:
            erros.append("Parâmetro {0}: tipo inválido {1}".format(p.get("nome"), p.get("tipo")))
        if p["nome"] in nomes_param:
            erros.append("Parâmetro duplicado: {0}".format(p["nome"]))
        nomes_param.add(p["nome"])
        por_tipo[p["nome"]] = p["tipo"]
        if p["tipo"] == "comprimento":
            if "padrao" not in p or "faixa" not in p:
                erros.append("Parâmetro {0}: comprimento exige 'padrao' e 'faixa'".format(p["nome"]))
            elif not (p["faixa"][0] <= p["padrao"] <= p["faixa"][1]):
                erros.append("Parâmetro {0}: padrão fora da faixa".format(p["nome"]))
            if p.get("formula"):
                try:
                    aplicar_formulas(spec, dict((x["nome"], float(x.get("padrao", 0)))
                                                for x in params_comprimento(spec)))
                except Exception as e:
                    erros.append("Parâmetro {0}: fórmula '{1}' inválida ({2})".format(p["nome"], p["formula"], e))

    padrao = valores_padrao(spec)
    nomes_plano = set(ESPECIAIS)
    eixo_plano = dict(ESPECIAIS)
    for pl in spec["planos"]:
        if pl["eixo"] not in EIXOS:
            erros.append("Plano {0}: eixo inválido".format(pl["nome"]))
        if pl.get("referencia", "WeakReference") not in REFERENCIAS:
            erros.append("Plano {0}: referência inválida".format(pl["nome"]))
        if pl["nome"] in nomes_plano:
            erros.append("Plano duplicado: {0}".format(pl["nome"]))
        nomes_plano.add(pl["nome"])
        eixo_plano[pl["nome"]] = pl["eixo"]
        try:
            avaliar(pl["pos"], padrao)
        except Exception as e:
            erros.append("Plano {0}: expressão '{1}' inválida ({2})".format(pl["nome"], pl["pos"], e))
    if erros:
        return erros

    # Cotas
    for i, c in enumerate(spec["cotas"]):
        pls = c["planos"]
        if any(n not in nomes_plano for n in pls):
            erros.append("Cota {0}: plano inexistente em {1}".format(i, pls))
            continue
        if len(set(eixo_plano[n] for n in pls)) != 1:
            erros.append("Cota {0}: planos de eixos diferentes {1}".format(i, pls))
        if c.get("eq"):
            if len(pls) < 3:
                erros.append("Cota {0}: EQ precisa de 3+ planos".format(i))
        elif "rotulo" in c:
            if len(pls) != 2:
                erros.append("Cota {0}: cota rotulada precisa de 2 planos".format(i))
            if por_tipo.get(c["rotulo"]) != "comprimento":
                erros.append("Cota {0}: rótulo {1} não é parâmetro de comprimento".format(i, c["rotulo"]))
        else:
            erros.append("Cota {0}: defina 'eq' ou 'rotulo'".format(i))

    # Caixas
    for cx in spec["caixas"]:
        for eixo in EIXOS:
            par = cx.get(eixo)
            if not par or len(par) != 2:
                erros.append("Caixa {0}: '{1}' precisa de [min, max]".format(cx["nome"], eixo))
                continue
            for n in par:
                if n not in nomes_plano:
                    erros.append("Caixa {0}: plano {1} inexistente".format(cx["nome"], n))
                elif eixo_plano[n] != eixo:
                    erros.append("Caixa {0}: plano {1} não é do eixo {2}".format(cx["nome"], n, eixo))
        for chave, tipo in (("material", "material"), ("visivel", "simnao")):
            if chave in cx and por_tipo.get(cx[chave]) != tipo:
                erros.append("Caixa {0}: '{1}' deve apontar para parâmetro {2}".format(cx["nome"], chave, tipo))
        for d in cx.get("detalhe", DETALHES):
            if d not in DETALHES:
                erros.append("Caixa {0}: detalhe inválido {1}".format(cx["nome"], d))

    for seq in spec.get("ordens", []):
        for n in seq:
            if n not in nomes_plano:
                erros.append("Ordem: plano {0} inexistente".format(n))
        if len(set(eixo_plano.get(n) for n in seq)) != 1:
            erros.append("Ordem {0}: planos de eixos diferentes".format(seq))

    # Tipos
    for t in spec["tipos"]:
        for k, v in t["valores"].items():
            p = [x for x in spec["parametros"] if x["nome"] == k]
            if not p:
                erros.append("Tipo {0}: parâmetro {1} inexistente".format(t["nome"], k))
            elif p[0].get("formula"):
                erros.append("Tipo {0}: {1} tem fórmula e não pode receber valor".format(t["nome"], k))
            elif p[0]["tipo"] == "comprimento" and not (p[0]["faixa"][0] <= v <= p[0]["faixa"][1]):
                erros.append("Tipo {0}: {1}={2} fora da faixa".format(t["nome"], k, v))
    if erros:
        return erros

    # Geometria: todas as caixas com dimensões positivas em todas as combinações de extremos
    erros.extend(checar_geometria(spec))
    return erros


def cenarios(spec, limite=65536):
    """Padrão, tipos e combinações min/max das faixas (fórmulas recalculadas)."""
    base = valores_padrao(spec)
    yield "padrao", base
    for t in spec["tipos"]:
        v = dict(base)
        v.update(dict((k, float(x)) for k, x in t["valores"].items() if k in base))
        yield "tipo " + t["nome"], aplicar_formulas(spec, v)
    livres = params_livres(spec)
    nomes = [p["nome"] for p in livres]
    faixas = [p["faixa"] for p in livres]
    n = 0
    for combo in itertools.product(*[(f[0], f[1]) for f in faixas]):
        n += 1
        if n > limite:
            break
        yield "extremos", aplicar_formulas(spec, dict(zip(nomes, [float(c) for c in combo])))


def checar_geometria(spec, folga_mm=1.0):
    erros = []
    vistos = set()
    for nome_cen, valores in cenarios(spec):
        pos = posicoes_planos(spec, valores)
        # "ordens": sequências de planos que devem permanecer em ordem crescente
        for seq in spec.get("ordens", []):
            for a, b in zip(seq, seq[1:]):
                if pos[b][1] - pos[a][1] < folga_mm and ("ordem", a, b) not in vistos:
                    vistos.add(("ordem", a, b))
                    erros.append("Ordem violada: {0} deveria ficar antes de {1} no cenário {2} {3}".format(
                        a, b, nome_cen, valores))
        for cx in spec["caixas"]:
            for eixo in EIXOS:
                a, b = cx[eixo]
                d = pos[b][1] - pos[a][1]
                if d < folga_mm:
                    chave = (cx["nome"], eixo)
                    if chave not in vistos:
                        vistos.add(chave)
                        erros.append("Caixa {0}: dimensão {1} = {2:.1f} mm no cenário {3} {4}".format(
                            cx["nome"], eixo, d, nome_cen, valores))
    return erros
