"""Executor compartilhado com política de ações injetável; sem avaliação automática."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import TypeAdapter

from usability_eval.browser import BrowserSession
from usability_eval.recording import Recorder
from usability_eval.schemas import (
    Action, EvaluationRecord, ExecutionRecord, ExecutionStep, Observation,
    RunConfig, RunRecord,
)


class ActionPolicy(Protocol):
    def next_action(self, observation: Observation) -> Action | None:
        """Escolhe uma ação com base na observação atual; None encerra a execução."""
        ...


def run(config: RunConfig, policy: ActionPolicy, *, results_dir: Path = Path("results"),
        timeout_ms: int = 5000, headless: bool = True) -> RunRecord:
    record = RunRecord(
        created_at=datetime.now(timezone.utc), config=config,
        execution=ExecutionRecord(status="running"),
        evaluation=EvaluationRecord(status="not_started"),
    )
    recorder = Recorder(results_dir / str(record.id))
    recorder.event("run_started", record)
    execution = record.execution

    def observe(browser: BrowserSession) -> Observation:
        observation = browser.observe()
        execution.observations.append(observation)
        recorder.event("observation", observation)
        evidence = browser.capture(observation, recorder.directory)
        execution.evidence.append(evidence)
        recorder.event("evidence", evidence)
        return observation

    try:
        with BrowserSession(timeout_ms=timeout_ms, headless=headless) as browser:
            current = None
            try:
                browser.navigate(str(config.task.start_url))
                current = observe(browser)
                while True:
                    # A política recebe uma cópia para não alterar as evidências históricas.
                    proposed = policy.next_action(current.model_copy(deep=True))
                    if proposed is None:
                        execution.status = "completed"
                        break
                    if len(execution.steps) >= config.max_actions:
                        execution.status = "limit_reached"
                        break
                    action = TypeAdapter(Action).validate_python(proposed)
                    recorder.event("action_requested", action)
                    if hasattr(action, "target_id") and action.target_id not in {
                        element.id for element in current.elements
                    }:
                        raise ValueError("Policy requested a target absent from the current observation")
                    started_at = datetime.now(timezone.utc)
                    after = None
                    error = None
                    try:
                        browser.execute(action)
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                    try:
                        after = observe(browser)
                    except Exception as exc:
                        error = error or f"Observation failed: {type(exc).__name__}: {exc}"
                    step = ExecutionStep(
                        started_at=started_at, finished_at=datetime.now(timezone.utc),
                        before_observation_id=current.id,
                        after_observation_id=after.id if after else None,
                        action=action, status="failed" if error else "succeeded", error=error,
                    )
                    execution.steps.append(step)
                    recorder.event("execution_step", step)
                    if error:
                        raise RuntimeError(error)
                    current = after
            finally:
                last = execution.observations[-1] if execution.observations else None
                trace = browser.stop_trace(recorder.directory, last)
                if trace is not None:
                    execution.evidence.append(trace)
                    recorder.event("evidence", trace)
    except Exception as exc:
        execution.status = "failed"
        execution.outcome_reason = f"{type(exc).__name__}: {exc}"
        recorder.event("execution_error", {"error": execution.outcome_reason})
    # Encerrar o roteiro não verifica os critérios da tarefa nem avalia usabilidade.
    recorder.event("execution_finished", execution)
    return recorder.save(record)
