from trade_supervisor.leases import InMemoryLeaseStore


def test_acquiring_a_replacement_runtime_increments_the_fencing_token():
    store = InMemoryLeaseStore()

    first = store.acquire(account_id="account-1", runtime_instance_id="runtime-1")
    replacement = store.acquire(
        account_id="account-1",
        runtime_instance_id="runtime-2",
    )

    assert first.fencing_token == 1
    assert replacement.fencing_token == 2
    assert store.current_token("account-1") == 2


def test_lease_store_rejects_heartbeat_from_replaced_runtime():
    store = InMemoryLeaseStore()
    first = store.acquire(account_id="account-1", runtime_instance_id="runtime-1")
    store.acquire(account_id="account-1", runtime_instance_id="runtime-2")

    assert store.heartbeat(
        account_id="account-1",
        runtime_instance_id="runtime-1",
        fencing_token=first.fencing_token,
    ) is False
