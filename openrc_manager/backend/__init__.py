"""Backend helpers for OpenRC Manager."""

from .distro_detect import DistroInfo, check_openrc_installed, detect_distro
from .service_manager import Service, ServiceManager

__all__ = [
    "DistroInfo",
    "Service",
    "ServiceManager",
    "check_openrc_installed",
    "detect_distro",
]
