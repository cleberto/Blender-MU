# Padrão de Modernização de Assets MU Online

Este documento contém somente invariantes globais. O procedimento executável pelo agente está em `agent/blender-mu-modernization/SKILL.md`; regras específicas ficam no perfil e nas lições do asset.

## 1. Fonte e preparação

- Preservar BMD, GLB e cenas originais; toda tentativa usa nova saída e novo run.
- Manter `00_ORIGINAL_BMD` intacta e separada do candidato.
- Associar cada mesh à armature do seu Armature Modifier; não adivinhar pela ordem da cena.
- Preservar rest pose, ações, escala e pivô. Não aplicar transforms para mascarar divergências.
- Usar no máximo quatro influências por vértice na exportação, salvo contrato diferente medido no destino.

## 2. Geometria, boca e simetria

- Resolver topologia e movimento em cinza antes de esculpir detalhe, gerar PBR ou criar LODs.
- Preservar silhueta, identidade e pontos de ancoragem; registrar desvios deliberados.
- Não usar Voxel Remesh sobre boca, dedos ou outras cavidades sem proteção e revisão da topologia.
- Boca funcional exige maxila, mandíbula, cavidade e charneira volumétrica planejadas; animação do osso sozinha não prova abertura.
- Não usar Automatic Weights global após resculpt nem corrigir cruzamento apenas aumentando/limitando rotação.
- Medir simetria em rest pose e por região. **Nunca executar `Mesh > Symmetrize` global como correção automática** de modelo rigado/mapeado.
- Corrigir assimetria localmente e revisar pares, costura, UVs, normais e pesos. Assimetria intencional exige exceção registrada em `SYMMETRY_EXEMPT`.

## 3. UVs e materiais

- Base Color em sRGB, sem duplicar luz/sombra antiga com o novo shading.
- Normal em Tangent Space e Non-Color, com bake high-to-low e cage adequados.
- ORM: R = AO, G = Roughness, B = Metallic; Emission somente para emissivos reais.
- Resolução e orçamento são definidos pelo asset e destino; 2K/4K de apresentação não é requisito universal de jogo.
- Evitar metallic genérico em pele/membrana e brilho plástico. Avaliar sob luz neutra e na iluminação de destino.

## 4. Gates obrigatórios

- [ ] Região facial simétrica dentro da tolerância ou exceções intencionais documentadas.
- [ ] Maxila sem peso indevido da mandíbula; rim groups e cavidade presentes quando aplicável.
- [ ] Todas as ações declaradas avaliadas em todos os quadros, sem deformação não finita ou colisão maxila/mandíbula.
- [ ] Abertura medida e revisão visual em movimento sem rasgo, cruzamento ou perda da charneira.
- [ ] LOD1/game camera preserva boca, face, asas, chifres e silhueta; não aprovar somente no LOD0.
- [ ] Materiais revisados sob luz neutra e na iluminação de destino.
- [ ] GLB reimportado em cena limpa, sem helpers, com escala, texturas, pesos e ações corretos.
- [ ] Evidências, hashes, parâmetros, defeitos e gates humanos registrados.

Um gate técnico não substitui aprovação visual humana nem teste no runtime de destino.
