#!/usr/bin/env python3
"""Detect Linux distro characteristics for OpenRC Manager."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(slots=True)
class DistroInfo:
    """Current distribution metadata used by the GUI and backend."""

    name: str
    pretty_name: str
    package_manager: str
    init_dir: Path
    conf_dir: Path
    runlevels_dir: Path
    log_paths: list[str]
    uses_elogind: bool
    special_features: dict


def _parse_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()
            if not line or "=" not in line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            data[key] = value.strip().strip('"')
    return data


def check_elogind() -> bool:
    """Check if elogind appears installed or running."""
    return Path("/run/elogind.pid").exists() or Path("/usr/bin/elogind").exists()


def check_openrc_installed() -> bool:
    """Verify OpenRC CLI tools are available."""
    try:
        result = subprocess.run(
            ["rc-service", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return False
    return result.returncode == 0


def detect_distro() -> DistroInfo:
    """Detect distribution and return normalized information."""

    os_release = _parse_os_release()
    distro_id = os_release.get("ID", "").lower()
    distro_id_like = os_release.get("ID_LIKE", "").lower()
    pretty_name = os_release.get("PRETTY_NAME", "Unknown Linux")

    init_dir = Path("/etc/init.d")
    conf_dir = Path("/etc/conf.d")
    runlevels_dir = Path("/etc/runlevels")

    if distro_id == "gentoo" or "gentoo" in distro_id_like:
        return DistroInfo(
            name="gentoo",
            pretty_name=pretty_name,
            package_manager="portage",
            init_dir=init_dir,
            conf_dir=conf_dir,
            runlevels_dir=runlevels_dir,
            log_paths=["/var/log/rc.log", "/var/log/messages", "/var/log/syslog"],
            uses_elogind=check_elogind(),
            special_features={"slots": True, "use_flags": True},
        )

    if distro_id == "alpine":
        return DistroInfo(
            name="alpine",
            pretty_name=pretty_name,
            package_manager="apk",
            init_dir=init_dir,
            conf_dir=conf_dir,
            runlevels_dir=runlevels_dir,
            log_paths=["/var/log/messages", "/var/log/rc.log"],
            uses_elogind=check_elogind(),
            special_features={"musl": True, "busybox": True},
        )

    if distro_id == "artix" or "artix" in distro_id_like:
        return DistroInfo(
            name="artix",
            pretty_name=pretty_name,
            package_manager="pacman",
            init_dir=init_dir,
            conf_dir=conf_dir,
            runlevels_dir=runlevels_dir,
            log_paths=["/var/log/rc.log", "/var/log/messages"],
            uses_elogind=check_elogind(),
            special_features={"arch_based": True},
        )

    if distro_id == "devuan" or "devuan" in distro_id_like:
        return DistroInfo(
            name="devuan",
            pretty_name=pretty_name,
            package_manager="apt",
            init_dir=init_dir,
            conf_dir=conf_dir,
            runlevels_dir=runlevels_dir,
            log_paths=["/var/log/syslog", "/var/log/messages", "/var/log/daemon.log"],
            uses_elogind=check_elogind(),
            special_features={"debian_based": True},
        )

    if distro_id == "void":
        return DistroInfo(
            name="void",
            pretty_name=pretty_name,
            package_manager="xbps",
            init_dir=init_dir,
            conf_dir=conf_dir,
            runlevels_dir=runlevels_dir,
            log_paths=["/var/log/messages", "/var/log/socklog"],
            uses_elogind=check_elogind(),
            special_features={"socklog": True},
        )

    if distro_id == "strataos" or "fedora" in distro_id_like:
        return DistroInfo(
            name="strataos",
            pretty_name=pretty_name,
            package_manager="dnf",
            init_dir=init_dir,
            conf_dir=conf_dir,
            runlevels_dir=runlevels_dir,
            log_paths=["/var/log/rc.log", "/var/log/messages"],
            uses_elogind=check_elogind(),
            special_features={"selinux": True, "fedora_based": True},
        )

    if distro_id in {"calculate", "funtoo"}:
        return DistroInfo(
            name=distro_id,
            pretty_name=pretty_name,
            package_manager="portage",
            init_dir=init_dir,
            conf_dir=conf_dir,
            runlevels_dir=runlevels_dir,
            log_paths=["/var/log/rc.log", "/var/log/messages"],
            uses_elogind=check_elogind(),
            special_features={"gentoo_based": True},
        )

    return DistroInfo(
        name="unknown",
        pretty_name=pretty_name,
        package_manager="unknown",
        init_dir=init_dir,
        conf_dir=conf_dir,
        runlevels_dir=runlevels_dir,
        log_paths=["/var/log/messages", "/var/log/syslog"],
        uses_elogind=check_elogind(),
        special_features={},
    )


def get_available_runlevels() -> list[str]:
    """Get runlevels present on the host."""
    runlevels_dir = Path("/etc/runlevels")
    if runlevels_dir.exists():
        return sorted(p.name for p in runlevels_dir.iterdir() if p.is_dir())
    return ["sysinit", "boot", "default", "shutdown"]
