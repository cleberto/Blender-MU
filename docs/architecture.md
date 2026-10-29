# Arquitetura do laboratório de assets MU

## Objetivo e modelo de informação

Um **asset** é uma identidade lógica estável (`mu:<tipo>:<slug>`). Uma **versão** é um resultado candidato ou aprovado, com parâmetros efetivos e artefatos imutáveis. Uma **execução** é uma tentativa concreta, inclusive quando falha. Uma **receita** define etapas e gates reaproveitáveis. Uma **lição** registra conhecimento transferível com evidência. O vínculo é `asset → versões → execuções`; versões também apontam para a receita, artefatos e decisões. Um shader/material pode ser um asset próprio e aparecer como dependência de um monstro ou item.

Arquivos JSON são a fonte estruturada. Os schemas em `schemas/` definem o contrato; `tools/registry.py validate` verifica integridade, caminhos, hashes e relações sem dependências externas. Markdown explica o porquê e os procedimentos longos. Não usar XML aqui: a estrutura é simples, JSON tem menos marcação e permite validação direta. Essa é uma decisão de projeto, não uma propriedade universal de consumo de tokens.

```text
AGENTS.md / CLAUDE.md       entrada curta para agentes
catalog/assets/<tipo>/<slug>/asset.json
catalog/assets/<tipo>/<slug>/versions/v0001.json
catalog/runs/<run-id>.json  tentativa, parâmetros e evidência
recipes/*.json             etapas, defaults e gates por fluxo
knowledge/lessons/*.json   aprendizado, escopo e proveniência
schemas/*.schema.json      contrato de dados
assets/original/            cópias verificadas das fontes legadas
vendor/                     snapshots das ferramentas externas necessárias
models/                    modelos de referência recebidos
docs/                      análise e procedimentos legíveis
```

## Identidade, versão e proveniência

- ID lógico não muda quando a geometria muda. Use o número do cliente quando conhecido (`mu:monster:monster03`); para itens e objetos, use o identificador de arquivo/categoria, e para conteúdo novo um slug estável. Nome visual e localização no mapa não são chaves.
- `v0001`, `v0002` etc. representam entregáveis. `parent_version` forma a linhagem. Uma tentativa descartada ainda fica em `catalog/runs/`; não precisa virar versão final, mas pode ser ligada a uma versão candidata.
- `status` distingue `reference`, `draft`, `review`, `approved` e `rejected`. `reference` significa material herdado ainda não aprovado para este laboratório. Não inferir qualidade pelo nome `hd`.
- `quality.required` vem da receita escolhida; `quality.results` guarda o resultado final de cada gate com evidência e run de origem. Runs antigos podem registrar falhas, mas a aprovação exige um resultado `pass` documentado para cada gate da versão. O `review` humano é requisito adicional.
- Modelos herdados têm `recipe: null` porque a receita local não os produziu. O manifesto antigo permanece em `parameters.source_manifest`; a receita local passa a valer apenas numa versão nova que realmente a execute.
- Cada arquivo relevante tem caminho relativo e SHA-256. Arquivos grandes podem ficar fora do repositório no futuro, mas o registro precisa de URI estável, hash e regra de recuperação. Um caminho `E:\...` é apenas dica de origem, nunca a única cópia reproduzível.
- Valores de parâmetros são o **snapshot efetivo** da execução/versão, não só defaults herdados. A receita guarda defaults; a versão registra overrides e o identificador/hash da receita usada. Registre semente, modelo/serviço e revisão dos pesos quando aplicável.
- Um `draft` recém-criado separa `parameters.baseline` de `parameters.planned_overrides`; antes de produzir artefatos, o agente resolve isso em parâmetros efetivos no run. Ao fechar a versão, troca o bloco provisório pelo snapshot efetivo. Nunca tratar parâmetros herdados como fatos da nova execução.
- Um run registra data ISO 8601, agente/ferramenta, ambiente, inputs, comandos, outputs, métricas, observações e decisão. Não registrar tokens, senhas ou dados de conta. Run concluído não é reescrito para ocultar falha; uma repetição ganha outro ID.

## Fluxo de trabalho

1. `list`/`show`: localizar a identidade antes de criar algo. Se houver versão, ler defeitos e lições ligadas.
2. Criar versão `draft` a partir da versão-base e abrir um run. Registrar hipótese, objetivo e parâmetros antes do trabalho caro.
3. Produzir e salvar artefatos por versão/run, com hashes. Anotar o que realmente foi executado e o que ficou indisponível.
4. Aplicar gates técnicos automatizados e revisão visual na escala e câmera de uso. Falha permanece registrada; decisão humana é anexada com motivo e evidência.
5. Fechar run; promover versão a `review`/`approved` somente com evidências. Atualizar `current_version` do asset apenas para a versão escolhida, preservando as anteriores.
6. Se o achado for reutilizável, criar/atualizar uma lição e vinculá-la à execução. Revisar defaults da receita em nova revisão, sem mudar silenciosamente runs antigos.

Comandos: `py -3.9 tools/registry.py list --query dragao`, `show mu:monster:monster03 --version v0002`, `new-asset item sword_01 "Sword 01" --mu-id 01`, `new-version mu:monster:monster03 --goal "..."`, `new-run mu:monster:monster03 v0002 --stage geometry --goal "..."`, `validate`. O CLI cria modelos de registro; o agente completa os fatos e evidências. O validador recusa caminhos ausentes, hashes incorretos, relações quebradas e versões aprovadas sem revisão.

## Qualidade por domínio

O destino de validação do Budge Dragon é o cliente Unity/OpenMU (`docs/dragon-v2-readiness.md`). O cliente já tem conversão BMD→assets nativos; uma variante HD deve ser integrada e medida lado a lado, sem sobrescrever o prefab original. As validações de outro cliente descritas no pacote recebido são histórico e não aprovam o asset na Unity.

Gates comuns: identidade, origem verificável, topologia adequada, escala/eixos/pivô, textura/material, custo em jogo, versão do Blender/exportador, licença/proveniência, comparação com referência e evidência visual. Monstros/NPCs exigem rig, deformação, ações e efeitos. Itens exigem empunhadura/socket, silhueta e variações. Cenários/mapas exigem colisão, UV, iluminação e repetição. Shaders exigem compatibilidade de renderizador, fidelidade de cor, custo e imagens de comparação. `recipes/monster-hd-v1.json` inicia um fluxo; receitas de outros domínios serão criadas quando o primeiro caso real for auditado, em vez de fingir parâmetros universais.

## Contexto para agentes e economia de leitura

`AGENTS.md` e `CLAUDE.md` são roteadores curtos. O agente consulta `list`, carrega só um asset, sua versão, sua receita e as lições aplicáveis. Documentos herdados extensos são referências sob demanda. Campos estruturados curtos servem para busca e validação; o motivo de escolhas estéticas e falhas complexas fica em notas Markdown ligadas por caminho. Evitar repetir a mesma instrução em cinco lugares.

Referências externas que orientaram esta organização: [OpenAI Docs: AGENTS.md e contexto por fase](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex), [OpenAI Docs: instruções curtas e divulgação progressiva](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra), [Claude Code: memória de projeto](https://code.claude.com/docs/en/memory), [JSON Schema 2020-12](https://json-schema.org/understanding-json-schema/reference/schema). A estrutura e os campos deste laboratório são decisões locais.
