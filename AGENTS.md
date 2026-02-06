# Agent Instructions

## Dependencies

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

Install dependencies:
```bash
uv sync --all-extras
```

## Build

Build the container:
```bash
podman build -t garbage_bin .
```

## Test

Run tests (requires libgl1 and libglib2.0-0 system packages on Linux):
```bash
uv run --all-extras pytest -v
```

## Lint and Format

Run linter:
```bash
uv run ruff check .
```

Fix auto-fixable issues:
```bash
uv run ruff check --fix .
```

Run formatter:
```bash
uv run ruff format .
```

## Committing

Pre-commit hooks enforce linting, formatting, and block direct commits to master.
Always create a feature branch before committing:
```bash
git checkout -b my-feature
```
