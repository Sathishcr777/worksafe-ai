"""
WorkSafe AI — System & Hardware Information Collector for Experiment 01.

Collects verified hardware and software environment telemetry for benchmark reproducibility.
Does NOT fabricate metrics when hardware sensors or telemetry are unavailable.
"""

import platform
import sys
import psutil
from typing import Dict, Any, Optional

def get_system_environment() -> Dict[str, Any]:
    """Collects OS, Python, CPU, RAM, and GPU environment details."""
    env: Dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "platform_machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_physical_cores": psutil.cpu_count(logical=False),
        "cpu_logical_cores": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
        "ram_used_percent": psutil.virtual_memory().percent,
    }

    # Detect power profile and battery status
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            env["power_plugged"] = battery.power_plugged
            env["battery_percent"] = battery.percent
            env["power_profile"] = "AC Mains (Turbo Boost)" if battery.power_plugged else "Battery DC (Power Throttled Profile)"
        else:
            env["power_plugged"] = True
            env["battery_percent"] = 100.0
            env["power_profile"] = "AC Mains (Assumed / No Battery Sensor)"
    except Exception:
        env["power_plugged"] = None
        env["battery_percent"] = None
        env["power_profile"] = "Unknown Power Profile"

    # Detect CPU clock frequency
    try:
        freq = psutil.cpu_freq()
        if freq is not None:
            env["cpu_freq_current_mhz"] = round(freq.current, 1)
        else:
            env["cpu_freq_current_mhz"] = None
    except Exception:
        env["cpu_freq_current_mhz"] = None

    # Detect GPU availability via PyTorch if installed
    try:
        import torch
        env["torch_version"] = torch.__version__
        env["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            env["gpu_count"] = torch.cuda.device_count()
            env["gpu_name"] = torch.cuda.get_device_name(0)
            env["cuda_version"] = torch.version.cuda
            props = torch.cuda.get_device_properties(0)
            env["gpu_total_memory_gb"] = round(props.total_memory / (1024 ** 3), 2)
        else:
            env["gpu_name"] = "None (CPU Execution)"
            env["gpu_total_memory_gb"] = 0.0
    except ImportError:
        env["torch_version"] = "Not Installed"
        env["cuda_available"] = False
        env["gpu_name"] = "Torch Not Available"
        env["gpu_total_memory_gb"] = 0.0

    return env


def get_current_resource_usage() -> Dict[str, Any]:
    """Measures current CPU and RAM utilization snapshot."""
    usage: Dict[str, Any] = {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_used_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 2),
    }

    try:
        import torch
        if torch.cuda.is_available():
            usage["gpu_memory_allocated_mb"] = round(torch.cuda.memory_allocated(0) / (1024 ** 2), 2)
            usage["gpu_memory_reserved_mb"] = round(torch.cuda.memory_reserved(0) / (1024 ** 2), 2)
    except Exception:
        pass

    return usage
