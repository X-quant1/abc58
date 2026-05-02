"""健康检查脚本 - 每分钟检查前后端是否存活，挂了自动拉起"""
import subprocess
import time
import urllib.request
import sys

BACKEND_URL = "http://localhost:8000/api/health"
FRONTEND_URL = "http://localhost:5173"

PYTHON_EXE = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\btc-quant\Scripts\python.exe"
NODE_EXE = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\node.exe"
BACKEND_DIR = r"c:\LH\OKX\backend"
FRONTEND_DIR = r"c:\LH\OKX\frontend"

def check_url(url, timeout=3):
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except:
        return False

def start_backend():
    print("[Backend] Starting...")
    subprocess.Popen(
        [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

def start_frontend():
    print("[Frontend] Starting...")
    subprocess.Popen(
        [NODE_EXE, r"node_modules\vite\bin\vite.js"],
        cwd=FRONTEND_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

def main():
    print("Health monitor started (checking every 60s)")
    while True:
        backend_ok = check_url(BACKEND_URL)
        frontend_ok = check_url(FRONTEND_URL)

        if not backend_ok:
            print("[Backend] DOWN - restarting")
            start_backend()

        if not frontend_ok:
            print("[Frontend] DOWN - restarting")
            start_frontend()

        if backend_ok and frontend_ok:
            print("[OK] All services healthy")

        time.sleep(60)

if __name__ == "__main__":
    main()
