# CodeSense AI Architecture

## System Context

CodeSense AI is split into three primary services:

- React frontend for repository import, analysis dashboards, AI chat, and report downloads.
- FastAPI backend for authentication, GitHub integration, repository metadata, reports, and orchestration.
- FastAPI AI service for deeper static analysis, LLM-assisted explanations, documentation generation, and technical debt scoring.

## Request Flow

```text
Developer
  -> React frontend
  -> FastAPI backend
  -> PostgreSQL for metadata
  -> FastAPI AI service for analysis
  -> FastAPI backend stores findings and report metadata
  -> React dashboard displays results
```

## Milestone 1 Boundaries

The first milestone intentionally uses sample data. This keeps the product workflow visible while the next milestones add authentication, GitHub OAuth, repository cloning, Semgrep, Tree-sitter parsing, and LLM calls.

## Near-Term Backend Modules

- Auth: register, login, JWT issue and validation, GitHub OAuth account linking.
- Repository Manager: GitHub repository listing, branch selection, clone jobs.
- Analysis Orchestrator: analysis job lifecycle and AI service calls.
- Report Service: persisted reports, PDF export, technical debt summaries.

## Near-Term AI Modules

- Repository loader
- File classifier
- Complexity calculator
- Code smell rule engine
- Security scanner adapter
- LLM explanation and suggestion generator
