# Environment Report

## Summary

- Recommended mode: `cpu`
- Architecture: `x86_64`
- Python: `3.12.12`
- uv available: `True`
- torch installed: `False`
- torch CUDA available: `False`

## Command Output

### `uname -a`

```text
Linux DESKTOP-Q75GUV0 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
```

### `uname -m`

```text
x86_64
```

### `lsb_release -a || cat /etc/os-release`

```text
Distributor ID:	Ubuntu
Description:	Ubuntu 22.04.5 LTS
Release:	22.04
Codename:	jammy
No LSB modules are available.
```

### `which uv || true`

```text
/home/zhexu/.local/bin/uv
```

### `uv --version || true`

```text
uv 0.9.18
```

### `which python3 || true`

```text
/home/zhexu/privacy-preserving-demo/.venv/bin/python3
```

### `python3 --version || true`

```text
Python 3.12.12
```

### `which nvidia-smi || true`

```text
/usr/lib/wsl/lib/nvidia-smi
```

### `nvidia-smi || true`

```text
Failed to initialize NVML: GPU access blocked by the operating system
Failed to properly shut down NVML: GPU access blocked by the operating system
```

### `which docker || true`

```text
/usr/bin/docker
```

### `docker --version || true`

```text
Docker version 29.2.0, build 0b9d198
```

## Isolation Statement

- The demo uses an isolated project environment.
- This preflight script is read-only and does not modify system configuration.
- GPU remains optional. CPU fallback stays available.
