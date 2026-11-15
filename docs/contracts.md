# Contratos de dados — versão 1.0

O módulo `usability_eval.schemas` contém contratos Pydantic. A navegação e a
persistência ficam nos módulos separados descritos em [execução](execution.md).
Os testes de contratos usam dados sintéticos; testes de integração separados
verificam a navegação real. Ainda não há integração com modelos.

## Responsabilidades

| Contrato | Uso |
| --- | --- |
| `Task` | Instrução, URL inicial e critérios observáveis de sucesso. |
| `RunConfig` | Tarefa, estratégia, repetição e limite de ações. |
| `Action` | União discriminada por `kind`: navegar, clicar, preencher, selecionar, pressionar tecla e rolar. |
| `Observation` / `Element` | Estado visível da página e elementos disponíveis para interação. |
| `ExecutionStep` | Ação tentada, observações anterior/posterior, horários, resultado técnico e erro. |
| `Evidence` | Trecho de texto ou caminho para captura, snapshot DOM ou trace, vinculado a uma observação. |
| `ExecutionRecord` | Observações, ações, evidências e resultado da tarefa. |
| `UsabilityIssue` | Problema, localização, impacto esperado, severidade e evidências. |
| `WalkthroughEntry` | Subobjetivo, fase, pergunta, resposta e justificativa do walkthrough futuro. |
| `EvaluationRecord` | Problemas e walkthrough, com status independente da execução. |
| `RunRecord` | Agrega a execução e a avaliação, validando as referências entre elas. |

Um clique bem-sucedido não significa que a tarefa foi concluída. `steps[].status`
registra o resultado técnico da ação; `task_outcome` registra o resultado da tarefa.
`execution.status=completed` significa que a execução terminou normalmente, mesmo
quando a tarefa falhou. A avaliação pode continuar em andamento após esse término.
`outcome_reason` permite explicar a decisão; a verificação dos critérios de sucesso
será responsabilidade do executor/analisador futuro.

Os IDs de elementos são locais a cada observação. O adaptador de navegador
mantém o mapeamento entre esses IDs e elementos reais. O contrato não define
seletores CSS nem executa comandos. Cada passo registra uma tentativa; novas
tentativas devem gerar novos passos.

As evidências são dados observados; os problemas são interpretações desses dados.
Um trace pode ser vinculado à observação de referência embora abranja mais passos.
Os caminhos dos artefatos serão relativos à pasta da execução, por convenção. Sua
existência e seu conteúdo não são verificados pelos contratos.

## GenderMag

`GenderMagStrategy` exige identificadores da persona, da versão do prompt e do
protocolo. `WalkthroughEntry` é um ponto de extensão, não uma implementação ou
validação metodológica do GenderMag. O catálogo de perguntas e a definição das
personas serão adicionados posteriormente. Entradas relacionadas a ações exigem
`step_id`; entradas sobre subobjetivos podem existir antes de qualquer ação.
Baseline não aceita registros de walkthrough. GenderMag aceita uma lista vazia,
inclusive para representar execuções ainda sem avaliação.

## Serialização e validação

```python
from pathlib import Path
from usability_eval.schemas import RunRecord

# `record` é um RunRecord montado com os dados coletados.
# Path("run.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
record = RunRecord.model_validate_json(Path("run.json").read_text(encoding="utf-8"))
schema = RunRecord.model_json_schema()
```

Datas exigem fuso horário; URLs aceitam HTTP/HTTPS, incluindo localhost. Campos
desconhecidos são rejeitados. O agregado rejeita IDs duplicados em cada coleção,
referências inexistentes e ações direcionadas a elementos ausentes da observação.
O JSON Schema descreve os campos, mas as regras cruzadas dos validadores exigem
validação com `RunRecord`.

Modelos e listas são mutáveis: valide novamente o agregado após alterações e antes
de gravar. `model_copy(update=...)` não substitui essa validação. UUIDs identificam
registros, mas não garantem integridade dos arquivos de evidência.

Problemas conhecidos ficam fora desses contratos e não devem ser incluídos no
contexto do agente. A separação de acesso será implementada junto ao executor.
