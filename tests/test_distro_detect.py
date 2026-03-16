from openrc_manager.backend.distro_detect import DistroInfo, detect_distro, get_available_runlevels


def test_detect_distro_returns_info():
    info = detect_distro()
    assert isinstance(info, DistroInfo)
    assert info.init_dir.as_posix() == "/etc/init.d"
    assert isinstance(info.log_paths, list)


def test_runlevels_is_list():
    runlevels = get_available_runlevels()
    assert isinstance(runlevels, list)
    assert len(runlevels) >= 1
