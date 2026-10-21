# CodeSense AI Production Deployment & Operations Guide

This guide provides end-to-end instructions for deploying CodeSense AI into production with real PostgreSQL, Redis, Google OAuth, Gemini AI, GitHub PR Webhooks, and Cloud Hosting.

---

## 1. Database Setup & Persistence (PostgreSQL / Neon / Supabase)

### Option A: Local / Docker PostgreSQL
To run PostgreSQL locally in Docker:
```bash
docker compose up -d postgres
```

### Option B: Cloud PostgreSQL (Neon / Supabase / AWS RDS)
1. Create a PostgreSQL database instance on [Neon](https://neon.tech) or [Supabase](https://supabase.com).
2. Copy the connection string and set `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@ep-sample-123.us-east-2.aws.neon.tech/codesense?sslmode=require
   ```

### Running Database Migrations
Run Alembic migrations from the `backend/` directory:
```bash
cd backend
alembic upgrade head
```
This boots and validates the `users`, `repositories`, `analyses`, `findings`, `organizations`, and `organization_members` tables.

---

## 2. Redis & Dedicated Background Worker

CodeSense includes an asynchronous queue for large AST repository scans.

1. **Start Redis**:
   ```bash
   docker compose up -d redis
   ```
2. **Start the Dedicated Background Worker**:
   ```bash
   cd backend
   python -m app.worker
   ```
The worker continuously monitors the `codesense:queue:analysis` queue and processes AST scans without blocking the API event loop.

---

## 3. Real Google OAuth & Gemini AI Configuration

1. **Google OAuth (1-Click Google Sign-In)**:
   - Create an OAuth 2.0 Web Application in [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
   - Set Authorized JavaScript Origins: `http://localhost:5173` and your production frontend domain (e.g., `https://codesense.vercel.app`).
   - Add to `.env`:
     ```env
     GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
     VITE_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
     ```

2. **Google Gemini Generative AI (Live PR Reviews & Chat)**:
   - Generate an API key at [Google AI Studio](https://aistudio.google.com).
   - Add to `.env`:
     ```env
     GEMINI_API_KEY=AIzaSy...
     ```

---

## 4. GitHub PR Webhook Integration

CodeSense can automatically audit Pull Requests and post review comments directly back to GitHub:

1. Navigate to your GitHub repository: **Settings -> Webhooks -> Add Webhook**.
2. **Payload URL**: `https://<your-backend-domain>/api/webhooks/github`
3. **Content type**: `application/json`
4. **Secret**: Set a secret key and mirror it in your `.env`:
   ```env
   GITHUB_WEBHOOK_SECRET=your-secret-key-here
   ```
5. **Events**: Select **"Let me select individual events"** and check **"Pull requests"**.
6. When a PR is opened or updated, CodeSense will automatically:
   - Run multi-language AST and Semgrep scanning.
   - Synthesize a structured review verdict (`APPROVE`, `REQUEST_CHANGES`, `COMMENT`).
   - Post comments and suggested patches to the PR.

---

## 5. Cloud Deployment

### Frontend (Vercel)
1. Push your repository to GitHub.
2. In [Vercel](https://vercel.com), click **Add New Project** and import `codesense-ai`.
3. Root Directory: `frontend`
4. Framework Preset: `Vite`
5. Configure Environment Variables:
   - `VITE_API_BASE_URL`: `https://<your-backend-domain>/api`
   - `VITE_GOOGLE_CLIENT_ID`: `xxx.apps.googleusercontent.com`
6. Click **Deploy**.

### Backend & AI Service (Render Blueprint)
CodeSense includes a [`render.yaml`](../render.yaml) blueprint specification:
1. In [Render](https://render.com), select **Blueprints -> New Blueprint Instance**.
2. Connect your GitHub repository. Render will automatically provision:
   - `codesense-backend` (FastAPI Web Service)
   - `codesense-ai-service` (FastAPI Web Service)
   - `codesense-worker` (Background Worker)
   - `codesense-postgres` (Managed PostgreSQL)
   - `codesense-redis` (Managed Redis)
3. Input your `GEMINI_API_KEY` and click **Apply**.
