"""Persistência local: eventos incrementais e agregado validado ao encerrar."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from usability_eval.schemas import RunRecord


class Recorder:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=False)

    def event(self, kind: str, payload: BaseModel | dict):
        data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        event = {"kind": kind, "recorded_at": datetime.now(timezone.utc).isoformat(), "data": data}
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    def save(self, record: RunRecord) -> RunRecord:
        validated = RunRecord.model_validate_json(record.model_dump_json())
        temporary = self.directory / "run.json.tmp"
        temporary.write_text(validated.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(self.directory / "run.json")
        return validated
