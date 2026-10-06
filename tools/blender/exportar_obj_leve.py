# -*- coding: utf-8 -*-
"""Exporta o objeto selecionado no Blender como OBJ leve para família híbrida do Revit.

Uso (Blender 4.x): Scripting > abrir este arquivo > selecionar o objeto > Run Script.
- Aplica escala/rotação, reduz para no máximo MAX_FACES faces e exporta em milímetros.
- A origem do objeto deve estar no ponto de inserção da família (centro, no piso).
"""
import os

import bpy

MAX_FACES = 5000
PASTA_SAIDA = os.path.join(os.path.dirname(bpy.data.filepath) or os.path.expanduser("~"), "obj_revit")

obj = bpy.context.active_object
if obj is None or obj.type != "MESH":
    raise RuntimeError("Selecione um objeto de malha")

bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

faces = len(obj.data.polygons)
if faces > MAX_FACES:
    mod = obj.modifiers.new("Decimate_Revit", "DECIMATE")
    mod.ratio = MAX_FACES / float(faces)
    bpy.ops.object.modifier_apply(modifier=mod.name)

os.makedirs(PASTA_SAIDA, exist_ok=True)
destino = os.path.join(PASTA_SAIDA, obj.name + ".obj")
# Blender trabalha em metros; global_scale=1000 converte para mm.
bpy.ops.wm.obj_export(filepath=destino, export_selected_objects=True, global_scale=1000.0,
                      export_materials=False, forward_axis="Y", up_axis="Z")
print("Exportado: {0} ({1} faces)".format(destino, len(obj.data.polygons)))
