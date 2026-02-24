FROM ubuntu:24.04

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        pkg-config \
        python3-pip \
        python3-dev \
        python3-venv \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Passed from Github Actions
ARG GIT_VERSION_TAG=unspecified
ARG GIT_COMMIT_MESSAGE=unspecified
ARG GIT_VERSION_HASH=unspecified

WORKDIR /app

# You can read these files for the information in your application
RUN echo $GIT_VERSION_TAG > GIT_VERSION_TAG.txt
RUN echo $GIT_COMMIT_MESSAGE > GIT_COMMIT_MESSAGE.txt
RUN echo $GIT_VERSION_HASH > GIT_VERSION_HASH.txt

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock* /app/

RUN uv sync --no-dev --no-install-project

COPY . /app

RUN uv sync --no-dev

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["uv", "run", "python3", "garbage_bin/healthcheck.py"]

CMD ["uv", "run", "python3", "garbage_bin/main.py"]
