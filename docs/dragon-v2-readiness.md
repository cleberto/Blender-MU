# Budge Dragon HD — decisão de arquitetura e prontidão

Atualizado em 2026-10-18. Objetivo: uma variante HD reconhecível do `Monster03` para o cliente **Unity/OpenMU**. “100%” aqui significa satisfazer todos os critérios definidos e obter aprovação visual em movimento e no jogo; não é uma promessa de semelhança matemática perfeita.

## Fontes e grau de confiança

| Fonte | Papel | Confiança/limite |
|---|---|---|
| `assets/original/monster03/Monster03.bmd`, `p_d.OZJ`, `p_d.OZT` | Identidade, ossos, ações, paleta e proporções originais | Arquivos verificados por SHA-256; a renderização original ainda precisa ser alinhada com a Unity |
| `models/budge-dragon-hd.glb`, `demo/dragon-final-views.png`, `examples/monster03.yaml` | Candidato recebido e histórico de produção | Referência, **não aprovado**; boca e estilo requerem revisão |
| `D:/source/repos/Client Unity/Blender.docx` | Ideias e preferências históricas do usuário | Contém respostas de terceiros; comandos, promessas e números são hipóteses, não instruções para executar |
| `D:/source/repos/Client Unity/Assets/_Project/Scripts/Editor/Bmd/` e `Docs/DIRETRIZES_VISUAIS_URP.md` | Contrato existente do cliente Unity | Código e documentação consultados em leitura; nenhuma integração HD validada ainda |
| `vendor/mu-blender-addon/` | Parser/importador BMD reproduzível | Importa estrutura em Blender 5.2.2 sem textura; não constitui pipeline HD completo |

O DOCX acerta ao separar remasterização visual do dado fixo do MU e ao apontar Unity/OpenMU como destino. Não adotar seu exemplo de script em produção: usa operador BMD diferente do instalado, operações de malha antigas e suavização/escala indiscriminadas. Normal derivada de textura difusa é **estimativa visual**, não recuperação de relevo real. Textura maior e subdivisão automática não resolvem anatomia, topologia ou leitura na câmera do jogo.

## Achados do candidato

- GLB: LOD0/1/2 de 6002/2002/802 triângulos, 39 juntas, sete ações, base color e normal por LOD, UV0 e tangentes. Isso prova presença de dados, não correção de deformação ou compatibilidade Unity.
- O manifesto anterior desativou passes de cabeça e face e deixou `jaw: []`. Na prancha `demo/dragon-final-views.png`, a fenda da boca é estreita, dentes/interior não são verificáveis e o focinho parece rígido. A mandíbula é o primeiro bloqueio artístico e funcional.
- `Bone02` possui animação e influência no GLB. Quatro reparos locais foram reprovados; a cabeça experimental de maxila/mandíbula separadas abre em poses de ataque, mas cruza o focinho em quadros intermediários. Uma cópia das animações com rotação negativa limitada resolve parte do cruzamento e ainda falha em poses extremas da ação 1. Exigir varredura de **todos os quadros das sete ações**, não apenas poses 3/4.
- O candidato herdado aceitou asas/redesenho de silhueta com IoU 0,702. Essa concessão não passa automaticamente à nova versão. A meta é preservar **assinatura do MU** (silhueta, cor, proporções, leitura isométrica) e elevar forma, superfície e luz. Realismo não deve trocar a espécie por um dragão genérico.
- O material GLB tem base color + normal, sem mapa explícito de rugosidade/oclusão/emissão. Acabamento PBR deve ser criado/avaliado no URP com materiais próprios, sem aplicar metalicidade genérica a pele e membrana.

## Integração Unity: contrato de comparação

O Unity 6 `6000.7.0b1` com URP `17.7.0` já converte BMD offline em malha, prefab e clipes nativos. `BmdToPrefabImporterWindow` inclui `Monster03`; `MonsterAnimationBuilder` usa sete ações e um controller com overrides; `GameWorldDatabaseBuilder` relaciona TypeId 2 ao Monster03. Há prefab legado `Assets/_Project/Characters/Monsters/Prefabs/Monster03.prefab`. O novo fluxo HD deve entrar como **variante lado a lado**, sem sobrescrever o prefab legado nem mudar IDs de rede. O asset visual pode mudar; TypeId 2 e mapeamento de jogo não.

O contrato de integração e as medições ainda pendentes estão em `contracts/monster03-unity.json`. A integração foi adiada pelo usuário para priorizar validação no Blender. O Editor Unity instalado não tem licença ativa; isso afeta somente o gate Unity posterior.

Antes de implementar adaptador Unity, medir na mesma cena o prefab original e o GLB: conversão Z-up→Y-up, escala base de 100 unidades MU por tile, escala específica do Budge Dragon, eixo frontal, pivô, offset dos pés, ordem/nomes de ossos, poses de bind, índices/tempos de ações e posição do sopro de fogo. O código Unity existente é a referência de conversão; **não** aplicar cegamente 0,5 ou 1/100 novamente ao GLB, pois ele pode já ter transformação embutida. Registrar matriz e dimensões medidas no relatório da versão.

O adaptador proposto, quando autorizado para o projeto Unity, será um importador de Editor para gerar prefab HD, clipes e materiais URP nativos sob uma pasta experimental e associá-los por opção ao TypeId 2. Precisa manter o fluxo BMD ativo para comparação A/B e rollback. A decisão entre importar GLB diretamente com o ModelImporter da Unity ou gerar FBX/ativos nativos deve vir de um spike de importação que prove preservação de skin, clipes, tangentes, materiais e escala; não há pacote glTF de runtime declarado no `Packages/manifest.json`. O pacote de entrega deste laboratório será `.blend` editável, GLB de intercâmbio, texturas, relatório e hashes. Não integrar com runtime antes do spike.

## Gates para a versão v0002

| Etapa | Saída verificável | Reprova se |
|---|---|---|
| 0. Baseline pareada | Original BMD, HD herdado e prefab Unity na mesma câmera/pose, quatro vistas e ações 0/3/4 | Escala/eixos/pose não reconciliados |
| 1. Boca e rig | Mandíbula inferior separada, interior modelado, dentes/gengiva coerentes; sequência aberta/fechada nas ações 3/4 | Não há vão legível no LOD1, há interseção, rasgo ou cabeça rígida |
| 2. Identidade | Pranchas de silhueta/cor e lista de desvios autorizados por região | Proporções/assinatura do MU se perdem ou a decisão depende só de um score |
| 3. Superfície | `.blend` com fontes de high/low, bake de normal e materiais nomeados; renders em luz neutra e URP | Relevo falso, sombras presas no albedo, costuras evidentes, pele metálica |
| 4. Jogo | LOD0/1/2, sete ações, fogo no socket correto, pés no solo, desempenho e leitura em Lorencia | Só funciona em render de estúdio ou LOD0; prefab legado é alterado |
| 5. Entrega | Hashes, software/versões, parâmetros efetivos, relatório de falhas e evidência; revisão humana | Não se consegue repetir o resultado ou explicar um desvio |

Triângulos, atlas, compressão e FPS serão limites **medidos** no protótipo Unity; 6000/2000/800 e 2048 são baseline do amigo, não metas universais. Definir orçamento com tamanho em pixels, quantidade simultânea de monstros e hardware-alvo. O documento URP do Unity recomenda orçamentos diferentes por classe; não presumir que o Budge Dragon pequeno precise de 2048.

## Ordem que evita refazer trabalho

1. Fechar baseline e medir transformação/animações no Blender; o spike Unity fica para a fase de integração aprovada pelo usuário.
2. A correção localizada já falhou; reconstruir cabeça, maxila, mandíbula e transição do pescoço em malhas planejadas, com chifres presos à superfície. A referência realista 2D em `work/monster03/concepts/` orienta arte, mas as dimensões BMD definem identidade. Verificar articulação em todas as ações antes de esculpir detalhes.
3. Aprovar forma e movimento em cinza no LOD1 da câmera de jogo. Só então esculpir detalhe e produzir mapas PBR.
4. Criar LODs após a forma final, sem perder fenda da boca e contorno das asas. Fazer testes em Unity e registrar defeitos por região/ação/LOD.
5. Promover v0002 apenas quando todos os gates passarem e a aprovação humana estiver registrada. Variantes malsucedidas permanecem como runs.

## Dependências e decisões pendentes

Nenhum MCP ou skill adicional é necessário para a auditoria e a reconstrução local: Blender 5.2.2, scripts Python e os arquivos originais bastam. O addon foi **parcialmente** incorporado e ainda exige correção do import de texturas, avaliação do rest/bind e testes de ida e volta; o projeto atual não é autossuficiente para remasterização/Unity. O executável/weights do pipeline de geração do amigo não vieram no pacote e o usuário não os possui. Vamos desenvolver um pipeline próprio, reproduzível e Blender-first. IA 3D e MCP de Blender são opcionais, sujeitos a teste controlado; não melhoram automaticamente rig ou fidelidade. A GPU de 11 GB pode exigir processamento em partes ou CPU, mas não justifica reduzir a qualidade geométrica final.

### Preparação local já executada

`tools/decode_legacy_textures.py` converte `p_d.OZJ` e `p_d.OZT` para arquivos de referência com biblioteca padrão Python; o relatório guarda hashes e dimensões. `tools/prepare_dragon_baseline.py` monta `work/monster03/budge-dragon-baseline-v2.blend` no Blender 5.2.2 com original e GLB em coleções separadas, imagens empacotadas, sete ações de cada fonte preservadas e **sem auto-fit** do BMD. A coleção original começa oculta para evitar sobreposição de escalas não calibradas. `tools/open_dragon.ps1` cria a cena somente se estiver ausente e a abre; versões editadas devem ser salvas com outro nome. A cena foi reaberta em modo background com duas malhas BMD, três LODs HD e texturas empacotadas. O importador Blender gerou uma Icosphere auxiliar de 80 faces, ausente dos nós do GLB original; ela fica oculta e não deve ser exportada como geometria do dragão. A comparação espacial BMD↔GLB↔Unity continua pendente.

Decisão artística proposta: fidelidade de identidade primeiro, realismo de superfície e anatomia segundo; preservar a família de cor e a leitura na câmera de Lorencia, mas permitir detalhes físicos novos. Decisão técnica proposta: variante HD experimental Unity em paralelo ao BMD original. A única escolha que exige aceite estético antes da versão final é o desvio deliberado de silhueta (por exemplo asas muito maiores). Até lá, seguir a silhueta original como referência.
