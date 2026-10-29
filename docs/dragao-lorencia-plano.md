# Dragão de Lorencia: plano de reconstrução com revisão rigorosa

> **Atualização de arquitetura:** leia primeiro `docs/dragon-v2-readiness.md`. O destino confirmado é o cliente Unity/OpenMU. As menções abaixo a instalar no cliente GLB privado do pacote recebido descrevem apenas a validação histórica do amigo, não o caminho de integração deste projeto.
>
> **Atualização experimental:** `docs/monster03-v0002-experiments.md` registra quatro tentativas de separação/reponderação da mandíbula. Nenhuma atingiu o gate visual. A próxima rota é reconstruir a topologia da cabeça e a cavidade bucal, mantendo os arquivos do GLB herdado imutáveis.

## Estado verificado em 18/10/2026

O monstro é o **Budge Dragon**, `Monster/Monster03.bmd` (índice 2 no cliente). O pacote recebido já contém `models/budge-dragon-hd.glb`, com 3 LODs de 6002/2002/802 triângulos, 39 juntas e as 7 ações originais. Isso é uma base útil para edição, não uma peça aprovada para o padrão de qualidade desejado.

O original e suas duas texturas foram copiados, sem alteração, do cliente em `E:\Comuns\Downloads\Ult MU\Data\Monster\` para `assets/original/monster03/`:

| Arquivo | SHA-256 |
|---|---|
| `Monster03.bmd` | `9758900D276F4DB86F237A31C0617FA00EE04469D964865E71BDDA01E20AE474` |
| `p_d.OZJ` | `A1A4673400834EAB6ADC190CAA268516D81DA5B23A88985686EBD95F5FEFEF68` |
| `p_d.OZT` | `5F896E492CB80A7770074142F9FC921CAD40B99746A2B1331D6BBD26F2C679D3` |

O BMD usa `p_d.jpg` no corpo e `p_d.tga` nas membranas das asas (no cliente, `OZJ` e `OZT`). A malha original tem 324 + 8 triângulos. A cadeia `Bone01` → `Bone02` → `Bone03` sai de `Bip01 Head`; **Bone02** move 4 vértices originais e gira nas sete ações, com amplitude de aproximadamente 0,905 rad na ação 3. O GLB conserva canais de animação dessa junta e tem 291 vértices do LOD0 com peso > 0,05 nela. Portanto, a hipótese prioritária é que a articulação da mandíbula existe, mas a geometria gerada e a distribuição dos pesos não formam uma abertura convincente. Confirmar visualmente a localização desses vértices antes de editar.

Em `examples/monster03.yaml`, a mandíbula está vazia (`bones.jaw: []`), `face.enabled: false` e `head.enabled: false`. A descrição do projeto registra que essas etapas foram puladas porque o monstro é pequeno na câmera do jogo. Para esta nova meta, isso deixa a boca sem correção anatômica. O mesmo arquivo aceita desvios grandes da silhueta original: IoU 0,702 e Chamfer 0,013, por decisão anterior sobre as asas. Essa aceitação não deve ser herdada automaticamente para uma versão que busca maior fidelidade.

## Estratégia

Tratar o BMD e suas animações como **verdade de identidade, escala, pivô e movimento**. Tratar o GLB existente como candidato de alta definição a ser reparado, preservando um arquivo mestre sem mudanças. Só regenerar a forma inteira se os defeitos de cabeça, proporção ou asas não puderem ser corrigidos localmente. Imagens de IA são referências de forma/material; não substituem vistas ortográficas conferidas contra o original.

O primeiro ciclo deve concentrar-se no rosto: separar mandíbula inferior e superior, criar interior da boca e espessura real de lábios, dentes e gengiva, corrigir a junção da mandíbula na cabeça e refazer os pesos no `Bone02` (ou em uma junta nova, se a análise das poses mostrar que `Bone02` não é suficiente). Abertura e fechamento devem ser vistos nas ações 3 e 4, inclusive na transição para idle. Se for preciso introduzir uma junta nova, verificar antes se o cliente GLB suporta o esqueleto alterado e manter o efeito de fogo ligado ao `Bip01 Head` (índice 7). Não modelar dentes apenas como pintura na textura.

Depois da boca, revisar silhueta nas quatro vistas, anatomia das asas e membranas, contato dos pés, cauda, microdetalhe e material. O GLB de referência foi visto em `demo/dragon-final-views.png`: o focinho tem uma fenda quase fechada e o modelo de conceito difere bastante do original. Cada revisão deve comparar **original, candidato atual e novo candidato** sob a mesma câmera e pose. A câmera padrão do jogo usa LOD1 para esse monstro; o rosto deve funcionar no LOD1, não só no LOD0 de estúdio.

## Etapas e critérios de saída

1. **Base reproduzível.** Abrir BMD e GLB no Blender 5.2.2, renderizar frente/lado/costas/topo e quadros das sete ações, nomear o estado inicial como `baseline`. Registrar escala, orientação, pivô, limites e caixas da cabeça, boca e asas. Não sobrescrever os três arquivos originais.
2. **Diagnóstico da mandíbula.** Mostrar os vértices e pesos de `Bone02` em cada LOD e a transformação dessa junta por quadro. Comparar posição da maxila/mandíbula no BMD e no GLB nas ações 0, 3 e 4. Decidir se corrigir topologia/pesos no GLB é suficiente.
3. **Forma e rig.** Fazer variantes numeradas, com arquivo `.blend` mestre e GLB exportado por variante. Primeira variante: reparo localizado da cabeça e da boca. Só abrir uma rota de nova geração 3D se a revisão da silhueta e anatomia reprovar esse reparo. Para nova geração, usar vistas e máscara/silhueta do original como restrições, escolher sementes visualmente e fazer retopologia manual nas regiões articuladas.
4. **Materiais.** Usar o original como referência de paleta e marcações, com textura base, normal e rugosidade coerentes. Corrigir costuras das raízes das asas já anotadas no pacote. Evitar sombras permanentes pintadas na base color. Inspecionar colorimetria sob luz neutra e luz do cliente.
5. **Validação técnica.** Conferir malha fechada onde necessário, normais, UVs, distorção, sobreposição, até quatro pesos por vértice, juntas, sete ações, três LODs, atlas ≤ 2048, pivô e nomes. No ataque, medir visualmente um espaço real entre as arcadas, dentes sem interseção, mandíbula sem rasgar pele e fogo saindo do ponto correto. Repetir em LOD0/1/2.
6. **Validação artística e no jogo.** Pranchas de comparação nas mesmas poses/câmeras e inspeção no cliente Unity/OpenMU em Lorencia. Resolver a escala por medição entre os prefabs BMD e HD; o fator 0,5 do cliente legado não pode ser reaplicado sem conferir a transformação do GLB. Registrar falhas específicas e corrigir. Só chamar de final depois da aprovação humana nas vistas de perto **e** na câmera normal do jogo.

**Critério de excelência:** não é um único escore ou prompt. É uma ficha de defeitos por região, versões rastreáveis e gates automáticos + inspeção visual em movimento. Os números do pipeline do amigo são ponto de partida; para a boca, a condição explícita de abertura e ausência de deformações é nova e obrigatória.

## Ferramentas e portabilidade

- **Neste chat/Codex:** manter a especificação e os scripts no projeto; operar Blender 5.2 em modo background para importação, relatórios, renders e exportação. Gerar conceitos apenas quando as vistas originais estiverem prontas; registrar qual imagem e semente originaram cada variante. O ChatGPT pode avaliar as pranchas e escrever automações, mas a seleção estética final fica com o operador.
- **Claude Code:** abrir este projeto como diretório de trabalho e dar ao Claude este documento, `agent/hd-model-pipeline/SKILL.md`, `docs/hd-model-pipeline.md`, `docs/hd-model-reproduce.md` e `examples/monster03.yaml`. Pedir que implemente os mesmos scripts e gates locais, sem assumir que `tools/hdmodel` existe aqui. O pacote compartilhado contém a **receita**, não o executável nem os pesos de IA.
- **Addon em `vendor/mu-blender-addon/`:** é uma cópia do módulo BMD de `D:\source\mu-blender-addon-main`; o importador BMD e o parser puro são úteis, mas o editor de mapas não é necessário para o dragão. O addon registra no Blender 5.2.2 e importa geometria, armature e sete ações com texturas desligadas. Com texturas ligadas, falha em `formats/textures.py` por ausência de Pillow no Python embutido (`NameError: Image is not defined`). Há ainda uso de `mesh.use_auto_smooth` protegido por `try/except`, API antiga, e aviso de `rest-vs-bind mismatch bones: 29/39`; é preciso validar poses contra o jogo antes de confiar no exportador. Modernizar a cópia versionada com testes de ida e volta antes de usar o addon para substituir arquivos do cliente.
- **Serviços de IA na nuvem:** opcionais. A receita original exige GPU NVIDIA de 24 GB ou mais e vários modelos/weights; não há vantagem em montar toda essa infraestrutura antes de medir quanto o reparo local resolve. Se a reconstrução integral se tornar necessária, escolher o serviço por testes de consistência entre vistas, topologia e capacidade de fornecer arquivos de saída, custos e disponibilidade atuais. Não presumir que uma imagem bonita garante malha animável.

## Comandos de auditoria já disponíveis

```powershell
py -3.9 tools\audit_dragon.py assets\original\monster03\Monster03.bmd models\budge-dragon-hd.glb
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b --python tools\blender_smoke.py -- D:\source\Blender\assets\original\monster03\Monster03.bmd D:\source\Blender\models\budge-dragon-hd.glb
```

O segundo comando desliga texturas no importador legado para testar a estrutura. Nenhum dos dois altera o modelo ou o cliente.

## Prompt inicial reutilizável

> Trabalhe no diretório deste projeto. Leia `docs/dragao-lorencia-plano.md` e os arquivos de referência nele citados. O objetivo é elevar a fidelidade e a qualidade do Budge Dragon de Lorencia, em especial criar uma boca anatomicamente coerente que abra nas ações de ataque. Comece auditando BMD, GLB, esqueleto, pesos e poses. Produza uma prancha comparativa do original e do candidato nas mesmas câmeras/quadros e um diagnóstico dos defeitos. Preserve fontes e arquivos mestres. Proponha a menor correção de geometria/rig que resolva os defeitos, implemente-a em uma variante rastreável e valide LOD0/1/2 e todas as animações. Não declare a peça final sem revisão visual da boca em movimento e no jogo. Se ferramentas/serviços externos forem necessários, explique exatamente o ganho esperado e as dependências.

Esse prompt serve em ChatGPT/Codex ou Claude Code. A especificação e os arquivos no projeto são a fonte comum de contexto; instruções específicas de cada agente não devem redefinir os critérios de qualidade.
