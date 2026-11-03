# MU Asset Lab — Guia de Execução para Agentes / Claude

Este é o ponto de entrada operacional para o modelo que executará o pipeline no Blender.
Antes de editar qualquer geometria, armature, pesos ou texturas, siga rigorosamente as instruções abaixo e a skill em `agent/blender-mu-modernization/SKILL.md`.

---

## 1. Verificação Rápida de Integridade (Doctor)

Antes de iniciar qualquer trabalho, execute o diagnóstico do ambiente e do registro:

```bash
# Windows / Linux / macOS:
python tools/run_pipeline.py doctor
```

- Valida se o catálogo de assets, versões e schemas JSON estão 100% íntegros (0 erros).
- Detecta automaticamente o executável do Blender (em `BLENDER_PATH`, no PATH do sistema ou em pastas padrão da Blender Foundation).

---

## 2. Preparação dos Arquivos Base (Sem Destruição)

Para o Budge Dragon (`monster03`) ou novos monstros:

```bash
# 1. Decodificar texturas OZJ/OZT para JPG/PNG de referência:
python tools/run_pipeline.py textures

# 2. Montar a cena base no Blender (preservando 00_ORIGINAL_BMD e 01_HD_GLB):
python tools/run_pipeline.py baseline --profile profiles/monster03.json
```

A cena de trabalho será gerada em `work/monster03/budge-dragon-baseline-v2.blend`.

---

## 3. Execução da Anatomia de Boca & Rigging (`MOUTH_UPPER` / `MOUTH_LOWER`)

O gargalo identificado nos experimentos anteriores era a continuidade geométrica do crânio impedindo a abertura da mandíbula. O pipeline agora possui construtor automatizado de peças anatômicas:

```bash
# Constrói MOUTH_UPPER (sem peso em Bone02) e MOUTH_LOWER (com Bone02) e os grupos RIM:
python tools/run_pipeline.py mouth --scene work/monster03/budge-dragon-baseline-v2.blend
```

Este script:
- Cria `MOUTH_UPPER` com o grupo de vértices `MOUTH_UPPER_RIM`.
- Cria `MOUTH_LOWER` dirigido por `Bone02` com o grupo `MOUTH_LOWER_RIM`.
- Insere cavidade bucal, dentes e língua sem furar a malha externa.
- Gera o arquivo pronto para validação em `work/monster03/candidate-mouth-rig.blend`.

---

## 4. Validação Rigorosa de Gates Técnicos

Execute o validador de simetria, rotação e colisão BVH da boca:

```bash
python tools/run_pipeline.py validate --profile profiles/monster03.json
```

O validador verifica:
1. **Simetria Facial Localizada**: Mede a região da cabeça em rest pose (nunca execute `Mesh > Symmetrize` global).
2. **Isolamento de Pesos da Mandíbula**: Confirma zero vazamento de `Bone02` na maxila superior (`MOUTH_UPPER`).
3. **Varredura Completa de Ações**: Avalia cada quadro de todas as 7 animações (`action00` a `action06`), checando se há valores não finitos ou colisão BVH entre maxila e mandíbula.
4. **Abertura Efetiva de Boca**: Mede a distância entre os centros de `MOUTH_UPPER_RIM` e `MOUTH_LOWER_RIM` nas poses de ataque (`action03` e `action04`).

---

## 5. Execução do Motor de Construção (Engine Build) & Prancha de Poses

Para rodar a compilação completa com renderização da folha de contato 7x3 das poses:

```bash
python tools/monster_engine.py build profiles/monster03.json
```

Produz em `work/monster03/engine-runs/<run-id>/`:
- `candidate.blend`: cena Blender final testada.
- `audit.json`: relatório detalhado de todos os testes de vértices, pesos e ações.
- `poses/full-body-actions.png`: prancha visual completa com 21 frames de validação.
- `provenance.json`: registro de hashes SHA-256 e comandos executados.

---

## Invariantes Obrigatórios (Regras de Ouro)

1. **Nunca use `Mesh > Symmetrize` Global**: Isso desregula a UV, inverte normais e destrói o rig. Se houver assimetria, corrija regionalmente no vertex group correspondente.
2. **Nunca use `With Automatic Weights`**: Sobrescreve o rig clássico do MU. Use o modificador `Data Transfer` com `NEAREST_FACE_INTERPOLATED` para projetar pesos da malha base.
3. **Limite de 4 Pesos por Vértice**: O contrato para motores modernos exige no máximo 4 influências de ossos por vértice normalizadas.
4. **Uma Aprovação Técnica Não é Aprovação Final**: O modelo só é considerado `approved` após aprovação visual humana em movimento e teste na câmera isométrica do cliente.
