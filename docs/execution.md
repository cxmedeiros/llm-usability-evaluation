# Execução com navegador — segundo incremento

O sistema abre um Chromium local, observa a página e executa ações escolhidas por
uma política Python. Ainda não usa LLMs nem avalia usabilidade. A mesma função
`run` recebe configurações baseline e GenderMag; essas estratégias são metadados
neste incremento e ainda não alteram a política.

## Preparação e validação

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
python -m playwright install chromium
python -m pytest
```

Os testes marcados `browser` precisam do Chromium instalado e de permissão para
abrir processos e um servidor HTTP em loopback. Eles usam páginas mínimas
temporárias, sem serviços externos nem interfaces experimentais do TCC. Não são
ignorados automaticamente quando falta o navegador: uma falha deve ser visível.
Para rodar apenas os testes sem navegador, use `python -m pytest -m 'not browser'`.
Em Linux, a instalação pode exigir bibliotecas de sistema adicionais conforme a
[documentação do Playwright](https://playwright.dev/python/docs/browsers).

## Exemplo manual

Com uma aplicação local já iniciada:

```bash
python examples/run_scripted.py http://localhost:8000/
python examples/run_scripted.py http://localhost:8000/ --click Enviar --headed
```

O primeiro comando apenas observa. O segundo busca um botão de nome exato
`Enviar` na observação e clica uma vez. O exemplo falha explicitamente se houver
zero ou vários botões correspondentes. Use dados de teste: o clique executa a
interação real da aplicação.

## Fluxo e responsabilidades

- `browser.py`: contexto isolado, viewport 1280×720, locale pt-BR, navegação,
  observações, ações, screenshots e trace.
- `runner.py`: ciclo observar → consultar política → executar → registrar, com
  limite de ações e interrupção na primeira falha.
- `recording.py`: grava eventos incrementais e um agregado validado ao terminar.
- `ActionPolicy.next_action(observation)`: recebe uma cópia da observação e devolve
  um dos contratos de ação ou `None` para encerrar. Uma política pode manter seu
  próprio histórico. Uma política nova deve ser criada para cada execução.

A abertura da URL inicial é preparação da sessão, não conta no limite de ações.
Navegações solicitadas pela política contam e geram passos normalmente. Quando a
política retorna `None`, a execução fica `completed`; se pede outra ação após o
limite, fica `limit_reached`. Um erro fica `failed`, com motivo registrado. Uma
ação sobre alvo inexistente é rejeitada antes da execução e aparece nos eventos,
sem gerar um passo com referência inválida.

Cada execução produz uma pasta nova, identificada por UUID:

```text
results/<run-id>/
├── run.json
├── events.jsonl
├── screenshots/<observation-id>.png
└── trace.zip
```

`action_requested` é gravado antes de executar a ação e `execution_step` após a
tentativa. Uma captura representa o viewport; o trace guarda mais detalhes da
sessão e pode ser aberto com `python -m playwright show-trace <caminho>/trace.zip`.
Se a navegação inicial falhar, pode existir trace sem observação à qual vinculá-lo.
Se o próprio navegador não iniciar, não haverá trace. Falhas de disco e término
forçado do processo podem impedir o agregado final; não há recuperação automática.

Nenhuma dessas saídas comprova sucesso da tarefa. `task_outcome` permanece
`not_assessed` e `evaluation.status` permanece `not_started`. Problemas e walkthrough
ficam vazios até a implementação da avaliação correspondente.

## Limites desta versão

A observação usa texto renderizado e controles visíveis do documento principal,
incluindo controles fora do viewport que podem ser alcançados por rolagem.
O nome dos elementos é uma aproximação baseada em labels e atributos; não é uma
implementação completa da árvore de acessibilidade. Não cobre iframes, múltiplas
abas, seletores customizados ou estratégias para aguardar estados assíncronos
específicos da aplicação. O carregamento inicial aguarda `DOMContentLoaded`;
não há espera arbitrária nem garantia de que toda atualização tardia já terminou.

Os IDs `e0`, `e1`, etc. valem somente para a observação atual. O adaptador mantém
handles para os nós exatos que observou: se um controle for removido por uma
atualização, a ação falha em vez de atingir outro elemento pela posição. Essa
escolha é deliberada apesar da preferência geral do Playwright por locators.
Handles são descartados na observação seguinte e o navegador é fechado ao sair.

O contexto isola cookies e armazenamento no navegador, mas não restaura dados do
servidor da aplicação. Restaurar o estado das interfaces será necessário antes
dos experimentos. O adaptador não lê o catálogo de problemas conhecidos, mas ainda
não existe isolamento de processo para políticas Python arbitrárias. Nenhuma
política deve receber acesso ao ground truth no futuro.
