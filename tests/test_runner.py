"""Integração: Chromium real sobre páginas mínimas servidas somente nos testes."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread

import pytest

from usability_eval.runner import run
from usability_eval.schemas import (
    BaselineStrategy, ClickAction, FillAction, GenderMagStrategy, NavigateAction,
    PressAction, RunConfig, RunRecord, ScrollAction, SelectAction, Task,
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def local_site(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("""<!doctype html><html lang="pt-BR">
      <meta charset="utf-8"><title>Teste de navegação</title>
      <body><label>Nome <input id="name"></label>
      <label for="course">Curso</label><select id="course"><option value="cc">Computação</option>
        <option value="si">Sistemas</option></select>
      <button onclick="document.querySelector('#result').textContent =
        'Enviado: ' + document.querySelector('#name').value + ' / ' +
        document.querySelector('#course').value">Enviar</button>
      <button disabled>Indisponível</button><button hidden>Oculto</button>
      <p id="result"></p>
      <button onclick="localStorage.setItem('saved', 'sim'); location.href='/next.html'">Avançar</button>
      <div style="height:1800px"></div><p>Fim</p></body></html>""", encoding="utf-8")
    (site / "next.html").write_text("""<!doctype html><meta charset="utf-8"><title>Destino</title>
      <body><p>Próxima página</p><script>
      document.body.append(localStorage.getItem('saved') || 'sem estado');
      </script></body>""", encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def config(url, **kwargs):
    return RunConfig(
        task=Task(id="smoke", instruction="Preencha e envie o formulário.",
                  start_url=url, success_criteria=["Confirmação visível."]),
        strategy=BaselineStrategy(prompt_version="scripted-test-v1"), **kwargs,
    )


class ScriptedPolicy:
    """Os alvos são escolhidos na observação atual, sem IDs pré-fixados."""

    def __init__(self, steps):
        self.steps = iter(steps)

    def next_action(self, observation):
        step = next(self.steps, None)
        return step(observation) if step else None


def target(observation, name):
    return next(element.id for element in observation.elements if element.name == name)


@pytest.mark.browser
def test_real_form_interaction_and_saved_evidence(local_site, tmp_path):
    policy = ScriptedPolicy([
        lambda obs: FillAction(target_id=target(obs, "Nome"), value="Pessoa teste"),
        lambda obs: SelectAction(target_id=target(obs, "Curso"), value="si"),
        lambda obs: PressAction(target_id=target(obs, "Nome"), key="Tab"),
        lambda obs: ClickAction(target_id=target(obs, "Enviar")),
        lambda obs: ScrollAction(delta_y=500),
    ])
    record = run(config(local_site), policy, results_dir=tmp_path / "results")
    assert record.execution.status == "completed", record.execution.outcome_reason
    assert len(record.execution.steps) == 5
    assert all(step.status == "succeeded" for step in record.execution.steps)
    assert "Enviado: Pessoa teste / si" in record.execution.observations[-1].visible_text
    assert record.execution.task_outcome == "not_assessed"
    assert record.evaluation.status == "not_started"
    assert record.evaluation.issues == []
    assert "Oculto" not in [e.name for e in record.execution.observations[0].elements]
    directory = tmp_path / "results" / str(record.id)
    restored = RunRecord.model_validate_json((directory / "run.json").read_text())
    assert restored == record
    for evidence in record.execution.evidence:
        artifact = directory / evidence.artifact_path
        assert artifact.stat().st_size > 0
        if evidence.kind == "screenshot":
            assert artifact.read_bytes().startswith(b"\x89PNG")
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    assert len([event for event in events if event["kind"] == "action_requested"]) == 5
    assert events[-1]["kind"] == "execution_finished"


@pytest.mark.browser
def test_action_failure_is_recorded(local_site, tmp_path):
    policy = ScriptedPolicy([lambda obs: ClickAction(target_id=target(obs, "Indisponível"))])
    record = run(config(local_site), policy, results_dir=tmp_path / "results", timeout_ms=300)
    assert record.execution.status == "failed"
    assert record.execution.steps[0].status == "failed"
    assert "Timeout" in record.execution.steps[0].error
    assert record.execution.task_outcome == "not_assessed"
    assert (tmp_path / "results" / str(record.id) / "run.json").exists()


@pytest.mark.browser
def test_action_limit(local_site, tmp_path):
    policy = ScriptedPolicy([lambda obs: ScrollAction(delta_y=10)] * 3)
    record = run(config(local_site, max_actions=1), policy, results_dir=tmp_path / "results")
    assert record.execution.status == "limit_reached"
    assert len(record.execution.steps) == 1


@pytest.mark.browser
def test_navigation_and_session_isolation(local_site, tmp_path):
    first = run(config(local_site), ScriptedPolicy([
        lambda obs: ClickAction(target_id=target(obs, "Avançar")),
        lambda obs: NavigateAction(url=local_site),
    ]), results_dir=tmp_path / "results")
    assert first.execution.status == "completed", first.execution.outcome_reason
    assert "Próxima página" in first.execution.observations[1].visible_text
    assert "sim" in first.execution.observations[1].visible_text
    second = run(config(local_site + "next.html"), ScriptedPolicy([]),
                 results_dir=tmp_path / "results")
    assert second.execution.status == "completed", second.execution.outcome_reason
    assert "sem estado" in second.execution.observations[0].visible_text
    assert first.id != second.id


@pytest.mark.browser
def test_gendermag_uses_same_runner_without_claiming_evaluation(local_site, tmp_path):
    settings = config(local_site)
    settings.strategy = GenderMagStrategy(
        persona_id="test", prompt_version="test", protocol_version="not-implemented",
    )
    record = run(settings, ScriptedPolicy([]), results_dir=tmp_path / "results")
    assert record.execution.status == "completed", record.execution.outcome_reason
    assert record.evaluation.status == "not_started"
    assert record.evaluation.walkthrough == []


@pytest.mark.browser
def test_initial_navigation_failure_still_saves_record(local_site, tmp_path):
    record = run(config(local_site + "missing.html"), ScriptedPolicy([]),
                 results_dir=tmp_path / "results")
    assert record.execution.status == "failed"
    assert "HTTP 404" in record.execution.outcome_reason
    assert record.execution.observations == []
    assert (tmp_path / "results" / str(record.id) / "run.json").exists()


@pytest.mark.browser
def test_invalid_policy_target_is_rejected_and_logged(local_site, tmp_path):
    record = run(config(local_site), ScriptedPolicy([
        lambda obs: ClickAction(target_id="missing"),
    ]), results_dir=tmp_path / "results")
    assert record.execution.status == "failed"
    assert "absent" in record.execution.outcome_reason
    assert record.execution.steps == []
    events = (tmp_path / "results" / str(record.id) / "events.jsonl").read_text()
    assert '"kind": "action_requested"' in events
