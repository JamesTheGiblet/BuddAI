import psutil

def meta():
    """
    Metadata for the System Info skill.
    """
    return {
        "name": "System Info",
        "description": "Reports current CPU and RAM usage.",
        "triggers": ["cpu usage", "ram usage", "memory usage", "system stats", "how much ram", "cpu load"]
    }

def run(payload):
    """
    Fetches system metrics.
    """
    # interval=0.1 ensures we get a fresh sample (blocking briefly)
    cpu_usage = psutil.cpu_percent(interval=0.1)
    
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    used_gb = mem.used / (1024 ** 3)
    percent_used = mem.percent
    
    return (f"🖥️ System Vital Signs:\n"
            f"   🧠 CPU Load: {cpu_usage}%\n"
            f"   💾 RAM Usage: {percent_used}% ({used_gb:.1f}GB / {total_gb:.1f}GB)")