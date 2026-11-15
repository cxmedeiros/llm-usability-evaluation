"""Contratos versionados; não executam navegação nem chamadas a modelos."""

from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Task(Contract):
    id: Text
    instruction: Text
    start_url: HttpUrl
    success_criteria: Annotated[list[Text], Field(min_length=1)]


class BaselineStrategy(Contract):
    kind: Literal["baseline"] = "baseline"
    prompt_version: Text


class GenderMagStrategy(Contract):
    kind: Literal["gendermag"] = "gendermag"
    prompt_version: Text
    persona_id: Text
    protocol_version: Text


Strategy = Annotated[BaselineStrategy | GenderMagStrategy, Field(discriminator="kind")]


class RunConfig(Contract):
    task: Task
    strategy: Strategy
    repetition: Annotated[int, Field(strict=True, ge=1)] = 1
    max_actions: Annotated[int, Field(strict=True, ge=1)] = 30


class NavigateAction(Contract):
    kind: Literal["navigate"] = "navigate"
    url: HttpUrl


class ClickAction(Contract):
    kind: Literal["click"] = "click"
    target_id: Text


class FillAction(Contract):
    kind: Literal["fill"] = "fill"
    target_id: Text
    value: str  # Uma string vazia representa limpar o campo.


class SelectAction(Contract):
    kind: Literal["select"] = "select"
    target_id: Text
    value: Text


class PressAction(Contract):
    kind: Literal["press"] = "press"
    target_id: Text
    key: Text


class ScrollAction(Contract):
    kind: Literal["scroll"] = "scroll"
    delta_y: Annotated[int, Field(strict=True)]


Action = Annotated[
    NavigateAction | ClickAction | FillAction | SelectAction | PressAction | ScrollAction,
    Field(discriminator="kind"),
]


class Element(Contract):
    id: Text
    role: Text
    name: str
    enabled: bool = True


class Observation(Contract):
    id: UUID = Field(default_factory=uuid4)
    recorded_at: AwareDatetime
    url: HttpUrl
    title: str
    visible_text: str
    elements: list[Element] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_elements(self) -> Self:
        ids = [element.id for element in self.elements]
        if len(ids) != len(set(ids)):
            raise ValueError("Element IDs must be unique within an observation")
        return self


class Evidence(Contract):
    id: UUID = Field(default_factory=uuid4)
    observation_id: UUID
    kind: Literal["screenshot", "dom_snapshot", "text", "trace"]
    description: Text
    artifact_path: Text | None = None
    excerpt: Text | None = None

    @model_validator(mode="after")
    def require_content(self) -> Self:
        if self.kind == "text" and self.excerpt is None:
            raise ValueError("Text evidence requires an excerpt")
        if self.kind != "text" and self.artifact_path is None:
            raise ValueError("Artifact evidence requires an artifact_path")
        return self


class ExecutionStep(Contract):
    """Uma tentativa de ação; sucesso da ação não implica sucesso da tarefa."""

    id: UUID = Field(default_factory=uuid4)
    started_at: AwareDatetime
    finished_at: AwareDatetime
    before_observation_id: UUID
    after_observation_id: UUID | None = None
    action: Action
    status: Literal["succeeded", "failed"]
    error: Text | None = None

    @model_validator(mode="after")
    def consistent_result(self) -> Self:
        if self.finished_at < self.started_at:
            raise ValueError("Step finishes before it starts")
        if self.status == "failed" and self.error is None:
            raise ValueError("Failed action requires an error")
        if self.status == "succeeded":
            if self.error is not None or self.after_observation_id is None:
                raise ValueError("Successful action requires an after observation and no error")
        return self


class ExecutionRecord(Contract):
    status: Literal["not_started", "running", "completed", "failed", "limit_reached"]
    task_outcome: Literal["not_assessed", "succeeded", "failed"] = "not_assessed"
    outcome_reason: Text | None = None
    observations: list[Observation] = Field(default_factory=list)
    steps: list[ExecutionStep] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class UsabilityIssue(Contract):
    id: UUID = Field(default_factory=uuid4)
    title: Text
    description: Text
    location: Text
    expected_impact: Text
    severity: Literal["low", "medium", "high"]
    evidence_ids: Annotated[list[UUID], Field(min_length=1)]


class WalkthroughEntry(Contract):
    """Ponto de extensão; o protocolo e suas perguntas serão definidos depois."""

    id: UUID = Field(default_factory=uuid4)
    subgoal: Text
    phase: Literal["subgoal", "before_action", "after_action"]
    step_id: UUID | None = None
    question_id: Text
    answer: Literal["yes", "no", "uncertain"]
    rationale: Text
    evidence_ids: Annotated[list[UUID], Field(min_length=1)]

    @model_validator(mode="after")
    def require_action_reference(self) -> Self:
        if self.phase != "subgoal" and self.step_id is None:
            raise ValueError("Action walkthrough requires a step_id")
        return self


class EvaluationRecord(Contract):
    status: Literal["not_started", "running", "completed", "failed"]
    issues: list[UsabilityIssue] = Field(default_factory=list)
    walkthrough: list[WalkthroughEntry] = Field(default_factory=list)


class RunRecord(Contract):
    schema_version: Literal["1.0"] = "1.0"
    id: UUID = Field(default_factory=uuid4)
    created_at: AwareDatetime
    config: RunConfig
    execution: ExecutionRecord
    evaluation: EvaluationRecord

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        groups = [
            self.execution.observations, self.execution.steps, self.execution.evidence,
            self.evaluation.issues, self.evaluation.walkthrough,
        ]
        for group in groups:
            ids = [item.id for item in group]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate IDs within a record collection")
        observations = {item.id: item for item in self.execution.observations}
        steps = {item.id for item in self.execution.steps}
        evidence = {item.id for item in self.execution.evidence}
        for step in self.execution.steps:
            if step.before_observation_id not in observations:
                raise ValueError("Unknown before observation")
            if step.after_observation_id is not None and step.after_observation_id not in observations:
                raise ValueError("Unknown after observation")
            if hasattr(step.action, "target_id"):
                targets = {e.id for e in observations[step.before_observation_id].elements}
                if step.action.target_id not in targets:
                    raise ValueError("Action target absent from its before observation")
        for item in self.execution.evidence:
            if item.observation_id not in observations:
                raise ValueError("Evidence references an unknown observation")
        for item in [*self.evaluation.issues, *self.evaluation.walkthrough]:
            if not set(item.evidence_ids) <= evidence:
                raise ValueError("Evaluation references unknown evidence")
        for entry in self.evaluation.walkthrough:
            if entry.step_id is not None and entry.step_id not in steps:
                raise ValueError("Walkthrough references an unknown step")
        if self.config.strategy.kind == "baseline" and self.evaluation.walkthrough:
            raise ValueError("Baseline cannot contain a GenderMag walkthrough")
        return self
