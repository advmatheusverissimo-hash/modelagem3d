# Pesquisa — Blender vs Revit nativo e qual IA usar (out/2026)

## Blender → Revit
- O Revit importa malha OBJ/STL como forma 3D importada, inclusive dentro de famílias, mas sem parâmetros. [Autodesk – Import a 3D Shape](https://help.autodesk.com/cloudhelp/2026/ENU/RevitLT-Model/files/GUID-FDEC83AA-6C4A-4ECE-800A-3CA4724C63E4.htm)
- O Blender trabalha com superfícies e o Revit com sólidos e vazios: há perda de textura e de geometria. O caminho mais robusto é IFC via BlenderBIM/Bonsai, que mesmo assim não fica editável. [Autodesk Forum](https://forums.autodesk.com/t5/revit-architecture-forum/blender-file-to-revit/td-p/7620378)
- Objetos BIM com detalhe excessivo incham os projetos; o mercado (padrão NBS) exige consistência, nível de detalhe sensato e parâmetros. [AEC Magazine](https://aecmag.com/features/bim-libraries-2/)

## IA no Blender
- Teste Claude vs Codex no Blender (versões anteriores dos modelos): Codex melhor em objetos estruturados e arquitetônicos; Claude melhor em orgânicos. [DailyTopAI](https://dailytopai.com/article/claude-opus-48-vs-gpt-55-codex-in-blender-who-really-builds-better-3d-scenes-510.html)
- Ranking Design Arena 3D (out/2026): Claude Opus 5.5 em 1º, GPT-6 Astra em 2º, quase empatados. [modelgrep](https://modelgrep.com/best/3d)
- As duas IAs têm precisão dimensional fraca e topologia não profissional no Blender. [MindStudio](https://www.mindstudio.ai/blog/claude-blender-mcp-real-world-performance)

## IA gerando famílias nativas
- Fetch BIM: Claude criou gabinetes paramétricos (12+ parâmetros, famílias aninhadas) em cerca de 20 min; qualidade de "modelador júnior". [Fetch BIM](https://blog.fetchbim.com/i-onboarded-claude-as-a-revit-family-creator)
- ArchSmarter: foto → JSON → add-in → família (estática, sem parâmetros). [ArchSmarter](https://www.archsmarter.com/blog/claude-revit-family)
- ChatGPT + MCP do Revit gerou tudo como DirectShape, que não é editável. [BIMpure](https://www.bimpure.com/blog/revit-ai-tutorial-image-to-model-with-chatgpt-6-astra)

## Conclusão adotada
Nativo no Revit, gerado por script a partir de specs JSON. Blender só para partes orgânicas.
