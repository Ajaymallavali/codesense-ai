# CodeSense AI

AI-powered code review and software quality platform for GitHub repositories.

CodeSense AI helps developers import repositories, analyze source code, detect bugs and code smells, estimate technical debt, generate documentation, and review pull requests with AI-assisted explanations.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, Recharts
- Backend API: Python, FastAPI, JWT authentication
- AI Service: Python, FastAPI
- Database: PostgreSQL
- Cache: Redis
- DevOps: Docker Compose

## Repository Layout

```text
codesense-ai/
  frontend/       React user interface
  backend/        FastAPI REST API
  ai-service/     FastAPI analysis service
  database/       PostgreSQL bootstrap scripts
  docker/         Service Dockerfiles
  docs/           Architecture and planning notes
  scripts/        Developer helper scripts
```

## Quick Start

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8050/api
- AI Service: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Local Development

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8050
```

AI service:

```bash
cd ai-service
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Auth smoke test:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\auth-smoke.ps1
```

## Current Milestone

Milestone 1 created the working project foundation:

- Product-style React dashboard
- FastAPI health and analysis endpoints
- FastAPI mock analysis endpoint
- PostgreSQL schema bootstrap
- Docker Compose environment
- Architecture documentation

Milestone 2 adds authentication:

- Register and login endpoints
- BCrypt password hashing
- HMAC-signed JWT access token
- Protected backend routes
- Auth-first frontend experience
- Logout and local token persistence
- Live browser-tested register/login flow
- Repeatable auth smoke-test script

The active backend is now fully Python/FastAPI. Upcoming milestones will deepen GitHub OAuth, repository import, static analysis, and AI review workflows.
