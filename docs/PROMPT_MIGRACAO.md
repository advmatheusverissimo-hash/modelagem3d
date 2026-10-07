# Migração para o Claude Code (no Windows, junto do Revit)

## Por que o Claude Code

O projeto é código (gerador pyRevit + specs JSON + validador + git). O ciclo de trabalho é **gerar → rodar no Revit → ler o log → corrigir → commit**. No chat, você faria esse vaivém copiando e colando. No Claude Code, ele lê `output/logs/` direto, edita os arquivos, roda `python tools/validar_specs.py`, tenta `pyrevit run` e faz os commits sozinho. O `CLAUDE.md` deste repositório é carregado automaticamente em toda sessão, então as regras não se perdem.

**Atenção:** precisa ser o Claude Code rodando **no seu PC Windows, onde está o Revit**. A versão na nuvem (claude.ai/code) não tem Revit e não consegue gerar nem testar `.rfa`. Ela serve só para editar código e documentos.

## Passo a passo no Windows

1. Instale o **Git for Windows** e o **Python 3** (marque "Add to PATH").
2. Instale o **pyRevit** (instalador `.exe` da página de releases do pyRevit) e abra o Revit uma vez para confirmar que a aba pyRevit aparece.
3. Instale o **Claude Code** pelo app desktop do Claude (aba Code) ou pelo terminal, conforme a documentação oficial do Claude Code para Windows.
4. Clone o repositório numa pasta curta, sem acentos e fora do OneDrive:
   ```
   cd C:\
   git clone https://github.com/advmatheusverissimo-hash/modelagem3d.git C:\familias-revit
   cd C:\familias-revit
   ```
5. Abra o Claude Code **dentro de `C:\familias-revit`** e cole o prompt abaixo.

## Prompt para colar no Claude Code

```
Responda sempre em português do Brasil e execute sem me fazer perguntas desnecessárias.

Este repositório (C:\familias-revit) é a minha biblioteca de famílias Revit (.rfa) para venda. Ele veio de outro ambiente, sem acesso ao Revit: o gerador v0 foi escrito, mas NUNCA rodou no Revit. Leia primeiro, nesta ordem: CLAUDE.md, README.md, docs/PADRAO.md, docs/ROADMAP.md, docs/CHECKLIST_VENDA.md, specs/escrivaninha.json e todo FamiliasGSVL.extension/lib/gsvl_familias/. As regras do CLAUDE.md valem como decisões já tomadas: não rediscuta (famílias nativas, sem DirectShape, sem MCP, geração por specs JSON, Blender só para partes orgânicas na vista Fine).

Etapa 0: diagnóstico do ambiente (faça primeiro e me reporte em uma tabela)
- Versões do Revit instaladas (C:\Program Files\Autodesk\Revit 20xx) e a pasta de templates de família (C:\ProgramData\Autodesk\RVT 20xx\Family Templates\). Liste os subidiomas, diga qual é o idioma dos templates e quais .rft servem para Mobiliário, Sistema de mobiliário e Janela (métricos).
- pyRevit instalado? Versão do CLI (`pyrevit --version`), motor padrão (IronPython ou CPython) e se `pyrevit run` funciona nesta máquina com a minha versão do Revit.
- Versões do Python e do git.
- Se faltar algo, diga exatamente o que instalar e pare até eu confirmar.
- Corrija o config.json (revit_versao e templates_dir) e os nomes de template nas specs, se não baterem com o que existe na máquina. Rode `python tools/validar_specs.py` e confirme que passa.

Etapa 1: completar a estrutura
- Registre a extensão no pyRevit (`pyrevit extensions paths add "C:\familias-revit"` ou o equivalente da versão instalada) e me dê instruções curtas e numeradas para eu dar Reload e conferir a aba FamiliasGSVL com os botões "Gerar Família" e "Flex Test".
- Falta a pasta tests/: crie um script de flex test em lote, executável via `pyrevit run` (se funcionar) e também pelo botão, que percorra todos os .rfa de output/rfa/, todos os tipos, os extremos de cada faixa da spec, e registre erros e avisos em output/logs/. Reaproveite gsvl_familias/flex.py em vez de duplicar código.
- Mantenha IronPython 2.7 compatível (sem f-strings) enquanto o motor padrão for IronPython.

Etapa 2: piloto (escrivaninha)
- Escrivaninha paramétrica: largura de 1000 a 1800, profundidade de 500 a 700, altura de 750, tampo de 25, pés, painel frontal, gaveteiro lateral opcional (Sim/Não de visibilidade) e 3 tipos (1200x600, 1400x600, 1600x700). A spec já existe em specs/escrivaninha.json.
- Gere o .rfa (via `pyrevit run` ou me pedindo para clicar em "Gerar Família"), leia o log em output/logs/, corrija os erros de API e repita até gerar limpo. Depois rode o flex test e corrija até passar sem erros nem avisos.
- Confira o padrão de qualidade do CLAUDE.md/PADRAO.md: Strong Reference nos planos externos, geometria travada, níveis de detalhe Coarse/Medium/Fine, linhas simbólicas em planta, subcategorias, materiais por parâmetro, identificação (Fabricante, Modelo, Descrição, URL, Código de montagem, OmniClass, IfcExportAs = IfcFurniture), arquivo abaixo de 500 KB e pré-visualização 3D.
- Registre na seção "Aprendizados" do CLAUDE.md cada pegadinha de API que encontrar, para não repetir nas próximas famílias.
- Me passe o passo a passo, curto e numerado, para eu abrir e conferir a família no Revit (planta, 3D, troca de tipos, gaveteiro liga/desliga, níveis de detalhe).
- Atualize docs/CHECKLIST_VENDA.md e docs/ROADMAP.md e faça commit em português.

Etapa 2b: casa-teste
- Crie um projeto novo no template de Arquitetura e rode o botão "Casa Teste" (casa/casa_teste.json). Leia o log casa_teste_*, corrija os erros de API até a casa sair limpa e os móveis gerados aparecerem nos cômodos certos, com a pegada real batendo com a spec. Me dê o passo a passo para eu conferir em planta e 3D.

Etapa 3: em seguida, nesta ordem (uma família por vez: gerar, testar, corrigir, commit, atualizar o checklist)
1. Mesa de jantar retangular (a spec já existe) e redonda (adicione ao gerador o suporte a extrusão circular).
2. Cama (solteiro, casal, queen e king), com estrutura nativa e colchão nativo simplificado. Deixe preparado o encaixe para uma malha OBJ opcional só na vista Fine (tools/blender/exportar_obj_leve.py).
3. Janela no template de Janela: corta a parede, com Largura, Altura, Peitoril, caixilho, folhas e material do vidro, linhas de abertura em planta e tipos de correr 2 folhas, de correr 4 folhas e maxim-ar. IfcExportAs = IfcWindow.

Forma de trabalhar
- Um passo por vez: gerar, testar, corrigir e commit em português. Faça push para o GitHub ao final de cada família.
- Quando precisar que eu clique algo no Revit, me dê instruções curtas e numeradas e depois leia o log sozinho.
- Nunca marque uma família como pronta sem o flex test limpo.
```

## Depois da migração

- O histórico do git já veio junto, então é só continuar commitando em `C:\familias-revit`.
- Os `.rfa` e os logs ficam fora do git (`.gitignore`). Para vender, guarde os `.rfa` finais em outro lugar (por exemplo, numa pasta de releases ou no Drive).
