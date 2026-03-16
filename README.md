# OpenRC Service Manager

Universal GTK4 GUI for managing OpenRC services on Gentoo, Alpine, Artix, Devuan, Void (OpenRC), StrataOS, Calculate, and Funtoo.

## Features

- List services from `/etc/init.d`
- Show service status (running, stopped, crashed)
- Display enabled runlevels
- Start, stop, restart services
- Enable/disable services per runlevel
- View dependencies and config details
- Search and filter services
- View service logs
- Distro detection with path and log adaptation
- Privileged actions via `pkexec`

## Requirements

- Python 3.9+
- OpenRC (`rc-service`, `rc-update`, `rc-status`)
- GTK4 + PyGObject
- libadwaita (optional but recommended)

## Install (development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Run

```bash
openrc-manager
```

Or:

```bash
python -m openrc_manager
```

## Tests

```bash
python -m pytest tests/
```

## Security notes

- The app only executes fixed OpenRC commands.
- Service names are validated against a strict allowlist pattern.
- Mutating operations are performed with `pkexec` when not running as root.

## Supported distributions

- Gentoo, Calculate, Funtoo
- Alpine
- Artix
- Devuan
- Void (with OpenRC)
- StrataOS

Unknown OpenRC distros are supported through generic fallback detection.
