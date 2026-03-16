from openrc_manager.backend.service_manager import ServiceManager


def test_manager_runlevels_fallback():
    manager = ServiceManager()
    runlevels = manager.get_available_runlevels()
    assert isinstance(runlevels, list)
    assert "default" in runlevels or len(runlevels) > 0


def test_get_all_services_returns_list():
    manager = ServiceManager()
    services = manager.get_all_services()
    assert isinstance(services, list)
