"""Tests for long-lived quant runtime worker contract."""

from time import sleep

from quant_runtime.worker import InMemoryJobStore, RuntimeJobWorker


def test_in_memory_job_store_tracks_status_and_result():
    store = InMemoryJobStore()

    job_id = store.submit({"symbol": "RB0909"})
    assert store.status(job_id)["status"] == "queued"

    store.succeed(job_id, {"symbol": "RB0909", "final_equity": 101000.0})

    assert store.status(job_id)["status"] == "succeeded"
    assert store.result(job_id)["result"]["final_equity"] == 101000.0


def test_runtime_job_worker_executes_submitted_payload(tmp_path):
    calls = []

    def fake_execute(payload, minute_data_dir):
        calls.append((payload, minute_data_dir))
        return {"symbol": payload["symbol"], "final_equity": 101000.0}

    worker = RuntimeJobWorker(minute_data_dir=tmp_path, execute=fake_execute)

    submitted = worker.submit({"symbol": "RB0909"})
    for _ in range(50):
        current = worker.status(submitted["job_id"])
        if current["status"] == "succeeded":
            break
        sleep(0.01)

    assert current["status"] == "succeeded"
    assert worker.result(submitted["job_id"])["result"]["final_equity"] == 101000.0
    assert calls == [({"symbol": "RB0909"}, tmp_path)]


def test_runtime_job_worker_reports_runner_errors(tmp_path):
    def fake_execute(payload, minute_data_dir):
        raise ValueError("bad payload")

    worker = RuntimeJobWorker(minute_data_dir=tmp_path, execute=fake_execute)

    submitted = worker.submit({"symbol": "RB0909"})
    for _ in range(50):
        current = worker.status(submitted["job_id"])
        if current["status"] == "failed":
            break
        sleep(0.01)

    assert current["status"] == "failed"
    assert current["error"] == "bad payload"
    assert worker.result(submitted["job_id"])["error"]["detail"] == "bad payload"
