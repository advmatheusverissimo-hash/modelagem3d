# Famílias Revit — biblioteca paramétrica para venda

Gerador de famílias Revit (.rfa) **nativas e paramétricas** (janelas, mesas, escrivaninhas, camas…) para venda a arquitetos e engenheiros.

Cada família é descrita num arquivo JSON (`specs/`) e um script pyRevit transforma a especificação em `.rfa` com planos de referência, cotas rotuladas, geometria travada, parâmetros, tipos, materiais e subcategorias. Assim a produção é em série e repetível.

> **Status:** v0 — o gerador foi escrito, mas **ainda não foi executado no Revit**. A primeira tarefa no Claude Code é rodar o piloto (escrivaninha) e corrigir o que a API reclamar. O validador de specs (`tools/validar_specs.py`) já roda e passa.

## Por que nativo (e não Blender → Revit)

Resumo da pesquisa em [`docs/PESQUISA.md`](docs/PESQUISA.md):

- Malha vinda do Blender (OBJ/STL) entra no Revit como forma importada: sem parâmetros, sem tipos, planta suja. Não vende.
- Janela precisa cortar parede e ter largura/altura paramétricas, então só funciona nativa.
- O Blender fica reservado para partes orgânicas (estofados), como OBJ leve visível só no nível de detalhe *Fino*.

## Estrutura

```
familias-revit/
├── CLAUDE.md                     # regras do projeto para o Claude Code
├── config.json                   # versão do Revit, pasta de templates, marca
├── casa/casa_teste.json          # casa térrea para testar os móveis em uso real
├── specs/                        # 1 JSON por família (fonte da verdade)
│   ├── escrivaninha.json         # piloto
│   └── mesa_jantar_retangular.json
├── FamiliasGSVL.extension/       # extensão pyRevit
│   ├── FamiliasGSVL.tab/Gerador.panel/
│   │   ├── GerarFamilia.pushbutton/script.py
│   │   └── FlexTest.pushbutton/script.py
│   └── lib/gsvl_familias/        # biblioteca do gerador
├── tools/
│   ├── validar_specs.py          # valida specs fora do Revit (Python 3)
│   ├── validar_casa.py           # valida a casa-teste e desenha a planta (SVG)
│   └── blender/exportar_obj_leve.py
├── docs/                         # padrão, checklist, pesquisa, roadmap
└── output/                       # rfa/ e logs/ (ignorados pelo git)
```

> **Migrando para o Claude Code no Windows?** Veja [`docs/PROMPT_MIGRACAO.md`](docs/PROMPT_MIGRACAO.md).

## Como usar

1. Instale o [pyRevit](https://github.com/pyrevitlabs/pyRevit/releases).
2. Ajuste o `config.json` (versão do Revit e pasta de templates `.rft`).
3. Registre a extensão: `pyrevit extend ui FamiliasGSVL "<caminho>\familias-revit"` **ou** pyRevit › Settings › Custom Extension Directories, apontando para a pasta do repositório. Depois, Reload.
4. Valide as specs: `python tools/validar_specs.py`
5. No Revit, abra qualquer projeto. Na aba **FamiliasGSVL**, clique em **Gerar Família**, escolha um JSON e o `.rfa` sai em `output/rfa/`.
6. Para testar os móveis numa casa: crie um projeto novo e clique em **Casa Teste** (planta em `docs/planta_casa_teste.svg`).
7. Clique em **Flex Test**, escolha o `.rfa` gerado e o relatório sai em `output/logs/`.

## Requisitos

- Revit 2024 ou mais recente (a API usa `ForgeTypeId`: `SpecTypeId`/`GroupTypeId`)
- pyRevit 4.8+ (motor IronPython padrão)
- Python 3 (só para o validador)
