# Agent Instructions

## Dependencies

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

Install dependencies:
```bash
uv sync --extra dev
```

## Build

Build the container:
```bash
podman build -t garbage_bin .
```

## Test

Run tests locally (requires libgl1 and libglib2.0-0 system packages):
```bash
uv run python -m pytest -v
```

Run tests in container:
```bash
podman build -t garbage_bin_test -f - . <<'EOF'
FROM ubuntu:24.04

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates pkg-config \
        python3-pip python3-dev python3-venv libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock /app/
RUN uv sync --extra dev --no-install-project
COPY . /app
RUN uv sync --extra dev
CMD ["uv", "run", "python", "-m", "pytest", "-v"]
EOF

podman run --rm garbage_bin_test
```

## Lint

Run linter:
```bash
uv run ruff check .
```

Fix auto-fixable issues:
```bash
uv run ruff check --fix .
```
