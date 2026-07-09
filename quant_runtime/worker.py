"""Job primitives for a future long-lived quant runtime worker."""

from dataclasses import dataclass
from itertools import count
from typing import Any


@dataclass
class JobRecord:
    job_id: str
    payload: dict[str, Any]
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


class InMemoryJobStore:
    def __init__(self) -> None:
        self._ids = count(1)
        self._records: dict[str, JobRecord] = {}

    def submit(self, payload: dict[str, Any]) -> str:
        job_id = f"job-{next(self._ids)}"
        self._records[job_id] = JobRecord(
            job_id=job_id,
            payload=payload,
            status="queued",
        )
        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        record = self._records[job_id]
        return {"job_id": record.job_id, "status": record.status, "error": record.error}

    def succeed(self, job_id: str, result: dict[str, Any]) -> None:
        record = self._records[job_id]
        record.status = "succeeded"
        record.result = result

    def result(self, job_id: str) -> dict[str, Any]:
        record = self._records[job_id]
        return {"job_id": record.job_id, "result": record.result}
