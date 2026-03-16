#!/usr/bin/env python3
"""Log reading utilities for OpenRC Manager."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .service_manager import ServiceManager


@dataclass(slots=True)
class LogSource:
    """Resolved log source metadata."""

    path: str
    exists: bool


class LogReader:
    """Provides service log data with distro-aware fallbacks."""

    def __init__(self, manager: ServiceManager):
        self.manager = manager

    def get_logs(self, service_name: str, lines: int = 200) -> str:
        return self.manager.get_logs(service_name, lines=lines)

    def discover_log_sources(self, service_name: str) -> list[LogSource]:
        candidates = [
            f"/var/log/{service_name}.log",
            f"/var/log/{service_name}/{service_name}.log",
            f"/var/log/{service_name}/current",
            *self.manager.distro.log_paths,
        ]
        seen: set[str] = set()
        sources: list[LogSource] = []
        for item in candidates:
            if item in seen:
                continue
            seen.add(item)
            p = Path(item)
            sources.append(LogSource(path=item, exists=p.exists()))
        return sources
