#!/usr/bin/env python3
"""
Smart Parking System - Fullstack Startup Script (Backend + Frontend)
Cross-platform runner script using Python.
"""

import os
import sys
import shutil
import signal
import subprocess
import time
from pathlib import Path

# ANSI colors
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
RESET = "\033[0m"


def print_banner():
    print(f"{BLUE}===================================================={RESET}")
    print(f"{BLUE}    Smart Parking System - Starting Application    {RESET}")
    print(f"{BLUE}===================================================={RESET}")


def check_env():
    root_dir = Path(__file__).parent.resolve()

    env_file = root_dir / ".env"
    env_example = root_dir / ".env.example"
    if not env_file.exists() and env_example.exists():
        print(f"{YELLOW}[-] Copying .env.example to .env ...{RESET}")
        shutil.copy(env_example, env_file)

    api_env = root_dir / "api" / ".env"
    api_env_example = root_dir / "api" / ".env.example"
    if not api_env.exists() and api_env_example.exists():
        print(f"{YELLOW}[-] Copying api/.env.example to api/.env ...{RESET}")
        shutil.copy(api_env_example, api_env)


def main():
    print_banner()
    check_env()

    root_dir = Path(__file__).parent.resolve()
    web_dir = root_dir / "web"

    # Check node_modules
    if not (web_dir / "node_modules").exists():
        print(
            f"{YELLOW}[!] Warning: web/node_modules not found. "
            f"If frontend fails to start, run 'cd web && npm install'.{RESET}"
        )

    processes = []

    def shutdown(signum=None, frame=None):
        print(f"\n{YELLOW}[!] Shutting down services...{RESET}")
        for p in processes:
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        time.sleep(1)
        for p in processes:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        print(f"{GREEN}[+] Services stopped successfully.{RESET}")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 1. Start Backend API
    print(f"{GREEN}[+] Starting Backend API (FastAPI) on port 8000...{RESET}")
    python_cmd = sys.executable
    backend_cmd = [
        python_cmd,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ]
    p_backend = subprocess.Popen(backend_cmd, cwd=str(root_dir))
    processes.append(p_backend)

    # 2. Start Frontend Next.js
    print(f"{GREEN}[+] Starting Frontend Web UI (Next.js) on port 3000...{RESET}")
    npm_cmd = shutil.which("npm") or "npm"
    p_frontend = subprocess.Popen([npm_cmd, "run", "dev"], cwd=str(web_dir))
    processes.append(p_frontend)

    print(f"\n{GREEN}===================================================={RESET}")
    print(f"{GREEN} Services are running!{RESET}")
    print(f" Backend API:    {BLUE}http://localhost:8000{RESET}")
    print(f" API Docs:       {BLUE}http://localhost:8000/docs{RESET}")
    print(f" Frontend UI:    {BLUE}http://localhost:3000{RESET}")
    print(f"{GREEN}===================================================={RESET}")
    print(f"{YELLOW}Press Ctrl+C to stop all services.{RESET}\n")

    try:
        while True:
            time.sleep(1)
            # Check if any process died unexpectedly
            for p in processes:
                if p.poll() is not None:
                    # process exited
                    pass
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
