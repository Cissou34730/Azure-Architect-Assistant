from app.ingestion.application.shutdown_manager import ShutdownManager


def test_shutdown_manager_job_specific_shutdown_is_isolated() -> None:
    manager = ShutdownManager()

    event_a = manager.register_job("job-a")
    event_b = manager.register_job("job-b")

    assert event_a.is_set() is False
    assert event_b.is_set() is False

    manager.request_shutdown("job-a")

    assert event_a.is_set() is True
    assert event_b.is_set() is False


def test_shutdown_manager_global_shutdown_sets_all_events() -> None:
    manager = ShutdownManager()

    event_a = manager.register_job("job-a")
    event_b = manager.register_job("job-b")

    manager.request_shutdown()

    assert event_a.is_set() is True
    assert event_b.is_set() is True


def test_shutdown_manager_unregister_removes_job() -> None:
    manager = ShutdownManager()

    event_a = manager.register_job("job-a")
    manager.unregister_job("job-a")

    manager.request_shutdown("job-a")

    assert event_a.is_set() is False
