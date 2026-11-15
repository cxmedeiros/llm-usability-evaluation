from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from usability_eval.schemas import Action, RunRecord, Task


def test_json_round_trip_preserves_execution_and_evaluation(run_record):
    restored = RunRecord.model_validate_json(run_record.model_dump_json())
    assert restored == run_record
    assert restored.execution.steps[0].status == "succeeded"
    assert restored.execution.task_outcome == "failed"
    assert restored.evaluation.issues[0].evidence_ids == [restored.execution.evidence[0].id]


@pytest.mark.parametrize("action", [
    {"kind": "navigate", "url": "http://localhost:8000/"},
    {"kind": "click", "target_id": "button"},
    {"kind": "fill", "target_id": "name", "value": ""},
    {"kind": "select", "target_id": "country", "value": "BR"},
    {"kind": "press", "target_id": "search", "key": "Enter"},
    {"kind": "scroll", "delta_y": 500},
])
def test_supported_browser_actions(action):
    parsed = TypeAdapter(Action).validate_python(action)
    assert parsed.kind == action["kind"]


@pytest.mark.parametrize("action", [
    {"kind": "click"},
    {"kind": "fill", "target_id": "name"},
    {"kind": "navigate", "url": "javascript:alert(1)"},
    {"kind": "execute_python", "code": "print(1)"},
    {"kind": "click", "target_id": "button", "value": "unexpected"},
    {"kind": "scroll", "delta_y": True},
])
def test_rejects_invalid_browser_actions(action):
    with pytest.raises(ValidationError):
        TypeAdapter(Action).validate_python(action)


@pytest.mark.parametrize("field,value", [
    ("instruction", "  "), ("start_url", "not-a-url"), ("success_criteria", []),
])
def test_rejects_incomplete_task(run_record, field, value):
    data = run_record.config.task.model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        Task.model_validate(data)


@pytest.mark.parametrize("case", [
    "unknown_observation", "unknown_target", "unknown_evidence", "duplicate_ids",
    "missing_artifact", "missing_excerpt", "missing_error", "unexpected_error",
    "missing_after", "backwards_time", "naive_time", "extra_field",
])
def test_rejects_inconsistent_records(run_record, case):
    data = run_record.model_dump(mode="json")
    execution = data["execution"]
    step = execution["steps"][0]
    if case == "unknown_observation":
        step["before_observation_id"] = str(uuid4())
    elif case == "unknown_target":
        step["action"]["target_id"] = "missing"
    elif case == "unknown_evidence":
        data["evaluation"]["issues"][0]["evidence_ids"] = [str(uuid4())]
    elif case == "duplicate_ids":
        execution["observations"].append(execution["observations"][0])
    elif case == "missing_artifact":
        execution["evidence"][0]["kind"] = "screenshot"
    elif case == "missing_excerpt":
        execution["evidence"][0]["excerpt"] = None
    elif case == "missing_error":
        step["status"] = "failed"
    elif case == "unexpected_error":
        step["error"] = "timeout"
    elif case == "missing_after":
        step["after_observation_id"] = None
    elif case == "backwards_time":
        step["finished_at"] = "2000-01-01T00:00:00Z"
    elif case == "naive_time":
        data["created_at"] = "2026-11-11T12:00:00"
    elif case == "extra_field":
        data["ground_truth"] = []
    with pytest.raises(ValidationError):
        RunRecord.model_validate(data)


def walkthrough_data(run_record):
    return dict(
        subgoal="Confirmar envio", phase="after_action",
        step_id=str(run_record.execution.steps[0].id), question_id="progress",
        answer="uncertain", rationale="Não há confirmação visível.",
        evidence_ids=[str(run_record.execution.evidence[0].id)],
    )


def test_gendermag_walkthrough_round_trip(run_record):
    data = run_record.model_dump(mode="json")
    data["config"]["strategy"] = dict(
        kind="gendermag", prompt_version="gm-v1", persona_id="persona-test",
        protocol_version="draft-v1",
    )
    data["evaluation"]["walkthrough"] = [walkthrough_data(run_record)]
    record = RunRecord.model_validate(data)
    assert RunRecord.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize("case", ["baseline", "missing_persona", "unknown_step", "missing_step"])
def test_rejects_invalid_walkthrough(run_record, case):
    data = run_record.model_dump(mode="json")
    entry = walkthrough_data(run_record)
    data["evaluation"]["walkthrough"] = [entry]
    if case != "baseline":
        data["config"]["strategy"] = dict(
            kind="gendermag", prompt_version="gm-v1", persona_id="persona-test",
            protocol_version="draft-v1",
        )
    if case == "missing_persona":
        del data["config"]["strategy"]["persona_id"]
    elif case == "unknown_step":
        entry["step_id"] = str(uuid4())
    elif case == "missing_step":
        entry["step_id"] = None
    with pytest.raises(ValidationError):
        RunRecord.model_validate(data)


def test_json_schema_exposes_discriminators():
    schema = RunRecord.model_json_schema()
    assert schema["$defs"]["RunConfig"]["properties"]["strategy"]["discriminator"]["propertyName"] == "kind"
    assert schema["$defs"]["ExecutionStep"]["properties"]["action"]["discriminator"]["propertyName"] == "kind"
