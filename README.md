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

### Caminho rápido (Windows)
1. Clone: `git clone https://github.com/advmatheusverissimo-hash/modelagem3d.git C:\familias-revit`
2. No PowerShell: `powershell -ExecutionPolicy Bypass -File C:\familias-revit\instalar.ps1`
   (confere git/python/pyRevit, acha o Revit e os templates, ajusta o `config.json`, registra a extensão e grava `output\logs\diagnostico_*.txt`).
3. Feche e reabra o Revit. Na aba **FamiliasGSVL**, clique em **Rodar Tudo** (funciona até na tela inicial).
4. Ele gera todas as famílias de `specs/` em `output/rfa/`, roda o flex test em cada uma, cria a casa-teste num projeto novo, mobilia e abre a casa. Copie o RESUMO da janela de saída e cole no chat.

### Botões avulsos
- **Gerar Família**: escolhe um JSON de `specs/` e gera o `.rfa`.
- **Flex Test**: testa a família ativa (ou um `.rfa` escolhido).
- **Casa Teste**: monta a casa no projeto ativo (precisa ser um projeto novo). Planta em `docs/planta_casa_teste.svg`.
- Fora do Revit: `python tools/validar_specs.py` e `python tools/validar_casa.py`.

## Requisitos

- Revit 2024 ou mais recente (a API usa `ForgeTypeId`: `SpecTypeId`/`GroupTypeId`)
- pyRevit 4.8+ (motor IronPython padrão)
- Python 3 (só para o validador)
