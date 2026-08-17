#!/usr/bin/python3
import subprocess
import re
import time

# ========== НАСТРОЙТЕ ЭТИ ПАРАМЕТРЫ ==========
REMOTE_USER = "sm"
REMOTE_HOST = "35.240.44.85"
COMPOSE_PATH = "/home/sm/PycharmProjects/ml-triton/docker-compose.yml"
LOCAL_UI_PORT = 8090
LOCAL_API_PORT = 8080
# =============================================

def run(cmd):
    ssh = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", cmd]
    try:
        return subprocess.run(ssh, capture_output=True, text=True, check=True).stdout.strip()
    except:
        return None

def run_local(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True).stdout.strip()
    except:
        return None

def status(name):
    s = run(f"docker inspect -f '{{{{.State.Status}}}}' {name} 2>/dev/null")
    return "✅" if s == "running" else "❌"
    
def last_log_time(name):
    raw = run(f"docker logs --tail 1 {name} 2>&1")
    if raw:
        match = re.search(r'\b(\d{2}:\d{2}):\d{2}', raw)
        if match:
            return match.group(1)
    return "N/A"

def gpu_mem():
    used = run("nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits")
    total = run("nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits")
    if used and total:
        try:
            return f"{int(used)}/{int(total)}MiB ({int(int(used)/int(total)*100)}%)"
        except:
            pass
    return "N/A"

# ---------- Управление портами ----------
def port_status():
    out = run("/home/sm/port-forward.sh status") or ""
    k_status = "✅" if ("ui: running" in out and "api: running" in out) else "❌"
    
    def port_open(p):
        return subprocess.run(f"ss -lnt | grep -q ':{p} '", shell=True, capture_output=True).returncode == 0
    
    s_status = "✅" if (port_open(LOCAL_UI_PORT) and port_open(LOCAL_API_PORT)) else "❌"
    return k_status, s_status
    
# ---------- Основное меню ----------
t_state = status("triton")
m_state = status("ml_triton")
m_log = last_log_time("ml_triton") if m_state != "not found" else ""
gpu = gpu_mem()
k_status, s_status = port_status()

print(f"Triton: {t_state}  ml-triton: {m_state}")
print("---")

print(f"Triton: {t_state} {gpu}")
print(f"-- Run GPU | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"docker run --rm --name triton --gpus=all --shm-size=3g -p8000:8000 -p8001:8001 -p8002:8002 -v /data:/data nvcr.io/nvidia/tritonserver:23.07-py3 tritonserver --model-repository=/data/models/common/model_repository --model-control-mode=poll\"' terminal=false")
print(f"-- Run CPU | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"docker run --rm --name triton --shm-size=3g -p8000:8000 -p8001:8001 -p8002:8002 -v /data:/data nvcr.io/nvidia/tritonserver:23.07-py3 tritonserver --model-repository=/data/models/common/model_repository --model-control-mode=poll\"' terminal=false")
print(f"-- Stop | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"docker stop triton\"' terminal=false")
print(f"-- Restart | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"docker restart triton\"' terminal=false")

print(f"ml-triton: {m_state} {m_log}")
print(f"-- Up | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"docker-compose -f {COMPOSE_PATH} up -d \"' terminal=false")
print(f"-- Build | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"docker-compose -f {COMPOSE_PATH} up --build -d\"' terminal=false")
print(f"-- Stop | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"docker stop ml_triton\"' terminal=false")

print(f"converter")
print(f"-- convert project onnx | bash='bash -c \"read -p \\\"Enter project name: \\\" project; if [ -n \\\"\\$project\\\" ]; then ssh {REMOTE_USER}@{REMOTE_HOST} \\\"/data/converting/convert_project.sh \\\"\\$project\\\"\\\"; fi; read -p \\\"Press Enter to close...\\\"\"' terminal=true")
print(f"-- Cleanup server | bash='ssh {REMOTE_USER}@{REMOTE_HOST} \"/home/sm/cleanup.sh\"' terminal=true")

# Блок MLRun port forwarding
print(f"MLRun ports (kubectl: {k_status}  tunnel: {s_status})")
print(f"-- Open ports | bash='bash -c \"ssh {REMOTE_USER}@{REMOTE_HOST} /home/sm/port-forward.sh start && ssh -f -N -L {LOCAL_UI_PORT}:localhost:{LOCAL_UI_PORT} -L {LOCAL_API_PORT}:localhost:{LOCAL_API_PORT} {REMOTE_USER}@{REMOTE_HOST}\"' terminal=false")
print(f"-- Close ports | bash='bash -c \"ssh {REMOTE_USER}@{REMOTE_HOST} /home/sm/port-forward.sh stop; fuser -k {LOCAL_UI_PORT}/tcp {LOCAL_API_PORT}/tcp\"' terminal=false")
