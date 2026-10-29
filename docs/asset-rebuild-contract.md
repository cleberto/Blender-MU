# Contrato reutilizável de reconstrução de assets MU

Este projeto registra cada reconstrução como **fonte imutável → versão → receita → execução → evidência → decisão**. A receita automática reduz trabalho repetido; ela não declara que um modelo é fiel, bonito ou pronto para o jogo. Essa decisão depende dos gates visuais e de integração registrados no próprio asset.

## Dados mínimos por asset

Para cada monstro, item, prop ou efeito, crie uma entrada em `catalog/assets/`, uma versão em `catalog/assets/<tipo>/<slug>/versions/`, um perfil em `profiles/` e uma pasta `work/<slug>/`. O perfil deve conter apenas referências estáveis e parâmetros de execução: fonte, rig/partes móveis quando existirem, LODs, construtor, renderizador, auditor, ações e gates humanos. Valores desconhecidos são `null` ou `unknown`; nunca se inventam valores para completar o perfil.

Use `profiles/asset-profile.template.json` como contrato compacto para tipos que ainda não possuem um motor específico. `profiles/monster03.json` e `schemas/monster-profile.schema.json` são a especialização executável para monstros animados. Itens estáticos e props reutilizam o contrato genérico até receberem um construtor/auditor próprio.

Perfis de superfície usam `schemas/surface-calibration.schema.json`; em um ambiente sem a biblioteca externa de JSON Schema, valide o perfil entregue com `py -3.9 tools/validate_surface_profile.py profiles/monster03.surface.json`.

## Procedimento obrigatório

1. Inventariar os arquivos originais e referências visuais; calcular hashes e registrar ID MU, escala, pivô, texturas, rig e ações.
2. Copiar para uma nova versão de trabalho. Arquivos do cliente, BMD e referências recebidas são somente leitura.
3. Construir uma única hipótese por run: topologia, rig, material, LOD ou exportação. Separar estudos evita que uma mudança de aparência esconda uma alteração estrutural.
4. Gerar evidência reproduzível: comando, versão do Blender, valores efetivos, hashes, fotos/turntable, poses e auditoria.
5. Comparar a hipótese com a fonte. O fingerprint deve separar estrutura (vértices/faces), UV, pesos, ações, imagens empacotadas e nomes de material. Assim uma calibração de shader não é classificada como mudança de geometria.
6. Registrar o resultado em `catalog/runs/`, inclusive uma rejeição. Se a entrega muda materialmente, criar uma nova versão em vez de sobrescrever a anterior.
7. Promover somente após revisão humana de silhueta, movimento, material, LOD e câmera do jogo. Blender é o ambiente atual de validação; Unity continua pendente até que a integração seja habilitada.

## Escopo do motor

O comando `py -3.9 tools/monster_engine.py build profiles/monster03.json` orquestra a receita de um monstro: isola a saída, executa o construtor, audita os dados, gera a prancha de poses e grava proveniência. Outros tipos devem receber adaptadores com a mesma saída (`candidate`, `audit`, `renders`, `provenance`, run de catálogo), e não reutilizar uma regra de malha ou rig sem validação.

Parâmetros que só funcionaram em um asset permanecem no perfil/construtor daquele asset. Uma regra é promovida a receita compartilhada somente depois de evidência em pelo menos outro asset de classe compatível.

## Convenções de evidência

- `work/<slug>/...`: candidatos e renders descartáveis, sempre ligados a um run.
- `catalog/runs/<run-id>.json`: intenção, entradas, passos, parâmetros efetivos, saídas, achados e gates.
- `knowledge/lessons/*.json`: regra curta reutilizável, ligada a evidências concretas e marcada como hipótese ou verificada.
- `docs/`: interpretação humana; deve apontar para JSON/arquivos de evidência, sem substituir o registro de máquina.

O Budge Dragon é o primeiro caso de referência: `M03_BODY_PBR_01` prova uma calibração de material sem tocar em malha, UV, pesos, ações ou texturas; a mandíbula continua um problema de topologia local e não é aprovada pela melhoria de superfície.
