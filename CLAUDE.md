# CLAUDE.md — Famílias Revit para venda

## Contexto
Biblioteca de famílias Revit (.rfa) para VENDER a arquitetos e engenheiros: janelas, mesas, escrivaninhas, camas e outros móveis. Dono: Matheus. Sempre responder em português do Brasil e executar sem perguntas desnecessárias.

## Decisões fixas (não rediscutir)
1. Famílias NATIVAS no Revit: planos de referência, extrusões/sweeps/blends, parâmetros, tipos. **Proibido DirectShape** e malha importada como geometria principal.
2. Geração por script pyRevit (IronPython 2.7 — sem f-strings, usar `.format`) com a API de famílias. Sem MCP.
3. Guiado por dados: `specs/*.json` é a fonte da verdade; o gerador em `FamiliasGSVL.extension/lib/gsvl_familias/` transforma spec em .rfa.
4. Blender só para partes orgânicas (estofados), exportadas como OBJ leve (`tools/blender/exportar_obj_leve.py`), visíveis só no nível *Fino* de uma família híbrida.

## Fluxo de trabalho
- Antes de qualquer coisa: `python tools/validar_specs.py` precisa passar.
- Gerar no Revit (botão "Gerar Família") e depois rodar o "Flex Test". Ler `output/logs/` e corrigir até ficar limpo.
- Quando precisar que o Matheus clique algo no Revit: instruções curtas e numeradas, depois ler o log.
- Um passo por vez, com commit git em português ao final de cada passo funcional.
- Ao concluir uma família, atualizar `docs/CHECKLIST_VENDA.md`.

## Padrão de qualidade (resumo — detalhes em docs/PADRAO.md)
- Unidades em mm nas specs (o gerador converte para pés).
- Origem no ponto de inserção. Planos Esquerda/Direita/Frente/Trás/Topo como referências fortes; geometria alinhada e travada.
- Simetria por cotas EQ nos eixos centrais. Cada parâmetro de dimensão rotula uma cota.
- Níveis de detalhe: Coarse = forma simples; Medium = forma principal; Fine = completo.
- Materiais por parâmetro; subcategorias por peça; parâmetros de identificação (Fabricante, Modelo, Descrição, URL, OmniClass, IfcExportAs).
- Arquivo leve (meta < 500 KB para móvel simples). Passar no flex test sem erros.

## Formato da spec (resumo)
- `parametros`: nome, tipo (`comprimento`|`simnao`|`material`|`texto`), `instancia`, `padrao`, `faixa` [min,max], `formula` opcional (sintaxe que vale no Revit e no Python, ex.: `(Altura - 6 * Espessura_Chapa) / 5`). Parâmetro com fórmula é calculado pelo validador, nunca varia sozinho e não pode receber valor nos `tipos`.
- `planos`: nome, eixo (`x`|`y`|`z`), `pos` (expressão em mm com nomes de parâmetros), `referencia` (Left/Right/Front/Back/Top/Bottom/StrongReference/WeakReference/NotAReference).
- Planos especiais: `@centro_x`, `@centro_y` (planos centrais do template) e `@nivel` (nível de referência).
- `ordens`: sequências de planos (mesmo eixo) que devem ficar sempre em ordem crescente — o validador testa em todos os extremos das faixas.
- `cotas`: `planos` [lista], `eq` true **ou** `rotulo` com o parâmetro.
- `caixas`: extrusões retangulares com `x`/`y`/`z` = [plano_min, plano_max], `material`, `visivel` (parâmetro sim/não), `subcategoria`, `detalhe` (coarse/medium/fine).
- `tipos`: nome + valores.

## Casa-teste (simulação de uso)
- `casa/casa_teste.json`: casa térrea brasileira (~83 m² úteis: suíte, quarto, 2 banheiros, estar/jantar, cozinha, área de serviço), pé-direito 2,80 m, paredes 15 cm externas e 12 cm internas. Coordenadas em mm pelos eixos.
- `python tools/validar_casa.py --svg docs/planta_casa_teste.svg` confere aberturas e móveis (dentro do cômodo, sem colisão, fora do giro das portas) e desenha a planta.
- No Revit: projeto NOVO → botão "Casa Teste" (`gsvl_familias/casa_revit.py`) cria paredes, portas, janelas, piso, ambientes, insere os .rfa de `output/rfa/` e confere a pegada real de cada móvel contra a spec (log `casa_teste_*`).
- Toda família nova entra na casa (`moveis`, com `pendente: true` + `dim_mm` enquanto o .rfa não existir).

## Estado atual
- v0 do gerador escrito, NUNCA executado no Revit.
- Primeira família a rodar (escolha do Matheus): `specs/armario_multiuso_2p.json` (armário multiuso 2 portas). Gerar, corrigir erros de API, flex test e registrar aqui o que foi aprendido. A escrivaninha vem depois.

## Aprendizados (preencher a cada sessão)
- (vazio)
