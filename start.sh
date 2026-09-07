#!/usr/bin/env bash

# ==============================================================================
# Smart Parking System - Fullstack Startup Script (Backend + Frontend)
# ==============================================================================

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}    Smart Parking System - Starting Application    ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Environment file check
if [ ! -f .env ] && [ -f .env.example ]; then
    echo -e "${YELLOW}[-] Copying .env.example to .env ...${NC}"
    cp .env.example .env
fi

if [ ! -f api/.env ] && [ -f api/.env.example ]; then
    echo -e "${YELLOW}[-] Copying api/.env.example to api/.env ...${NC}"
    cp api/.env.example api/.env
fi

# 2. Python / Backend check
if command -v python3 &>/dev/null; then
    scheme_python="python3"
else
    scheme_python="python"
fi

if ! $scheme_python -c "import uvicorn, fastapi" &>/dev/null; then
    echo -e "${YELLOW}[!] Warning: Required Python packages (fastapi, uvicorn) may not be installed in the active environment.${NC}"
    echo -e "${YELLOW}[!] Please ensure you have installed dependencies via: pip install -r requirements.txt${NC}"
fi

# 3. Node.js / Frontend check
if [ ! -d "web/node_modules" ]; then
    echo -e "${YELLOW}[!] Warning: web/node_modules directory not found.${NC}"
    echo -e "${YELLOW}[!] If frontend fails to start, please run: cd web && npm install${NC}"
fi

# Cleanup handler for graceful shutdown
cleanup() {
    echo -e "\n${YELLOW}[!] Shutting down services...${NC}"
    if [ -n "$PID_BACKEND" ] && kill -0 "$PID_BACKEND" 2>/dev/null; then
        echo -e "${GREEN}[+] Stopping Backend API (PID: $PID_BACKEND)...${NC}"
        kill -TERM "$PID_BACKEND" 2>/dev/null || true
    fi
    if [ -n "$PID_FRONTEND" ] && kill -0 "$PID_FRONTEND" 2>/dev/null; then
        echo -e "${GREEN}[+] Stopping Frontend Web UI (PID: $PID_FRONTEND)...${NC}"
        kill -TERM "$PID_FRONTEND" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo -e "${GREEN}[+] Services stopped successfully.${NC}"
}

trap cleanup SIGINT SIGTERM EXIT

# 4. Start Backend (FastAPI)
echo -e "${GREEN}[+] Starting Backend API (FastAPI) on port 8000...${NC}"
$scheme_python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
PID_BACKEND=$!

# 5. Start Frontend (Next.js)
echo -e "${GREEN}[+] Starting Frontend Web UI (Next.js) on port 3000...${NC}"
(cd web && npm run dev) &
PID_FRONTEND=$!

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN} Services are running!${NC}"
echo -e " Backend API:    ${BLUE}http://localhost:8000${NC}"
echo -e " API Docs:       ${BLUE}http://localhost:8000/docs${NC}"
echo -e " Frontend UI:    ${BLUE}http://localhost:3000${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}\n"

# Wait for background processes
wait
