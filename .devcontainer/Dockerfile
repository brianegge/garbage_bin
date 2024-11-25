ARG VARIANT="3.12-bullseye"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

ARG DEBIAN_FRONTEND=noninteractive
ARG USER=vscode

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y build-essential --no-install-recommends make \
        ca-certificates \
        git \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncurses5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev \
        libgl1-mesa-dev \
        libsystemd-dev \
        pkg-config \
        python3-systemd \
        ack \
        systemd \
        libsystemd-dev \
        libgl1

RUN (type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
    && sudo mkdir -p -m 755 /etc/apt/keyrings \
    && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && sudo apt update \
    && sudo apt install gh -y

# Python and poetry installation
USER $USER
ARG HOME="/home/$USER"
ARG PYTHON_VERSION=3.12

# RUN pipx install poetry
WORKDIR /workspace
COPY pyproject.toml poetry.lock /workspace/

# ENV PYENV_ROOT="${HOME}/.pyenv"
# ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${HOME}/.local/bin:$PATH"
# RUN echo "Acquire::Check-Valid-Until \"false\";\nAcquire::Check-Date \"false\";" | cat > /etc/apt/apt.conf.d/10no--check-valid-until
# RUN apt-get update && apt-get install -y ack systemd libsystemd-dev libgl1
RUN pipx install pre-commit

# RUN echo "done 0" \
#     && curl https://pyenv.run | bash \
#     && echo "done 1" \
#     && pyenv install ${PYTHON_VERSION} \
#     && echo "done 2" \
#     && pyenv global ${PYTHON_VERSION} \
#     && echo "done 3" \
ENV PATH="${HOME}/.local/bin:${PATH}"
RUN curl -sSL https://install.python-poetry.org | python3
RUN poetry install --no-interaction --no-root \
     && poetry config virtualenvs.in-project true
    # && poetry config virtualenvs.create false \
    # && poetry config virtualenvs.prefer-active-python true
