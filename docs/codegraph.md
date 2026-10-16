# CodeGraph Engine

CodeGraph is a development-time MCP tool for evidence-backed codebase search,
route inspection, symbol tracing, and architecture context. It is not part of
the FastAPI runtime or Docker deployment.

## Install on Windows

Run in PowerShell:

```powershell
pip install --upgrade --no-cache-dir "codegraph-engine[mcp]"
codegraph --version
```

## Index this repository

Run from the repository root:

```powershell
codegraph init .
codegraph index .
codegraph status .
codegraph doctor .
codegraph doctor --database .
```

Useful FastAPI route checks:

```powershell
codegraph routes --json .
codegraph routes --method GET .
codegraph routes --path /api/auth .
```

## MCP editor setup

The repository includes `.cursor/mcp.json`. After installing CodeGraph and
restarting Cursor, its MCP tools can use the indexed repository through:

```powershell
codegraph mcp serve
```

Keep `.codegraph.sqlite3` local. It is generated from the source tree and is
excluded from Git by this project.
