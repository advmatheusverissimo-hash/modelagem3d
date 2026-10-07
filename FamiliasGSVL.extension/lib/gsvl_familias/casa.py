# -*- coding: utf-8 -*-
"""Casa-teste: leitura e checagem geométrica (sem API do Revit).

Python puro, compatível com IronPython 2.7 (pyRevit) e Python 3 (validador).
Coordenadas em mm pelos eixos das paredes.
"""
import codecs
import json
import os

from gsvl_familias import spec as specmod

TOL = 1.0  # mm


def carregar(caminho):
    with codecs.open(caminho, "r", "utf-8-sig") as f:
        return json.loads(f.read())


# ------------------------------------------------------------------ paredes
def _esp(casa, parede):
    return float(casa["paredes_tipos"][parede["tipo"]]["espessura"])


def parede_em(casa, ponto):
    """Parede cujo eixo contém o ponto (ou None)."""
    x, y = ponto
    for p in casa["paredes"]:
        (x0, y0), (x1, y1) = p["de"], p["ate"]
        if abs(x0 - x1) < TOL and abs(x - x0) < TOL and min(y0, y1) - TOL <= y <= max(y0, y1) + TOL:
            return p
        if abs(y0 - y1) < TOL and abs(y - y0) < TOL and min(x0, x1) - TOL <= x <= max(x0, x1) + TOL:
            return p
    return None


def _vertical(p):
    return abs(p["de"][0] - p["ate"][0]) < TOL


def retangulo_interno(casa, amb):
    """Retângulo livre do ambiente: eixos menos meia espessura das paredes que o limitam."""
    x0, y0, x1, y1 = [float(v) for v in amb["eixos"]]
    lados = {"x0": ((x0, (y0 + y1) / 2.0), +1), "x1": ((x1, (y0 + y1) / 2.0), -1),
             "y0": (((x0 + x1) / 2.0, y0), +1), "y1": (((x0 + x1) / 2.0, y1), -1)}
    r = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}
    for lado, (pt, sinal) in lados.items():
        p = parede_em(casa, pt)
        if p is not None:
            r[lado] += sinal * _esp(casa, p) / 2.0
    return (r["x0"], r["y0"], r["x1"], r["y1"])


# ------------------------------------------------------------------- móveis
def _dims_tipo(caminho_specs, familia, tipo):
    """(Largura, Profundidade) do tipo, lidos da spec da família (ou None)."""
    if not os.path.isdir(caminho_specs):
        return None
    for nome in os.listdir(caminho_specs):
        if not nome.endswith(".json"):
            continue
        sp = specmod.carregar(os.path.join(caminho_specs, nome))
        if sp.get("nome_arquivo") != familia:
            continue
        base = specmod.valores_padrao(sp)
        for t in sp["tipos"]:
            if t["nome"] == tipo:
                v = dict(base)
                v.update(t["valores"])
                return float(v["Largura"]), float(v["Profundidade"])
        return None
    return None


def pegada(movel, dims):
    """Retângulo em planta (x0, y0, x1, y1) do móvel, considerando a rotação."""
    L, P = dims
    rot = int(movel.get("rot", 0)) % 360
    if rot not in (0, 90, 180, 270):
        raise ValueError(u"rot {0} não suportada (use 0/90/180/270)".format(rot))
    if rot in (90, 270):
        L, P = P, L
    cx, cy = [float(v) for v in movel["em"]]
    return (cx - L / 2.0, cy - P / 2.0, cx + L / 2.0, cy + P / 2.0)


def _sobrepoe(a, b, folga=0.0):
    return (a[0] < b[2] - folga and b[0] < a[2] - folga and
            a[1] < b[3] - folga and b[1] < a[3] - folga)


def area_porta(casa, porta):
    """Faixa livre de giro da porta: largura da folha para os dois lados da parede."""
    p = parede_em(casa, porta["em"])
    x, y = porta["em"]
    w = float(porta["largura"])
    if _vertical(p):
        return (x - w, y - w / 2.0, x + w, y + w / 2.0)
    return (x - w / 2.0, y - w, x + w / 2.0, y + w)


# ---------------------------------------------------------------- validação
def validar(casa, caminho_specs):
    """Retorna (erros, avisos, pegadas{indice: retângulo})."""
    erros, avisos = [], []
    ambientes = dict((a["nome"], a) for a in casa["ambientes"])

    # aberturas: na parede, dentro dela e sem colidir umas com as outras
    aberturas = [("porta", a) for a in casa["portas"]] + [("janela", a) for a in casa["janelas"]]
    ocupado = []
    for tipo, ab in aberturas:
        p = parede_em(casa, ab["em"])
        if p is None:
            erros.append(u"{0} {1}: ponto {2} não está no eixo de nenhuma parede".format(tipo, ab["nome"], ab["em"]))
            continue
        ix = 1 if _vertical(p) else 0
        c = float(ab["em"][ix])
        a0, a1 = sorted([p["de"][ix], p["ate"][ix]])
        meia = float(ab["largura"]) / 2.0
        if c - meia < a0 + 100 or c + meia > a1 - 100:
            erros.append(u"{0} {1}: não cabe na parede (fica a menos de 100 mm da ponta)".format(tipo, ab["nome"]))
        topo = float(ab.get("peitoril", 0)) + float(ab["altura"])
        if topo > casa["pe_direito"] - 100:
            erros.append(u"{0} {1}: topo a {2:.0f} mm, acima do pé-direito".format(tipo, ab["nome"], topo))
        faixa = (id(p), c - meia, c + meia)
        for outro_nome, f in ocupado:
            if f[0] == faixa[0] and faixa[1] < f[2] and f[1] < faixa[2]:
                erros.append(u"{0} {1}: sobrepõe {2} na mesma parede".format(tipo, ab["nome"], outro_nome))
        ocupado.append((ab["nome"], faixa))

    # móveis: dentro do ambiente, sem colisão entre si e fora do giro das portas
    pegadas = {}
    for i, m in enumerate(casa["moveis"]):
        rot_nome = u"{0} [{1}]".format(m["familia"], m["tipo"])
        dims = _dims_tipo(caminho_specs, m["familia"], m["tipo"])
        if dims is None:
            if "dim_mm" in m:
                dims = tuple(float(v) for v in m["dim_mm"])
                if not m.get("pendente"):
                    avisos.append(u"{0}: spec não encontrada, usando dim_mm".format(rot_nome))
            else:
                erros.append(u"{0}: spec/tipo não encontrado e sem dim_mm".format(rot_nome))
                continue
        try:
            r = pegada(m, dims)
        except ValueError as e:
            erros.append(u"{0}: {1}".format(rot_nome, e))
            continue
        pegadas[i] = r
        amb = ambientes.get(m["ambiente"])
        if amb is None:
            erros.append(u"{0}: ambiente '{1}' inexistente".format(rot_nome, m["ambiente"]))
            continue
        ri = retangulo_interno(casa, amb)
        if r[0] < ri[0] - TOL or r[1] < ri[1] - TOL or r[2] > ri[2] + TOL or r[3] > ri[3] + TOL:
            erros.append(u"{0}: sai do ambiente {1} (móvel {2}, livre {3})".format(
                rot_nome, amb["nome"], _fmt(r), _fmt(ri)))
        for porta in casa["portas"]:
            if _sobrepoe(r, area_porta(casa, porta)):
                avisos.append(u"{0}: invade o giro da porta {1}".format(rot_nome, porta["nome"]))
    idx = sorted(pegadas)
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            if _sobrepoe(pegadas[idx[a]], pegadas[idx[b]]):
                erros.append(u"Colisão: {0} x {1}".format(
                    casa["moveis"][idx[a]]["familia"], casa["moveis"][idx[b]]["familia"]))
    return erros, avisos, pegadas


def _fmt(r):
    return u"x {0:.0f}..{2:.0f}, y {1:.0f}..{3:.0f}".format(*r)
