# Padrão de modelagem das famílias

## 1. Template e categoria
| Peça | Template (.rft) | Categoria | IfcExportAs |
|---|---|---|---|
| Mesa, escrivaninha, cama | Mobiliário métrico / Metric Furniture | Mobiliário | IfcFurniture |
| Sistemas de móveis (bancada + gaveteiro) | Sistema de mobiliário / Metric Furniture System | Sistemas de mobiliário | IfcFurniture |
| Janela | Janela métrica / Metric Window | Janelas | IfcWindow |

## 2. Planos de referência
- Origem = ponto de inserção (centro em planta, nível no piso). Janela: centro no eixo da parede, base no peitoril.
- Planos externos: Esquerda (Left), Direita (Right), Frente (Front), Trás (Back), Topo (Top), como referências **fortes**.
- Planos internos: referência fraca (WeakReference) ou NotAReference.
- Nada de geometria "solta": toda face vai alinhada e travada a um plano.

## 3. Parâmetros
- Nomes em português, sem acento, com `_` (ex.: `Espessura_Tampo`). Os rótulos visíveis podem ter acento no futuro via parâmetros compartilhados.
- **Tipo** para dimensões de catálogo (largura, profundidade, altura). **Instância** só para opções de uso (ex.: `Mostrar_Gaveteiro`).
- Toda dimensão tem `faixa` [min, max] na spec, e o flex test testa os extremos.
- Materiais sempre por parâmetro (`Material_*`), nunca fixos.

## 4. Nível de detalhe
| Nível | O que mostra |
|---|---|
| Coarse (Baixo) | Volume envolvente / peças principais |
| Medium (Médio) | Peças principais + painéis |
| Fine (Alto) | Tudo, inclusive puxadores, ferragens e malha orgânica (se houver) |

## 5. Subcategorias
Uma por peça lógica (Tampo, Pés, Painel, Gaveteiro, Caixilho, Folha, Vidro…), para o arquiteto controlar a visibilidade e as penas.

## 6. Identificação (todo tipo)
Fabricante, Modelo, Descrição, URL, Código de montagem, OmniClass, IfcExportAs, Versão da família.

## 7. Peso e desempenho
- Móvel simples < 500 KB; janela < 800 KB.
- Sem CAD importado, sem imagens raster, sem famílias aninhadas desnecessárias.
- Rodar **Purgar não usados** antes de publicar.

## 8. Família híbrida (Blender)
- Malha OBJ ≤ 5.000 faces, escala em mm, origem no ponto de inserção.
- Importada dentro de uma subfamília própria, visível só em **Fine**.
- A geometria nativa simplificada continua em Coarse/Medium e na planta.
