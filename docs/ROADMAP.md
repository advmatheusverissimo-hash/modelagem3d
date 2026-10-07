# Roadmap

## Fase 1 — Piloto (escrivaninha)
- [ ] Rodar o gerador no Revit e corrigir erros de API
- [ ] Flex test limpo nos 3 tipos e nos extremos das faixas
- [ ] Conferir planta, cortes, 3D e níveis de detalhe
- [ ] Registrar aprendizados no CLAUDE.md

## Casa-teste
- [x] Planta da casa térrea em JSON + validador + desenho SVG
- [ ] Rodar o botão "Casa Teste" no Revit e corrigir erros de API
- [ ] Usar a casa para renders de catálogo (vistas 3D por cômodo)

## Fase 2 — Móveis retos
- [ ] Armário multiuso 2 portas (spec `armario_multiuso_2p.json` criada e validada; 1ª família a rodar no Revit)
- [ ] Linhas simbólicas em planta (arco de abertura das portas) — o gerador ainda não cria
- [ ] Prateleiras em quantidade variável (hoje são 4 fixas, distribuídas por fórmula)
- [ ] Mesa de jantar retangular (spec já criada)
- [ ] Mesa redonda: o gerador precisa de suporte a extrusão circular (`cilindros`)
- [ ] Cama (solteiro/casal/queen/king): estrutura + cabeceira + colchão nativo simplificado
- [ ] Suporte a sweeps (perfis de tampo com borda) e blends (pés cônicos)

## Fase 3 — Janelas
- [ ] Suporte ao template de janela no gerador (hospedeira em parede, vazio de corte "Opening")
- [ ] Janela de correr 2 folhas e 4 folhas
- [ ] Maxim-ar
- [ ] Parâmetros: Largura, Altura, Peitoril (Altura do peitoril padrão), Espessura_Caixilho, Material_Caixilho, Material_Vidro
- [ ] Linhas simbólicas de abertura em planta

## Fase 4 — Híbridos (Blender)
- [ ] Estofados (sofá, poltrona) com malha OBJ leve só em Fine
- [ ] Rotina de importação OBJ dentro da família pelo gerador

## Fase 5 — Comercial
- [ ] **Lote de release em Revit comercial**: desenvolver e testar no educacional; na hora de vender, rodar o gerador sobre as specs num Revit comercial (completo — o Revit LT não roda pyRevit/API) e publicar só esses .rfa
- [ ] Decidir a versão mínima de venda (salvar a partir da versão mais antiga suportada, pois .rfa não abre em Revit anterior)
- [ ] Definir marca e preço; páginas de produto com imagens e ficha técnica
- [ ] Plataformas: loja própria, BIMobject/BIMsmith, marketplaces de conteúdo BIM
- [ ] Pacotes (ex.: "Home office completo") e licença de uso
