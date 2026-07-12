from trade_runtime.health import RuntimeHealthSnapshot


def test_runtime_health_is_ready_only_with_process_ctp_and_account_readiness():
    ready = RuntimeHealthSnapshot(
        process_alive=True,
        ctp_connected=True,
        account_ready=True,
    )

    assert ready.status == "READY"


def test_runtime_health_reports_degraded_when_ctp_is_disconnected():
    disconnected = RuntimeHealthSnapshot(
        process_alive=True,
        ctp_connected=False,
        account_ready=False,
    )

    assert disconnected.status == "DEGRADED"


def test_runtime_health_reports_unhealthy_when_the_process_is_not_alive():
    stopped = RuntimeHealthSnapshot(
        process_alive=False,
        ctp_connected=False,
        account_ready=False,
    )

    assert stopped.status == "UNHEALTHY"
