# -*- coding: utf-8 -*-
"""Constrói a casa-teste no projeto Revit ativo e a mobilia com as famílias GSVL.

Fluxo: tipos de parede -> paredes -> portas/janelas -> piso -> separadores e
ambientes -> móveis (carrega os .rfa de output/rfa) -> conferência -> salvar.

IronPython 2.7: sem f-strings. Revit 2024+.
v0: escrito sem execução no Revit — corrigir conforme o log da primeira rodada.
"""
import math
import os

import clr
from System.Collections.Generic import List

from Autodesk.Revit.DB import (
    BuiltInCategory, BuiltInParameter, CompoundStructure, CurveArray, CurveLoop,
    ElementId, ElementTransformUtils, Family, FamilySymbol, FilteredElementCollector,
    Floor, FloorType, Level, Line, MaterialFunctionAssignment, Plane, SaveAsOptions,
    SketchPlane, UV, ViewPlan, Wall, WallKind, WallType, XYZ,
)
from Autodesk.Revit.DB.Structure import StructuralType

from gsvl_familias import casa as casamod
from gsvl_familias.falhas import ColetorFalhas, transacao
from gsvl_familias.util import config, mm, pasta, raiz_repo

PARAMS_LARGURA = (BuiltInParameter.DOOR_WIDTH, BuiltInParameter.WINDOW_WIDTH,
                  BuiltInParameter.FAMILY_WIDTH_PARAM)
PARAMS_ALTURA = (BuiltInParameter.DOOR_HEIGHT, BuiltInParameter.WINDOW_HEIGHT,
                 BuiltInParameter.FAMILY_HEIGHT_PARAM)
NOMES_LARGURA = (u"Largura", u"Width")
NOMES_ALTURA = (u"Altura", u"Height")


def _xyz(p, z=0.0):
    return XYZ(mm(p[0]), mm(p[1]), z)


class ConstrutorCasa(object):
    def __init__(self, doc, casa, log):
        self.doc = doc
        self.casa = casa
        self.log = log
        self.paredes = []      # (spec_parede, Wall)
        self.moveis = []       # (spec_movel, FamilyInstance)

    # ------------------------------------------------------------ utilidades
    def _etapa(self, nome, funcao):
        col = ColetorFalhas(self.log, u"[{0}] ".format(nome))
        t = transacao(self.doc, u"Casa teste: " + nome, col)
        t.Start()
        try:
            funcao()
            status = t.Commit()
            self.log.info(u"Etapa {0}: {1}".format(nome, status))
        except Exception as e:
            if t.HasStarted() and not t.HasEnded():
                t.RollBack()
            self.log.erro(u"Etapa {0}: {1}".format(nome, e))

    def _nivel(self):
        niveis = sorted(FilteredElementCollector(self.doc).OfClass(Level), key=lambda n: abs(n.Elevation))
        if not niveis:
            raise Exception(u"Projeto sem nível")
        self.nivel = niveis[0]
        self.planta = None
        for v in FilteredElementCollector(self.doc).OfClass(ViewPlan):
            if not v.IsTemplate and v.GenLevel is not None and v.GenLevel.Id == self.nivel.Id:
                self.planta = v
                break
        self.log.info(u"Nível: {0} | planta: {1}".format(
            self.nivel.Name, self.planta.Name if self.planta else u"(não encontrada)"))

    # ---------------------------------------------------------------- paredes
    def _tipo_parede(self, nome, esp_mm):
        for wt in FilteredElementCollector(self.doc).OfClass(WallType):
            if wt.Kind == WallKind.Basic and wt.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == nome:
                return wt
        base = None
        for wt in FilteredElementCollector(self.doc).OfClass(WallType):
            if wt.Kind == WallKind.Basic and wt.GetCompoundStructure() is not None:
                base = wt
                break
        if base is None:
            raise Exception(u"Nenhum tipo de parede básica no template")
        novo = base.Duplicate(nome)
        cs = CompoundStructure.CreateSingleLayerCompoundStructure(
            MaterialFunctionAssignment.Structure, mm(esp_mm), ElementId.InvalidElementId)
        novo.SetCompoundStructure(cs)
        self.log.info(u"Tipo de parede criado: {0} ({1} mm)".format(nome, esp_mm))
        return novo

    def criar_paredes(self):
        tipos = {}
        for chave, t in self.casa["paredes_tipos"].items():
            tipos[chave] = self._tipo_parede(t["nome"], t["espessura"])
        altura = mm(self.casa["pe_direito"])
        for p in self.casa["paredes"]:
            linha = Line.CreateBound(_xyz(p["de"]), _xyz(p["ate"]))
            w = Wall.Create(self.doc, linha, tipos[p["tipo"]].Id, self.nivel.Id, altura, 0.0, False, False)
            self.paredes.append((p, w))
        self.log.info(u"{0} paredes criadas".format(len(self.paredes)))

    def _parede_revit(self, ponto):
        alvo = casamod.parede_em(self.casa, ponto)
        for p, w in self.paredes:
            if p is alvo:
                return w
        return None

    # ---------------------------------------------------------------- aberturas
    def _definir(self, elem, bips, nomes, valor_mm):
        for bip in bips:
            par = elem.get_Parameter(bip)
            if par is not None and not par.IsReadOnly:
                par.Set(mm(valor_mm))
                return True
        for n in nomes:
            par = elem.LookupParameter(n)
            if par is not None and not par.IsReadOnly:
                par.Set(mm(valor_mm))
                return True
        return False

    def _simbolo(self, categoria, largura, altura):
        simbolos = list(FilteredElementCollector(self.doc).OfCategory(categoria).OfClass(FamilySymbol))
        if not simbolos:
            raise Exception(u"Nenhuma família de {0} carregada no projeto".format(categoria))
        nome = u"GSVL {0:.0f}x{1:.0f}".format(largura, altura)
        for s in simbolos:
            if s.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == nome:
                return s
        base = simbolos[0]
        novo = base.Duplicate(nome)
        ok_l = self._definir(novo, PARAMS_LARGURA, NOMES_LARGURA, largura)
        ok_a = self._definir(novo, PARAMS_ALTURA, NOMES_ALTURA, altura)
        if not (ok_l and ok_a):
            self.log.aviso(u"Tipo {0} ({1}): não consegui definir {2}".format(
                nome, base.Family.Name, u"largura" if not ok_l else u"altura"))
        self.log.info(u"Tipo criado: {0} : {1}".format(base.Family.Name, nome))
        return novo

    def criar_aberturas(self):
        grupos = ((BuiltInCategory.OST_Doors, self.casa["portas"]),
                  (BuiltInCategory.OST_Windows, self.casa["janelas"]))
        for categoria, lista in grupos:
            for ab in lista:
                try:
                    host = self._parede_revit(ab["em"])
                    if host is None:
                        raise Exception(u"parede não encontrada no ponto {0}".format(ab["em"]))
                    sim = self._simbolo(categoria, ab["largura"], ab["altura"])
                    if not sim.IsActive:
                        sim.Activate()
                        self.doc.Regenerate()
                    inst = self.doc.Create.NewFamilyInstance(
                        _xyz(ab["em"]), sim, host, self.nivel, StructuralType.NonStructural)
                    if "peitoril" in ab:
                        inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).Set(mm(ab["peitoril"]))
                    if ab.get("inverter"):
                        inst.flipFacing()
                    if ab.get("espelhar"):
                        inst.flipHand()
                    marca = inst.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
                    if marca is not None:
                        marca.Set(ab["nome"].split(u" ")[0])
                except Exception as e:
                    self.log.erro(u"Abertura {0}: {1}".format(ab["nome"], e))
        self.log.info(u"Aberturas processadas")

    # ------------------------------------------------------------------- piso
    def criar_piso(self):
        xs = [v for p in self.casa["paredes"] for v in (p["de"][0], p["ate"][0])]
        ys = [v for p in self.casa["paredes"] for v in (p["de"][1], p["ate"][1])]
        meia = self.casa["paredes_tipos"]["externa"]["espessura"] / 2.0
        x0, x1, y0, y1 = min(xs) - meia, max(xs) + meia, min(ys) - meia, max(ys) + meia
        pts = [_xyz((x0, y0)), _xyz((x1, y0)), _xyz((x1, y1)), _xyz((x0, y1))]
        laco = CurveLoop()
        for i in range(4):
            laco.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
        tipo = None
        for ft in FilteredElementCollector(self.doc).OfClass(FloorType):
            if not ft.IsFoundationSlab:
                tipo = ft
                break
        lacos = List[CurveLoop]()
        lacos.Add(laco)
        Floor.Create(self.doc, lacos, tipo.Id, self.nivel.Id)
        self.log.info(u"Piso criado ({0})".format(tipo.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()))

    # --------------------------------------------------------------- ambientes
    def criar_ambientes(self):
        seps = self.casa.get("separadores", [])
        if seps:
            if self.planta is None:
                raise Exception(u"sem vista de planta para os separadores")
            arr = CurveArray()
            for s in seps:
                arr.Append(Line.CreateBound(_xyz(s["de"]), _xyz(s["ate"])))
            sp = SketchPlane.Create(self.doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, self.nivel.Elevation)))
            self.doc.Create.NewRoomBoundaryLines(sp, arr, self.planta)
            self.doc.Regenerate()
        self.ambientes = {}
        for i, a in enumerate(self.casa["ambientes"]):
            r = casamod.retangulo_interno(self.casa, a)
            uv = UV(mm((r[0] + r[2]) / 2.0), mm((r[1] + r[3]) / 2.0))
            room = self.doc.Create.NewRoom(self.nivel, uv)
            room.Name = a["nome"]
            room.Number = str(i + 1)
            self.ambientes[a["nome"]] = room
        self.log.info(u"{0} ambientes criados".format(len(self.ambientes)))

    # ------------------------------------------------------------------ móveis
    def _familia(self, nome):
        for f in FilteredElementCollector(self.doc).OfClass(Family):
            if f.Name == nome:
                return f
        caminho = os.path.join(raiz_repo(), config()["saida_rfa"], nome + u".rfa")
        if not os.path.exists(caminho):
            return None
        ref = clr.Reference[Family]()
        self.doc.LoadFamily(caminho, ref)
        return ref.Value

    def _tipo_familia(self, fam, nome_tipo):
        for sid in fam.GetFamilySymbolIds():
            s = self.doc.GetElement(sid)
            if s.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == nome_tipo:
                return s
        return None

    def criar_moveis(self):
        for m in self.casa["moveis"]:
            rotulo = u"{0} [{1}]".format(m["familia"], m["tipo"])
            if m.get("pendente"):
                self.log.info(u"Móvel pendente (família ainda não existe): " + rotulo)
                continue
            try:
                fam = self._familia(m["familia"])
                if fam is None:
                    self.log.aviso(u"Móvel {0}: .rfa não encontrado em output/rfa — gere a família antes".format(rotulo))
                    continue
                sim = self._tipo_familia(fam, m["tipo"])
                if sim is None:
                    self.log.erro(u"Móvel {0}: tipo não existe na família".format(rotulo))
                    continue
                if not sim.IsActive:
                    sim.Activate()
                    self.doc.Regenerate()
                pt = _xyz(m["em"], self.nivel.Elevation)
                inst = self.doc.Create.NewFamilyInstance(pt, sim, self.nivel, StructuralType.NonStructural)
                rot = int(m.get("rot", 0)) % 360
                if rot:
                    eixo = Line.CreateBound(pt, pt + XYZ.BasisZ)
                    ElementTransformUtils.RotateElement(self.doc, inst.Id, eixo, math.radians(rot))
                self.moveis.append((m, inst))
            except Exception as e:
                self.log.erro(u"Móvel {0}: {1}".format(rotulo, e))
        self.log.info(u"{0} móveis inseridos".format(len(self.moveis)))

    # -------------------------------------------------------------- conferência
    def conferir(self):
        """Compara a caixa envolvente real de cada móvel com a pegada esperada e com o cômodo."""
        caminho_specs = os.path.join(raiz_repo(), "specs")
        z = self.nivel.Elevation + mm(300)
        for m, inst in self.moveis:
            rotulo = u"{0} [{1}]".format(m["familia"], m["tipo"])
            bb = inst.get_BoundingBox(None)
            if bb is None:
                self.log.erro(u"Conferência {0}: sem caixa envolvente".format(rotulo))
                continue
            real = (bb.Min.X * 304.8, bb.Min.Y * 304.8, bb.Max.X * 304.8, bb.Max.Y * 304.8)
            dims = casamod._dims_tipo(caminho_specs, m["familia"], m["tipo"])
            if dims is not None:
                esp = casamod.pegada(m, dims)
                # puxadores e afins podem sobressair; tolerância de 60 mm por lado
                desvio = max(abs(real[i] - esp[i]) for i in range(4))
                (self.log.aviso if desvio > 60 else self.log.info)(
                    u"Conferência {0}: pegada real {1} | esperada {2} | desvio máx {3:.0f} mm".format(
                        rotulo, casamod._fmt(real), casamod._fmt(esp), desvio))
            room = self.ambientes.get(m["ambiente"]) if hasattr(self, "ambientes") else None
            if room is not None:
                fora = [c for c in ((real[0] + 5, real[1] + 5), (real[2] - 5, real[1] + 5),
                                    (real[2] - 5, real[3] - 5), (real[0] + 5, real[3] - 5))
                        if not room.IsPointInRoom(XYZ(mm(c[0]), mm(c[1]), z))]
                if fora:
                    self.log.aviso(u"Conferência {0}: {1} canto(s) fora do ambiente {2}".format(
                        rotulo, len(fora), m["ambiente"]))

    # ---------------------------------------------------------------- execução
    def executar(self):
        self._nivel()
        self._etapa(u"paredes", self.criar_paredes)
        self._etapa(u"aberturas", self.criar_aberturas)
        self._etapa(u"piso", self.criar_piso)
        self._etapa(u"ambientes", self.criar_ambientes)
        self._etapa(u"móveis", self.criar_moveis)
        self.conferir()


def construir(doc, caminho_casa, log):
    """Constrói a casa no documento ativo e salva em output/casa. Devolve o caminho salvo."""
    if doc.IsFamilyDocument:
        log.erro(u"Abra um PROJETO novo (não uma família) antes de rodar")
        return None
    for wt in FilteredElementCollector(doc).OfClass(WallType):
        nome = wt.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or u""
        if nome.startswith(u"GSVL") and list(FilteredElementCollector(doc).OfClass(Wall)):
            log.erro(u"Este projeto já tem a casa-teste. Abra um projeto novo para gerar de novo")
            return None
    casa = casamod.carregar(caminho_casa)
    erros, _avisos, _peg = casamod.validar(casa, os.path.join(raiz_repo(), "specs"))
    if erros:
        for e in erros:
            log.erro(u"Casa: " + e)
        return None
    c = ConstrutorCasa(doc, casa, log)
    c.executar()
    destino = os.path.join(pasta(u"output/casa"), casa["nome_arquivo"] + u".rvt")
    try:
        opts = SaveAsOptions()
        opts.OverwriteExistingFile = True
        doc.SaveAs(destino, opts)
        log.info(u"Salvo: " + destino)
    except Exception as e:
        log.aviso(u"Não salvei automaticamente ({0}). Salve manualmente em {1}".format(e, destino))
    return destino
