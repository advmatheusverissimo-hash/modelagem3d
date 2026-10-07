# -*- coding: utf-8 -*-
"""Valida a casa-teste fora do Revit e desenha a planta em SVG.

Uso: python tools/validar_casa.py [casa/casa_teste.json] [--svg saida.svg]
Checa aberturas (na parede, sem sobreposição, abaixo do pé-direito) e móveis
(dentro do ambiente, sem colisão entre si, fora do giro das portas).
Dimensões dos móveis vêm das specs; móveis "pendentes" usam dim_mm.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "FamiliasGSVL.extension", "lib"))
from gsvl_familias import casa as casamod  # noqa: E402  (módulo puro, sem API do Revit)

CORES = {"externa": "#2b2b2b", "interna": "#555555"}


def svg(casa, pegadas, destino):
    xs = [v for p in casa["paredes"] for v in (p["de"][0], p["ate"][0])]
    ys = [v for p in casa["paredes"] for v in (p["de"][1], p["ate"][1])]
    m = 1200
    x0, x1, y0, y1 = min(xs) - m, max(xs) + m, min(ys) - m, max(ys) + m
    W, H = x1 - x0, y1 - y0
    ty = lambda y: y1 - y + y0  # noqa: E731  (y para cima, como na planta)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="{0} {1} {2} {3}" width="1000" height="{4:.0f}" '
         'font-family="Arial" >'.format(x0, y0, W, H, 1000.0 * H / W),
         '<rect x="{0}" y="{1}" width="{2}" height="{3}" fill="#ffffff"/>'.format(x0, y0, W, H)]
    for a in casa["ambientes"]:
        r = casamod.retangulo_interno(casa, a)
        o.append('<rect x="{0}" y="{1}" width="{2}" height="{3}" fill="#f4efe6"/>'.format(
            r[0], ty(r[3]), r[2] - r[0], r[3] - r[1]))
        ex = a["eixos"]
        area = (r[2] - r[0]) * (r[3] - r[1]) / 1e6
        o.append('<text x="{0}" y="{1}" font-size="200" text-anchor="middle" fill="#7a6a55">{2}</text>'.format(
            (ex[0] + ex[2]) / 2.0, ty(ex[1] + 450), a["nome"]))
        o.append('<text x="{0}" y="{1}" font-size="160" text-anchor="middle" fill="#7a6a55">{2:.1f} m²</text>'.format(
            (ex[0] + ex[2]) / 2.0, ty(ex[1] + 220), area))
    for p in casa["paredes"]:
        e = casamod._esp(casa, p)
        (a0, b0), (a1, b1) = p["de"], p["ate"]
        o.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{3}" stroke="{4}" stroke-width="{5}" stroke-linecap="square"/>'.format(
            a0, ty(b0), a1, ty(b1), CORES[p["tipo"]], e))
    for sep in casa.get("separadores", []):
        (a0, b0), (a1, b1) = sep["de"], sep["ate"]
        o.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{3}" stroke="#999" stroke-width="20" stroke-dasharray="100,60"/>'.format(
            a0, ty(b0), a1, ty(b1)))
    for tipo, lista, cor in (("porta", casa["portas"], "#c0392b"), ("janela", casa["janelas"], "#2e86c1")):
        for ab in lista:
            p = casamod.parede_em(casa, ab["em"])
            if p is None:
                continue
            e = casamod._esp(casa, p) + 4
            x, y = ab["em"]
            w = ab["largura"]
            if casamod._vertical(p):
                rx, ry, rw, rh = x - e / 2.0, y - w / 2.0, e, w
            else:
                rx, ry, rw, rh = x - w / 2.0, y - e / 2.0, w, e
            o.append('<rect x="{0}" y="{1}" width="{2}" height="{3}" fill="#ffffff" stroke="{4}" stroke-width="25"/>'.format(
                rx, ty(ry + rh), rw, rh, cor))
            if tipo == "porta":
                r = casamod.area_porta(casa, ab)
                o.append('<rect x="{0}" y="{1}" width="{2}" height="{3}" fill="none" stroke="{4}" '
                         'stroke-width="12" stroke-dasharray="60,60"/>'.format(r[0], ty(r[3]), r[2] - r[0], r[3] - r[1], cor))
    for i, r in pegadas.items():
        mv = casa["moveis"][i]
        pend = mv.get("pendente")
        o.append('<rect x="{0}" y="{1}" width="{2}" height="{3}" fill="{4}" fill-opacity="0.55" stroke="#1e5631" '
                 'stroke-width="20" {5}/>'.format(r[0], ty(r[3]), r[2] - r[0], r[3] - r[1],
                                                 "#cfcfcf" if pend else "#7dcea0",
                                                 'stroke-dasharray="80,50"' if pend else ""))
        # marca da frente do móvel
        rot = int(mv.get("rot", 0)) % 360
        cx, cy = (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0
        fx, fy = {0: (cx, r[1]), 90: (r[2], cy), 180: (cx, r[3]), 270: (r[0], cy)}[rot]
        o.append('<circle cx="{0}" cy="{1}" r="45" fill="#1e5631"/>'.format(fx, ty(fy)))
        rotulo = mv["tipo"].split(" (")[0]
        o.append('<text x="{0}" y="{1}" font-size="120" text-anchor="middle" fill="#1e3d2a">{2}</text>'.format(
            cx, ty(cy) + 40, rotulo))
    o.append('<text x="{0}" y="{1}" font-size="170" fill="#333">{2} — eixos em mm · verde = família GSVL · '
             'cinza tracejado = família pendente · ● = frente do móvel · tracejado vermelho = giro de porta</text>'.format(
                 x0 + 150, y0 + 300, casa["nome_arquivo"]))
    o.append("</svg>")
    with open(destino, "w", encoding="utf-8") as f:
        f.write("\n".join(o))


def main(args):
    destino_svg = None
    if "--svg" in args:
        i = args.index("--svg")
        destino_svg = args[i + 1]
        args = args[:i] + args[i + 2:]
    caminho = args[0] if args else os.path.join(RAIZ, "casa", "casa_teste.json")
    casa = casamod.carregar(caminho)
    erros, avisos, pegadas = casamod.validar(casa, os.path.join(RAIZ, "specs"))
    for e in erros:
        print("ERRO   " + e)
    for a in avisos:
        print("AVISO  " + a)
    pend = sum(1 for m in casa["moveis"] if m.get("pendente"))
    print("{0}: {1} paredes, {2} portas, {3} janelas, {4} ambientes, {5} móveis ({6} pendentes) -> {7}".format(
        os.path.basename(caminho), len(casa["paredes"]), len(casa["portas"]), len(casa["janelas"]),
        len(casa["ambientes"]), len(casa["moveis"]), pend, "REPROVADA" if erros else "OK"))
    if destino_svg:
        svg(casa, pegadas, destino_svg)
        print("Planta: " + destino_svg)
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
