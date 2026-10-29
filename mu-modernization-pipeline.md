# Pipeline de Modernização de Assets MU Online (.bmd -> Blender -> PBR/GLB)

Este guia define o procedimento operacional padrão para modernizar monstros, NPCs, armaduras e itens do MU Online, garantindo padrão de apresentação nível Sketchfab e integridade técnica para o cliente.

---

## 1. Regras Fundamentais (Invioláveis)
1. **Nunca esculpir ou retopologizar diretamente na malha crua do BMD.** Manter sempre a collection `00_ORIGINAL_BMD` intacta.
2. **Preservar a Armature e as Ações:** Não aplicar transforms (Ctrl+A) de rotação/escala na Armature sem congelar a Rest Pose correspondente.
3. **Máximo de 4 influências de peso por vértice** no modelo de exportação final.

---

## 2. Checklist Técnico Específico de Anatomia & Rig
### A. Mandíbula e Cavidade Bucal
- **Verificação Pré-Sculpt:** Isolar os dentes e a mandíbula inferior em sub-objetos ou aplicar máscaras de escultura para evitar que lábio superior e inferior sofram fusão por remesh.
- **Checagem de Vertex Weights:**
  - O grupo de vértice da mandíbula (`Jaw` ou bone equivalente) deve conter apenas os vértices da metade inferior da boca.
  - Nunca usar *Automatic Weights* global na cabeça após o resculpt. Use *Data Transfer* a partir da malha original com interpolação de topologia limpa, ajustando manualmente o loop dos lábios.

### B. Simetria Facial e Corporal
- Antes de iniciar a escultura, alinhar a malha no centro X = 0.
- Ligar sempre **Sculpt Symmetry (X)**.
- Caso ocorra assimetria não intencional, rodar `Mesh > Symmetrize (-X to +X)` no Modo Edição antes de qualquer bake de normais.

---

## 3. Estrutura de Texturas PBR
- **Base Color:** Textura sem luz/sombra pré-bakeada (de-lighted), sRGB.
- **Normal Map:** Tangent Space, Non-Color, gerado a partir do High-Poly esculpido para o Low-Poly limpo.
- **ORM Texture (Packed):**
  - Canal R: Ambient Occlusion
  - Canal G: Roughness (Pele/Escamas: 0.5-0.7 | Metais: 0.2-0.35 | Chifres/Ossos: 0.4-0.6)
  - Canal B: Metallic (Monstros: 0.0 | Armaduras/Armas metálicas: 1.0)
- **Emission:** Apenas para olhos, núcleos de fogo e runas incandescentes.

---

## 4. Estúdio de Renderização Padrão
Executar `setup_mu_studio.py` no Blender:
- **Motor:** Cycles (256 samples, Denoise ativado).
- **Color Management:** AgX com Look 'Medium High Contrast'.
- **Câmera:** 85mm posicionada na altura do peito/olhos, ângulo heroico.
- **Iluminação 3 Pontos:** Key Light (quente suave), Fill Light (fria suave), Rim Light (destaque na silhueta e escamas traseiras).

---

## 5. Gates de Aprovação (Definição de Pronto)
1. **Gate 1 (Geometria):** Simetria perfeita e silhueta reconhecível do monstro clássico.
2. **Gate 2 (Deformação):** Boca abre e fecha limpa na ação de rugido/ataque sem arrastar o crânio superior.
3. **Gate 3 (Materiais):** Shaders PBR equilibrados sob luz branca neutra, sem efeito plastificado.
4. **Gate 4 (Export):** Teste de round-trip em GLB limpo sem erros de escala, peso ou textura.



# Pipeline de Modernização de Assets MU Online (Blender-MU Asset Lab)

Diretrizes operacionais e regras para o agente (Claude / Automação) no repositório `Blender-MU`.

---

## 1. Regras do Repositório & Integridade (Invioláveis)
1. **Consulte o Registro Primeiro:** Antes de editar qualquer monstro/item, execute `py -3.9 tools/registry.py show <asset-id>` e leia o respectivo `profiles/<asset>.json`.
2. **Imutabilidade do Original:** A collection `00_ORIGINAL_BMD` e os arquivos sob `assets/original/` são estritamente somente-leitura.
3. **Preservação de Rest Pose & Ações:** A armature (`mu_root`) gerencia as 7 ações (`action00` a `action06`). Nunca aplique rotação/escala com `Ctrl+A` sem congelar a Rest Pose.
4. **Sem Enxertos Paramétricos:** Conforme registrado nos experimentos do `Monster03`, não tente enxertar cabeças inteiras externas (*head grafts*). Mantenha o crânio/corpo HD herdado e faça retopologia local da cavidade bucal com interior modelado (`requires_mouth_interior: true`).
5. **Máximo de 4 pesos por vértice** para compatibilidade com Unity URP.

---

## 2. Protocolo Anti-Erros de Anatomia & Rig
### A. Mandíbula e Abertura Bucal
- **Ossos Críticos:** Cabeça = `Bip01 Head`, Mandíbula = `Bone02`.
- **Topologia:** Criar loops contínuos contornando os lábios, modelando a cavidade interna (gengiva/dentes) como geometria separada da casca do crânio.
- **Weights:** O grupo `Bone02` deve conter **apenas** a mandíbula e dentes inferiores. Nenhum vértice da maxila superior pode ter peso em `Bone02`.

### B. Simetria
- Alinhar centro em X = 0.
- Manter **Sculpt Symmetry (X)** ativado.
- Em caso de assimetria, usar `Mesh > Symmetrize (-X to +X)` antes do bake.

---

## 3. Validação Automática Pré-Bake & Pré-Export
Antes de submeter um modelo ou gerar GLB para o cliente Unity/OpenMU:
1. Executar a validação:
   `blender <scene.blend> --background --python tools/validate_rig_symmetry.py`
   - Deve passar com tolerância `<= 0.005m` de simetria.
   - Deve passar sem colisões destrutivas nos frames de `action03` (ataque) e `action04` (rugido).
2. Se falhar em qualquer gate, corrija a malha antes de gerar o run record.

---

## 4. Setup do Estúdio Master de Renderização
Para gerar pranchas de revisão e aprovação visual padronizadas (nível Sketchfab):
- Executar: `blender <scene.blend> --background --python tools/setup_mu_studio.py`
- **Configurações:**
  - Cycles com AgX (Medium High Contrast).
  - Iluminação 3 Pontos (Key quente 5500K, Fill fria 6500K, Rim 600W de recorte).
  - Câmera 85mm com enquadramento proporcional automático.

---

## 5. Gates de Aprovação Humana (`human_gates`)
O run só avança para versão aprovada após passar por:
1. `head_and_mouth_in_motion`: Boca abre e fecha sem furar focinho em todas as ações.
2. `body_wing_tail_silhouette`: Silhueta e proporções fiéis ao MU clássico sob câmera isométrica.
3. `game_camera_materials`: Shaders PBR sem brilho de plástico sob luz neutra.
4. `unity_ingame`: Teste no prefab variante do Unity/OpenMU com TypeId mantido.