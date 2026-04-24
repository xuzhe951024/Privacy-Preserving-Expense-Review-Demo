# Environment Report

## Summary

- Recommended mode: `gpu_default`
- Architecture: `x86_64`
- Python: `3.12.12`
- uv available: `True`
- torch installed: `True`
- torch CUDA available: `True`
- resolved runtime device: `cuda`
- GLiNER installed: `True`

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
Fri Apr 24 16:08:25 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01              Driver Version: 591.59         CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5090        On  |   00000000:01:00.0  On |                  N/A |
|  0%   38C    P8             13W /  575W |    2788MiB /  32607MiB |      1%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A             466      C   /node                                 N/A      |
+-----------------------------------------------------------------------------------------+
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
- The default runtime is GPU-first when CUDA is available. CPU fallback stays available.
