ARG VARIANT="3.12-bullseye"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

# Python and poetry installation
USER $USER
ARG HOME="/home/$USER"
ARG PYTHON_VERSION=3.12

# RUN pipx install poetry
WORKDIR /workspace
COPY pyproject.toml poetry.lock /workspace/

# ENV PYENV_ROOT="${HOME}/.pyenv"
# ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${HOME}/.local/bin:$PATH"
RUN echo "Acquire::Check-Valid-Until \"false\";\nAcquire::Check-Date \"false\";" | cat > /etc/apt/apt.conf.d/10no--check-valid-until
RUN apt-get update && apt-get install -y ack systemd libsystemd-dev
RUN pipx install pre-commit

# RUN echo "done 0" \
#     && curl https://pyenv.run | bash \
#     && echo "done 1" \
#     && pyenv install ${PYTHON_VERSION} \
#     && echo "done 2" \
#     && pyenv global ${PYTHON_VERSION} \
#     && echo "done 3" \
ENV PATH="/home/.local/bin:${PATH}"
RUN curl -sSL https://install.python-poetry.org | python3
RUN poetry install $(test "$YOUR_ENV" == production && echo "--only=main") --no-interaction --no-root
    # && poetry config virtualenvs.in-project true \
    # && poetry config virtualenvs.create false \
    # && poetry config virtualenvs.prefer-active-python true
