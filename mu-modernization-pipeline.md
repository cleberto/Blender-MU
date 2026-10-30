# Pipeline de Modernização de Assets MU Online

O fluxo oficial deste repositório é **Blender-first, reproduzível e orientado por evidências**. Esta página é um índice; não duplica regras nem substitui os documentos específicos do asset.

## Entrada para agentes

1. `CLAUDE.md` — ponto de entrada do Claude.
2. `AGENTS.md` — integridade, versionamento e catálogo.
3. `agent/blender-mu-modernization/SKILL.md` — procedimento operacional completo.
4. `PIPELINE_STANDARDS.md` — invariantes globais de qualidade.
5. `docs/architecture.md` — registry, versões, runs e lições.

## Fluxo resumido

```text
BMD/GLB original preservado
  → baseline e referências pareadas
  → graybox/topologia
  → rig e todos os quadros de todas as ações
  → identidade e simetria regional
  → UV, bake e materiais
  → LODs e câmera normal do jogo
  → GLB e reimportação limpa
  → revisão humana
  → integração no runtime, quando autorizada
```

Não avance para superfície enquanto boca, articulações ou topologia estiverem reprovadas. Não use subdivisão, upscale, normal derivada da difusa, pós-processamento ou um render bonito para esconder essas falhas.

## Ferramentas atuais

- `tools/prepare_dragon_baseline.py`: cria a baseline não destrutiva do Monster03.
- `tools/monster_engine.py`: executa um construtor específico por perfil; não é um reparo universal.
- `tools/inspect_glb_symmetry.py`: mede simetria diretamente no GLB sem alterá-lo.
- `tools/validate_rig_symmetry.py`: valida simetria regional, pesos, todos os frames, colisão entre bocas separadas e abertura por rim groups.
- `tools/audit_monster_scene.py`: auditoria técnica geral dirigida pelo perfil.
- `tools/render_monster_pose_sheet.py`: gera evidências de movimento para revisão.

O comando completo de validação e os nomes esperados dos objetos estão na skill. Ausência de Blender, cena ou evidência deve ser reportada como teste não executado, nunca como aprovação.

## Monster03 / Budge Dragon

Leitura obrigatória:

- `docs/dragon-v2-readiness.md`
- `docs/monster03-v0002-experiments.md`
- `knowledge/lessons/dragon-jaw-bone02.json`
- `knowledge/lessons/dragon-face-symmetry.json`
- `profiles/monster03.json`

Estado: o corpo HD recebido é baseline visual, não asset aprovado. `Bone02` anima, mas a cabeça contínua não possui topologia bucal funcional. Cortes/reweights/enxertos anteriores foram reprovados. A próxima etapa é reconstruir localmente maxila, mandíbula, cavidade e charneira volumétrica, corrigir a assimetria facial regional e validar as sete ações em todos os quadros antes de PBR e LODs.

## Escopo de aprovação

`candidate` ou `eligible_for_review` não significa `approved`. A aprovação exige gates técnicos, revisão humana em movimento e na câmera do jogo e, quando aplicável, validação no cliente Unity/OpenMU. Nenhum experimento deve sobrescrever o original, instalar dados no cliente ou alterar o prefab legado sem autorização específica.
