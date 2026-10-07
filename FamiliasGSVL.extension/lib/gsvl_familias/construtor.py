# -*- coding: utf-8 -*-
"""Constrói uma família Revit a partir de uma spec JSON.

Fluxo: parâmetros -> planos de referência -> cotas (EQ e rotuladas)
-> caixas (extrusões alinhadas e travadas) -> fórmulas -> tipos -> identificação -> salvar.

IronPython 2.7: sem f-strings. Revit 2024+ (ForgeTypeId).
v0: escrito sem execução no Revit — corrigir conforme o log da primeira rodada.
"""
import os
import unicodedata

from Autodesk.Revit.DB import (
    BuiltInParameter, CurveArray, CurveArrArray, FamilyElementVisibility,
    FamilyElementVisibilityType, FamilyInstanceReferenceType, FilteredElementCollector,
    GroupTypeId, Level, Line, Options, Plane, PlanarFace, ReferenceArray, ReferencePlane,
    SaveAsOptions, SketchPlane, Solid, SpecTypeId, View, View3D, ViewPlan, ViewType, XYZ,
)

from gsvl_familias import spec as specmod
from gsvl_familias.falhas import ColetorFalhas, transacao
from gsvl_familias.util import config, mm, pasta

TOL = 1e-6


def _sem_acento(s):
    s = unicodedata.normalize("NFKD", s)
    return u"".join(c for c in s if not unicodedata.combining(c)).lower()


# palavras-chave por categoria, usadas quando nenhum nome exato da spec existe na máquina
CHAVES_CATEGORIA = {
    u"mobiliario": ([u"mobili", u"furniture"], [u"sistema", u"system"]),
    u"janelas": ([u"janela", u"window"], [u"cortina", u"curtain"]),
}


def encontrar_template(templates_dir, nomes, categoria=u"", log=None):
    """Acha o .rft pelo nome exato; se não houver, por palavra-chave da categoria."""
    alvo = set(_sem_acento(n) for n in nomes)
    todos = []
    for raiz, _dirs, arquivos in os.walk(templates_dir):
        for a in arquivos:
            if not a.lower().endswith(".rft"):
                continue
            if _sem_acento(a) in alvo:
                return os.path.join(raiz, a)
            todos.append(os.path.join(raiz, a))
    incluir, excluir = CHAVES_CATEGORIA.get(_sem_acento(categoria), ([], []))
    candidatos = [c for c in todos
                  if any(k in _sem_acento(os.path.basename(c)) for k in incluir)
                  and not any(k in _sem_acento(os.path.basename(c)) for k in excluir)]
    if candidatos:
        # prefere métrico e o nome mais curto (o template "puro" da categoria)
        candidatos.sort(key=lambda c: (u"metric" not in _sem_acento(c), len(os.path.basename(c))))
        if log is not None:
            log.aviso(u"Template exato não encontrado; usando {0} (candidatos: {1})".format(
                candidatos[0], u", ".join(os.path.basename(c) for c in candidatos[:6])))
        return candidatos[0]
    raise IOError(u"Template não encontrado em {0}: {1} ({2} .rft na pasta)".format(
        templates_dir, u", ".join(nomes), len(todos)))


class Construtor(object):
    def __init__(self, doc, spec, log):
        self.doc = doc
        self.spec = spec
        self.log = log
        self.fm = doc.FamilyManager
        self.fc = doc.FamilyCreate
        self.refs = {}       # nome -> (eixo, pos_pes, Reference)
        self.fparams = {}    # nome -> FamilyParameter
        padrao = specmod.valores_padrao(spec)
        self.pos_mm = specmod.posicoes_planos(spec, padrao)
        maior = max([abs(v[1]) for v in self.pos_mm.values()] + [500.0])
        self.extensao = mm(maior + 300)   # meio-comprimento dos planos desenhados
        self.offset_cota = mm(maior + 150)

    # ---------------------------------------------------------------- vistas
    def _vistas(self):
        self.planta = None
        self.frente = None
        self.vista3d = None
        for v in FilteredElementCollector(self.doc).OfClass(View):
            if v.IsTemplate:
                continue
            if v.ViewType == ViewType.FloorPlan and self.planta is None:
                self.planta = v
            elif v.ViewType == ViewType.Elevation and v.ViewDirection.Y < -0.9:
                self.frente = v
            elif v.ViewType == ViewType.ThreeD and self.vista3d is None:
                self.vista3d = v
        if self.planta is None or self.frente is None:
            raise Exception(u"Vista de planta ou elevação Frontal não encontrada no template")
        self.log.info(u"Vistas: planta={0}, frente={1}".format(self.planta.Name, self.frente.Name))

    # ------------------------------------------------------------ parâmetros
    def _tipo_forge(self, tipo):
        if tipo == "comprimento":
            return SpecTypeId.Length, GroupTypeId.Geometry
        if tipo == "simnao":
            return SpecTypeId.Boolean.YesNo, GroupTypeId.Visibility
        if tipo == "material":
            return SpecTypeId.Reference.Material, GroupTypeId.Materials
        return SpecTypeId.String.Text, GroupTypeId.IdentityData

    def _add_param(self, nome, tipo, instancia):
        existente = self.fm.get_Parameter(nome)
        if existente is not None:
            return existente
        spec_t, grupo = self._tipo_forge(tipo)
        return self.fm.AddParameter(nome, grupo, spec_t, instancia)

    def parametros(self):
        tipos = self.spec["tipos"]
        if self.fm.Types.Size == 0:
            self.fm.NewType(tipos[0]["nome"])
        else:
            self.fm.RenameCurrentType(tipos[0]["nome"])
        for p in self.spec["parametros"]:
            fp = self._add_param(p["nome"], p["tipo"], bool(p.get("instancia", False)))
            self.fparams[p["nome"]] = fp
            if p["tipo"] == "comprimento":
                self.fm.Set(fp, mm(p["padrao"]))
            elif p["tipo"] == "simnao":
                self.fm.Set(fp, int(p.get("padrao", 1)))
        for nome in ("IfcExportAs", "Versao_Familia"):
            self.fparams[nome] = self._add_param(nome, "texto", False)
        self.log.info(u"{0} parâmetros criados".format(len(self.fparams)))

    # ------------------------------------------------------- planos/referências
    def _especiais(self):
        for rp in FilteredElementCollector(self.doc).OfClass(ReferencePlane):
            n = rp.Normal
            if abs(n.X) > 0.99 and abs(rp.BubbleEnd.X) < TOL:
                self.refs["@centro_x"] = ("x", 0.0, rp.GetReference())
            elif abs(n.Y) > 0.99 and abs(rp.BubbleEnd.Y) < TOL:
                self.refs["@centro_y"] = ("y", 0.0, rp.GetReference())
        nivel = FilteredElementCollector(self.doc).OfClass(Level).FirstElement()
        if nivel is not None:
            self.refs["@nivel"] = ("z", nivel.Elevation, nivel.GetPlaneReference())
        for k in ("@centro_x", "@centro_y", "@nivel"):
            if k not in self.refs:
                self.log.erro(u"Referência especial {0} não encontrada no template".format(k))

    def planos(self):
        self._especiais()
        L = self.extensao
        for pl in self.spec["planos"]:
            eixo, pos = pl["eixo"], mm(self.pos_mm[pl["nome"]][1])
            if eixo == "x":
                rp = self.fc.NewReferencePlane(XYZ(pos, -L, 0), XYZ(pos, L, 0), XYZ.BasisZ, self.planta)
            elif eixo == "y":
                rp = self.fc.NewReferencePlane(XYZ(-L, pos, 0), XYZ(L, pos, 0), XYZ.BasisZ, self.planta)
            else:
                rp = self.fc.NewReferencePlane(XYZ(-L, 0, pos), XYZ(L, 0, pos), XYZ.BasisY, self.frente)
            rp.Name = pl["nome"]
            ref_tipo = pl.get("referencia", "WeakReference")
            try:
                rp.get_Parameter(BuiltInParameter.ELEM_REFERENCE_NAME).Set(
                    int(getattr(FamilyInstanceReferenceType, ref_tipo)))
            except Exception as e:
                self.log.aviso(u"Plano {0}: não foi possível definir referência {1} ({2})".format(pl["nome"], ref_tipo, e))
            self.refs[pl["nome"]] = (eixo, pos, rp.GetReference())
        self.log.info(u"{0} planos criados".format(len(self.spec["planos"])))

    # ------------------------------------------------------------------ cotas
    def cotas(self):
        for i, c in enumerate(self.spec["cotas"]):
            nomes = c["planos"]
            try:
                eixo = self.refs[nomes[0]][0]
                posicoes = [self.refs[n][1] for n in nomes]
                ra = ReferenceArray()
                for n in nomes:
                    ra.Append(self.refs[n][2])
                off = self.offset_cota + mm(120) * (i % 6)
                a, b = min(posicoes), max(posicoes)
                if eixo == "x":
                    linha, vista = Line.CreateBound(XYZ(a, -off, 0), XYZ(b, -off, 0)), self.planta
                elif eixo == "y":
                    linha, vista = Line.CreateBound(XYZ(-off, a, 0), XYZ(-off, b, 0)), self.planta
                else:
                    linha, vista = Line.CreateBound(XYZ(-off, 0, a), XYZ(-off, 0, b)), self.frente
                dim = self.fc.NewLinearDimension(vista, linha, ra)
                if c.get("eq"):
                    dim.AreSegmentsEqual = True
                else:
                    dim.FamilyLabel = self.fparams[c["rotulo"]]
            except Exception as e:
                self.log.erro(u"Cota {0} {1}: {2}".format(i, nomes, e))
        self.log.info(u"Cotas processadas")

    # ----------------------------------------------------------------- caixas
    def _subcategoria(self, nome):
        cat = self.doc.OwnerFamily.FamilyCategory
        for sub in cat.SubCategories:
            if sub.Name == nome:
                return sub
        return self.doc.Settings.Categories.NewSubcategory(cat, nome)

    def _faces(self, elem):
        opt = Options()
        opt.ComputeReferences = True
        for g in elem.get_Geometry(opt):
            if isinstance(g, Solid):
                for f in g.Faces:
                    if isinstance(f, PlanarFace):
                        yield f

    def _alinhar(self, ext, cx):
        travados = 0
        for f in list(self._faces(ext)):   # lista antes de alterar a geometria
            n = f.FaceNormal
            for eixo, comp, vista in (("x", n.X, self.planta), ("y", n.Y, self.planta), ("z", n.Z, self.frente)):
                if abs(comp) < 0.99:
                    continue
                nome_plano = cx[eixo][0] if comp < 0 else cx[eixo][1]
                try:
                    al = self.fc.NewAlignment(vista, self.refs[nome_plano][2], f.Reference)
                    al.IsLocked = True
                    travados += 1
                except Exception as e:
                    self.log.erro(u"Caixa {0}: falha ao travar face {1}{2} em {3}: {4}".format(
                        cx["nome"], "-" if comp < 0 else "+", eixo, nome_plano, e))
        if travados != 6:
            self.log.aviso(u"Caixa {0}: {1}/6 faces travadas".format(cx["nome"], travados))

    def caixas(self):
        for cx in self.spec["caixas"]:
            try:
                x0, x1 = [self.refs[n][1] for n in cx["x"]]
                y0, y1 = [self.refs[n][1] for n in cx["y"]]
                z0, z1 = [self.refs[n][1] for n in cx["z"]]
                pts = [XYZ(x0, y0, z0), XYZ(x1, y0, z0), XYZ(x1, y1, z0), XYZ(x0, y1, z0)]
                perfil = CurveArray()
                for i in range(4):
                    perfil.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
                arr = CurveArrArray()
                arr.Append(perfil)
                sp = SketchPlane.Create(self.doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, z0)))
                ext = self.fc.NewExtrusion(True, arr, sp, z1 - z0)
                self.doc.Regenerate()

                if "subcategoria" in cx:
                    ext.Subcategory = self._subcategoria(cx["subcategoria"])
                det = cx.get("detalhe", ["coarse", "medium", "fine"])
                vis = FamilyElementVisibility(FamilyElementVisibilityType.Model)
                vis.IsShownInCoarse = "coarse" in det
                vis.IsShownInMedium = "medium" in det
                vis.IsShownInFine = "fine" in det
                ext.SetVisibility(vis)
                if "material" in cx:
                    self.fm.AssociateElementParameterToFamilyParameter(
                        ext.get_Parameter(BuiltInParameter.MATERIAL_ID_PARAM), self.fparams[cx["material"]])
                if "visivel" in cx:
                    self.fm.AssociateElementParameterToFamilyParameter(
                        ext.get_Parameter(BuiltInParameter.IS_VISIBLE_PARAM), self.fparams[cx["visivel"]])

                self._alinhar(ext, cx)
                self.log.info(u"Caixa {0} criada (id {1})".format(cx["nome"], ext.Id))
            except Exception as e:
                self.log.erro(u"Caixa {0}: {1}".format(cx["nome"], e))

    # ------------------------------------------------------ fórmulas e tipos
    def formulas(self):
        for p in self.spec["parametros"]:
            if p.get("formula"):
                try:
                    self.fm.SetFormula(self.fparams[p["nome"]], p["formula"])
                except Exception as e:
                    self.log.erro(u"Fórmula {0}: {1}".format(p["nome"], e))

    def _identificacao_tipo(self):
        idt = self.spec.get("identificacao", {})
        marca = config().get("marca", {})
        textos = (
            (BuiltInParameter.ALL_MODEL_MANUFACTURER, marca.get("fabricante")),
            (BuiltInParameter.ALL_MODEL_MODEL, idt.get("modelo")),
            (BuiltInParameter.ALL_MODEL_DESCRIPTION, idt.get("descricao")),
            (BuiltInParameter.ALL_MODEL_URL, marca.get("url")),
            (BuiltInParameter.UNIFORMAT_CODE, idt.get("codigo_montagem")),
        )
        for bip, valor in textos:
            if not valor:
                continue
            try:
                fp = self.fm.get_Parameter(bip)
                if fp is not None:
                    self.fm.Set(fp, valor)
            except Exception as e:
                self.log.aviso(u"Identificação {0}: {1}".format(bip, e))
        if idt.get("ifc_export_as"):
            self.fm.Set(self.fparams["IfcExportAs"], idt["ifc_export_as"])
        if idt.get("versao_familia"):
            self.fm.Set(self.fparams["Versao_Familia"], idt["versao_familia"])

    def tipos(self):
        padrao = specmod.valores_padrao(self.spec)
        existentes = dict((t.Name, t) for t in self.fm.Types)
        for t in self.spec["tipos"]:
            if t["nome"] in existentes:
                self.fm.CurrentType = existentes[t["nome"]]
            else:
                self.fm.NewType(t["nome"])
            valores = dict(padrao)
            valores.update(t["valores"])
            for nome, v in valores.items():
                p = [x for x in self.spec["parametros"] if x["nome"] == nome][0]
                if p.get("formula"):
                    continue
                if p["tipo"] == "comprimento":
                    self.fm.Set(self.fparams[nome], mm(v))
                elif p["tipo"] == "simnao":
                    self.fm.Set(self.fparams[nome], int(v))
            self._identificacao_tipo()
        omni = self.spec.get("identificacao", {}).get("omniclass")
        if omni:
            try:
                self.doc.OwnerFamily.get_Parameter(BuiltInParameter.OMNICLASS_CODE).Set(omni)
            except Exception as e:
                self.log.aviso(u"OmniClass: {0}".format(e))
        self.log.info(u"{0} tipos configurados".format(len(self.spec["tipos"])))

    # -------------------------------------------------------------- execução
    def executar(self):
        self._vistas()
        self.parametros()
        self.planos()
        self.doc.Regenerate()
        self.cotas()
        self.doc.Regenerate()
        self.caixas()
        self.formulas()
        self.tipos()
        self.doc.Regenerate()


def gerar(app, caminho_spec, log):
    """Gera o .rfa e devolve o caminho salvo (ou None se falhar)."""
    cfg = config()
    sp = specmod.carregar(caminho_spec)
    erros = specmod.validar(sp)
    if erros:
        for e in erros:
            log.erro(u"Spec: " + e)
        return None

    template = encontrar_template(cfg["templates_dir"], sp["templates"], sp.get("categoria", u""), log)
    log.info(u"Template: " + template)
    doc = app.NewFamilyDocument(template)

    coletor = ColetorFalhas(log, u"Revit: ")
    t = transacao(doc, u"Gerar família", coletor)
    t.Start()
    try:
        c = Construtor(doc, sp, log)
        c.executar()
        status = t.Commit()
        log.info(u"Transação: {0}".format(status))
    except Exception as e:
        log.erro(u"Falha geral: {0}".format(e))
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        doc.Close(False)
        return None

    destino = os.path.join(pasta(cfg["saida_rfa"]), sp["nome_arquivo"] + ".rfa")
    opts = SaveAsOptions()
    opts.OverwriteExistingFile = True
    if getattr(c, "vista3d", None) is not None:
        opts.PreviewViewId = c.vista3d.Id
    doc.SaveAs(destino, opts)
    doc.Close(False)
    kb = os.path.getsize(destino) / 1024.0
    log.info(u"Salvo: {0} ({1:.0f} KB)".format(destino, kb))
    return destino
