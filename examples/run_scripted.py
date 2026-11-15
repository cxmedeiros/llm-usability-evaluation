"""Abre uma URL e, opcionalmente, clica uma vez em um botão pelo nome observado."""

import argparse
from pathlib import Path

from usability_eval.runner import run
from usability_eval.schemas import BaselineStrategy, ClickAction, Observation, RunConfig, Task


class ClickOnce:
    def __init__(self, button_name: str | None):
        self.button_name = button_name
        self.finished = False

    def next_action(self, observation: Observation):
        if self.finished or self.button_name is None:
            return None
        matches = [element for element in observation.elements
                   if element.role == "button" and element.name == self.button_name]
        if len(matches) != 1:
            raise ValueError(f"Esperado um botão chamado {self.button_name!r}; encontrados {len(matches)}")
        self.finished = True
        return ClickAction(target_id=matches[0].id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--click", help="Nome exato de um botão para clicar uma vez")
    parser.add_argument("--headed", action="store_true", help="Mostrar janela do Chromium")
    args = parser.parse_args()
    config = RunConfig(
        task=Task(
            id="manual-smoke", start_url=args.url,
            instruction=f"Clicar em {args.click}." if args.click else "Abrir a página e observar.",
            success_criteria=["Verificação manual posterior; não implementada neste exemplo."],
        ),
        strategy=BaselineStrategy(prompt_version="scripted-smoke-v1"),
    )
    record = run(config, ClickOnce(args.click), headless=not args.headed)
    print(f"Execução: {record.execution.status}")
    print(f"Registro: {Path('results') / str(record.id) / 'run.json'}")
    if record.execution.outcome_reason:
        print(record.execution.outcome_reason)
    if record.execution.status == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
