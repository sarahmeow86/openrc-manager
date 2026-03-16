#!/usr/bin/env python3
"""Core OpenRC service management operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import subprocess
from typing import Optional

from .distro_detect import DistroInfo, detect_distro


SERVICE_NAME_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


@dataclass(slots=True)
class Service:
    """Represents an OpenRC service."""

    name: str
    enabled: bool
    runlevels: list[str]
    status: str
    pid: Optional[int] = None
    uptime: Optional[str] = None
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    description: str = ""
    script_path: Optional[Path] = None
    conf_path: Optional[Path] = None


class ServiceManager:
    """Universal OpenRC service management helper."""

    def __init__(self, distro: Optional[DistroInfo] = None):
        self.distro = distro or detect_distro()
        self.init_dir = self.distro.init_dir
        self.conf_dir = self.distro.conf_dir
        self.runlevels_dir = self.distro.runlevels_dir

    @staticmethod
    def _validate_service_name(service_name: str) -> None:
        if not SERVICE_NAME_RE.match(service_name):
            raise ValueError(f"Invalid service name: {service_name!r}")

    @staticmethod
    def _run_command(
        args: list[str],
        timeout: int,
        text: bool = True,
        privileged: bool = False,
    ) -> subprocess.CompletedProcess:
        cmd = list(args)
        if privileged and os.geteuid() != 0:
            cmd = ["pkexec"] + cmd
        return subprocess.run(
            cmd,
            capture_output=True,
            text=text,
            timeout=timeout,
            check=False,
        )

    def get_all_services(self) -> list[Service]:
        """Return all valid OpenRC init scripts as service objects."""
        services: list[Service] = []
        enabled_map = self._get_enabled_services_map()

        if not self.init_dir.exists():
            return services

        for script in sorted(self.init_dir.iterdir(), key=lambda p: p.name):
            if not script.is_file() or script.name.startswith("."):
                continue
            if not self._is_valid_init_script(script):
                continue

            service = self._build_service_object(script, enabled_map)
            if service is not None:
                services.append(service)
        return services

    def _is_valid_init_script(self, script: Path) -> bool:
        try:
            if script.stat().st_mode & 0o111 == 0:
                return False
            with script.open("r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read(2048)
            return (
                "#!/sbin/openrc-run" in content
                or "depend()" in content
                or "start()" in content
            )
        except Exception:
            return False

    def _get_enabled_services_map(self) -> dict[str, list[str]]:
        enabled: dict[str, list[str]] = {}
        try:
            result = self._run_command(["rc-update", "show", "-v"], timeout=10)
        except Exception:
            return enabled

        for line in result.stdout.splitlines():
            if "|" not in line:
                continue
            left, _, right = line.partition("|")
            name = left.strip()
            if not name:
                continue
            runlevels = [item.strip() for item in right.split() if item.strip()]
            enabled[name] = runlevels
        return enabled

    def _build_service_object(
        self,
        script: Path,
        enabled_map: dict[str, list[str]],
    ) -> Optional[Service]:
        name = script.name
        try:
            status = self.get_service_status(name)
            runlevels = enabled_map.get(name, [])
            conf_path = self.conf_dir / name
            if not conf_path.exists():
                conf_path = None
            return Service(
                name=name,
                enabled=bool(runlevels),
                runlevels=runlevels,
                status=status,
                pid=self._get_service_pid(name) if status == "running" else None,
                dependencies=self._parse_dependencies(script),
                description=self._get_description(name),
                script_path=script,
                conf_path=conf_path,
            )
        except Exception:
            return None

    def get_service_status(self, service_name: str) -> str:
        self._validate_service_name(service_name)
        try:
            result = self._run_command(
                ["rc-service", service_name, "status"],
                timeout=5,
            )
            output = (result.stdout + "\n" + result.stderr).lower()
            if "started" in output or "running" in output:
                return "running"
            if "crashed" in output:
                return "crashed"
            if "starting" in output:
                return "starting"
            if "stopping" in output:
                return "stopping"
            if "stopped" in output:
                return "stopped"
            return "unknown"
        except subprocess.TimeoutExpired:
            return "unknown"
        except Exception:
            return "unknown"

    def _parse_dependencies(self, script: Path) -> dict[str, list[str]]:
        deps: dict[str, list[str]] = {
            "need": [],
            "use": [],
            "want": [],
            "before": [],
            "after": [],
            "provide": [],
            "keyword": [],
        }
        try:
            content = script.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"depend\s*\(\s*\)\s*\{([^}]*)\}", content, re.DOTALL)
            if not match:
                return deps
            body = match.group(1)
            for dep_type in deps.keys():
                for dep_line in re.findall(rf"^\s*{dep_type}\s+(.+)$", body, re.MULTILINE):
                    deps[dep_type].extend(dep_line.strip().split())
        except Exception:
            pass
        return deps

    def _get_description(self, service_name: str) -> str:
        self._validate_service_name(service_name)
        try:
            result = self._run_command(
                ["rc-service", service_name, "describe"],
                timeout=5,
            )
            text = result.stdout.strip()
            if text:
                return text
        except Exception:
            pass

        script = self.init_dir / service_name
        try:
            with script.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    line = line.strip()
                    if line.startswith("description="):
                        return line.split("=", 1)[1].strip().strip("\"'")
        except Exception:
            pass
        return service_name

    def _get_service_pid(self, service_name: str) -> Optional[int]:
        self._validate_service_name(service_name)
        candidates = [
            Path(f"/run/{service_name}.pid"),
            Path(f"/run/{service_name}/{service_name}.pid"),
            Path(f"/var/run/{service_name}.pid"),
            Path(f"/var/run/{service_name}/{service_name}.pid"),
        ]
        for pid_path in candidates:
            if not pid_path.exists():
                continue
            try:
                pid = int(pid_path.read_text(encoding="utf-8").strip())
            except Exception:
                continue
            if Path(f"/proc/{pid}").exists():
                return pid
        return None

    def _run_service_command(self, service_name: str, command: str) -> tuple[bool, str]:
        self._validate_service_name(service_name)
        if command not in {"start", "stop", "restart"}:
            return False, f"Unsupported command: {command}"
        try:
            result = self._run_command(
                ["rc-service", service_name, command],
                timeout=60,
                privileged=True,
            )
            message = (result.stdout + "\n" + result.stderr).strip()
            return result.returncode == 0, message
        except subprocess.TimeoutExpired:
            return False, f"Timeout while trying to {command} service"
        except Exception as exc:
            return False, str(exc)

    def start_service(self, service_name: str) -> tuple[bool, str]:
        return self._run_service_command(service_name, "start")

    def stop_service(self, service_name: str) -> tuple[bool, str]:
        return self._run_service_command(service_name, "stop")

    def restart_service(self, service_name: str) -> tuple[bool, str]:
        return self._run_service_command(service_name, "restart")

    def enable_service(self, service_name: str, runlevel: str = "default") -> tuple[bool, str]:
        self._validate_service_name(service_name)
        if not runlevel:
            return False, "Runlevel cannot be empty"
        try:
            result = self._run_command(
                ["rc-update", "add", service_name, runlevel],
                timeout=10,
                privileged=True,
            )
            message = (result.stdout + "\n" + result.stderr).strip()
            return result.returncode == 0, message
        except Exception as exc:
            return False, str(exc)

    def disable_service(self, service_name: str, runlevel: str = "default") -> tuple[bool, str]:
        self._validate_service_name(service_name)
        if not runlevel:
            return False, "Runlevel cannot be empty"
        try:
            result = self._run_command(
                ["rc-update", "del", service_name, runlevel],
                timeout=10,
                privileged=True,
            )
            message = (result.stdout + "\n" + result.stderr).strip()
            return result.returncode == 0, message
        except Exception as exc:
            return False, str(exc)

    def get_available_runlevels(self) -> list[str]:
        runlevels: list[str] = []
        if self.runlevels_dir.exists():
            runlevels = [item.name for item in self.runlevels_dir.iterdir() if item.is_dir()]
        if not runlevels:
            runlevels = ["sysinit", "boot", "default", "shutdown"]
        return sorted(runlevels)

    def get_logs(self, service_name: str, lines: int = 100) -> str:
        self._validate_service_name(service_name)
        lines = max(1, min(lines, 5000))

        service_candidates = [
            f"/var/log/{service_name}.log",
            f"/var/log/{service_name}/{service_name}.log",
            f"/var/log/{service_name}/current",
        ]

        for candidate in service_candidates:
            path = Path(candidate)
            if not path.exists() or not path.is_file():
                continue
            try:
                result = self._run_command(["tail", "-n", str(lines), candidate], timeout=10)
            except Exception:
                continue
            if result.stdout.strip():
                return result.stdout

        for candidate in self.distro.log_paths:
            path = Path(candidate)
            if not path.exists() or not path.is_file():
                continue
            try:
                grep_result = self._run_command(
                    ["grep", "-i", service_name, candidate],
                    timeout=10,
                )
            except Exception:
                continue
            if grep_result.stdout.strip():
                out_lines = grep_result.stdout.strip().splitlines()
                return "\n".join(out_lines[-lines:])

        return f"No logs found for {service_name}"

    def get_service_config(self, service_name: str) -> Optional[str]:
        self._validate_service_name(service_name)
        conf_path = self.conf_dir / service_name
        if conf_path.exists() and conf_path.is_file():
            try:
                return conf_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return None
        return None

    def get_service_details(self, service_name: str) -> dict[str, object]:
        self._validate_service_name(service_name)
        script = self.init_dir / service_name
        deps = self._parse_dependencies(script) if script.exists() else {}
        return {
            "name": service_name,
            "status": self.get_service_status(service_name),
            "description": self._get_description(service_name),
            "runlevels": self._get_enabled_services_map().get(service_name, []),
            "dependencies": deps,
            "config": self.get_service_config(service_name),
            "script_path": str(script),
        }
