"""Tests for long-lived quant runtime worker contract."""

from quant_runtime.worker import InMemoryJobStore


def test_in_memory_job_store_tracks_status_and_result():
    store = InMemoryJobStore()

    job_id = store.submit({"symbol": "RB0909"})
    assert store.status(job_id)["status"] == "queued"

    store.succeed(job_id, {"symbol": "RB0909", "final_equity": 101000.0})

    assert store.status(job_id)["status"] == "succeeded"
    assert store.result(job_id)["result"]["final_equity"] == 101000.0
