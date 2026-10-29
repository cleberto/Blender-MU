# Padrão de Modernização de Assets MU Online

## 1. Importação & Preparação
- Sempre preservar o arquivo bruto: `[Nome]_00_RAW.blend`.
- Conferir armature: no máximo 4 influências de peso por vértice.
- Verificar integridade de bones faciais/mandíbula antes de qualquer modificação.

## 2. Modelagem & Esculpir (Resculpt)
- Manter simetria ligada (Eixo X) para cabeça, torso e membros simétricos.
- Não aplicar Voxel Remesh com cavidades (boca, dedos fechados) sem mascaramento prévio.
- Manter a silhueta e pontos de ancoragem fiéis ao original.

## 3. UVs e Texturas PBR
- Resolução padrão de apresentação: 2048x2048 (2K) ou 4096x4096 (4K).
- Textura ORM packed:
  - R: Ambient Occlusion
  - G: Roughness
  - B: Metallic
- Normal Map: Tangent Space, Non-Color.

## 4. Gates de Aprovação (Checklist)
- [ ] Simetria facial e corporal consistente.
- [ ] Articulações e boca abrem e fecham sem puxar vértices vizinhos indevidos.
- [ ] Shaders sem brilho excessivo/plástico (Roughness calibrado).
- [ ] Teste de animação: Idle, Walk, Attack, Die executados sem artefatos de skinning.
- [ ] Exportação GLB validada via reimport limpo.
