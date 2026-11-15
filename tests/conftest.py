from datetime import datetime, timezone

import pytest

from usability_eval.schemas import (
    BaselineStrategy, ClickAction, Element, EvaluationRecord, Evidence,
    ExecutionRecord, ExecutionStep, Observation, RunConfig, RunRecord, Task,
    UsabilityIssue,
)


@pytest.fixture
def run_record():
    """Dados sintéticos: não representam uma navegação real."""
    now = datetime.now(timezone.utc)
    before = Observation(
        recorded_at=now, url="http://localhost:8000/", title="Cadastro",
        visible_text="Enviar", elements=[Element(id="submit", role="button", name="Enviar")],
    )
    after = Observation(
        recorded_at=now, url="http://localhost:8000/", title="Cadastro", visible_text="Enviar",
    )
    step = ExecutionStep(
        started_at=now, finished_at=now, before_observation_id=before.id,
        after_observation_id=after.id, action=ClickAction(target_id="submit"), status="succeeded",
    )
    evidence = Evidence(
        observation_id=after.id, kind="text", description="Ausência de confirmação visível",
        excerpt="Enviar",
    )
    return RunRecord(
        created_at=now,
        config=RunConfig(
            task=Task(id="register", instruction="Envie o cadastro.",
                      start_url="http://localhost:8000/",
                      success_criteria=["Uma confirmação de envio é exibida."]),
            strategy=BaselineStrategy(prompt_version="baseline-v1"),
        ),
        execution=ExecutionRecord(
            status="completed", task_outcome="failed",
            outcome_reason="Não foi possível confirmar o envio.",
            observations=[before, after], steps=[step], evidence=[evidence],
        ),
        evaluation=EvaluationRecord(
            status="completed", issues=[UsabilityIssue(
                title="Sem confirmação", description="A tela não confirma o envio.",
                location="Formulário de cadastro", expected_impact="Incerteza sobre o resultado.",
                severity="medium", evidence_ids=[evidence.id],
            )],
        ),
    )
