FROM ubuntu:24.04

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y build-essential --no-install-recommends  \
        curl \
        ca-certificates \
        libsystemd-dev \
        pkg-config \
        python3-pip \
        python3-dev \
        python3-venv \
        python3-systemd && \
        rm -rf /var/lib/apt/lists/*

# Passed from Github Actions
ARG GIT_VERSION_TAG=unspecified
ARG GIT_COMMIT_MESSAGE=unspecified
ARG GIT_VERSION_HASH=unspecified

WORKDIR /app

# You can read these files for the information in your application
RUN echo $GIT_VERSION_TAG > GIT_VERSION_TAG.txt
RUN echo $GIT_COMMIT_MESSAGE > GIT_COMMIT_MESSAGE.txt
RUN echo $GIT_VERSION_HASH > GIT_VERSION_HASH.txt

COPY poetry.lock pyproject.toml /app/

RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Set POETRY_HOME environment variable
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

RUN --mount=type=cache,target=/root/.cache/pypoetry \
       poetry install --only main --no-interaction

COPY . /app

CMD ["python3", "garbage_bin/main.py"]
