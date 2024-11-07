FROM ubuntu:23.10

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
        python3-systemd \
        python3-opencv


RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -

COPY . /app
WORKDIR /app
ENV PATH=/opt/poetry/bin:$PATH
RUN poetry config virtualenvs.in-project true && poetry install
# Python and poetry installation
# ARG HOME="/home/$USER"
# ARG PYTHON_VERSION=3.11

# ENV PYENV_ROOT="${HOME}/.pyenv"
# ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${HOME}/.local/bin:$PATH"

# WORKDIR /app
# COPY pyproject.toml poetry.lock ./

# # Install Poetry
# RUN pip install --upgrade --break-system-packages pip && pip install --break-system-packages poetry
# RUN poetry config virtualenvs.create false \
#     && poetry install --no-dev
# RUN echo "done 0" \
#     && curl https://pyenv.run | bash \
#     && echo "done 1" \
#     && pyenv install ${PYTHON_VERSION} \
#     && echo "done 2" \
#     && pyenv global ${PYTHON_VERSION} \
#     && echo "done 3" \
#     && curl -sSL https://install.python-poetry.org | python3 - \
#     && poetry config virtualenvs.in-project true \
#     && poetry config virtualenvs.create false \
#     && poetry config virtualenvs.prefer-active-python true \
#     && poetry install --no-dev

# COPY . .
CMD ["/app/.venv/bin/python3", "main.py"]
