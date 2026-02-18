# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.7
ARG JUPYTER_VERSION=2025-04-14

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv_image

FROM python:${PYTHON_VERSION}-slim AS base

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_FROZEN=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# Create a non-privileged user.
# See https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user
ARG UID=1000
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    nomad


# Final stage to create the runnable image with minimal size
FROM base AS base_final

WORKDIR /app

RUN apt-get update \
 && apt-get install --yes --quiet --no-install-recommends \
       libgomp1 \
       libmagic1 \
       curl \
       zip \
       unzip \
       nodejs \
       npm \
       && npm install -g configurable-http-proxy@^4.2.0 \
       # clean cache and logs
       && rm -rf /var/lib/apt/lists/* /var/log/* /var/tmp/* ~/.npm

# Activate the virtualenv in the container
# See here for more information:
# https://pythonspeed.com/articles/multi-stage-docker-python/
ENV PATH="/opt/venv/bin:$PATH"


FROM base AS builder

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

ENV RUNTIME=docker

WORKDIR /app

RUN apt-get update \
 && apt-get install --yes --quiet --no-install-recommends \
      libgomp1 \
      libmagic1 \
      file \
      gcc \
      build-essential \
      curl \
      zip \
      unzip \
      git \
 && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=uv_image /uv /bin/uv

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=source=.git,target=.git,type=bind \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --extra plugins


COPY scripts ./scripts

FROM builder AS docs

WORKDIR /app

ARG NOMAD_DOCS_REPO="https://github.com/FAIRmat-NFDI/nomad-docs.git"

RUN set -ex && \
    echo "Cloning from: $NOMAD_DOCS_REPO" && \
    git clone "$NOMAD_DOCS_REPO" docs

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv run --with nomad-docs --directory docs mkdocs build \
    && mkdir -p built_docs \
    && cp -r docs/site/* built_docs

FROM base_final AS final

ARG PYTHON_VERSION=3.12

COPY --chown=nomad:${UID} --from=builder /opt/venv /opt/venv
COPY --chown=nomad:${UID} scripts/run.sh .
COPY --chown=nomad:${UID} scripts/run-worker.sh .
COPY configs/nomad.yaml nomad.yaml
COPY pyproject.toml uv.lock /opt/
COPY --chown=nomad:${UID} --from=docs /app/built_docs /opt/venv/lib/python${PYTHON_VERSION}/site-packages/nomad/app/static/docs

RUN mkdir -p /app/.volumes/fs \
 && chown -R nomad:${UID} /app \
 && chown -R nomad:${UID} /opt/venv \
 && mkdir nomad \
 && cp /opt/venv/lib/python${PYTHON_VERSION}/site-packages/nomad/jupyterhub_config.py nomad/


USER nomad

# The application ports
EXPOSE 8000
EXPOSE 9000

VOLUME /app/.volumes/fs


FROM quay.io/jupyter/base-notebook:${JUPYTER_VERSION} AS jupyter_builder

ENV UV_PROJECT_ENVIRONMENT=/opt/conda \
    UV_FROZEN=1

# Fix: https://github.com/hadolint/hadolint/wiki/DL4006
# Fix: https://github.com/koalaman/shellcheck/wiki/SC3014
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER root

RUN apt-get update \
 && apt-get install --yes --quiet --no-install-recommends \
      libgomp1 \
      libmagic1 \
      file \
      gcc \
      build-essential \
      curl \
      zip \
      unzip \
      git \
      # clean cache and logs
      && rm -rf /var/lib/apt/lists/* /var/log/* /var/tmp/* ~/.npm

# Switch back to jovyan to avoid accidental container runs as root
USER ${NB_UID}
WORKDIR "${HOME}"

COPY --from=uv_image /uv /bin/uv

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    # Use inexact to avoid removing pre-installed packages in the environment
    # Use no-install-project to skip installing the current project (`nomad-distribution`)
    uv sync --extra plugins --extra jupyter --no-install-project --inexact


FROM quay.io/jupyter/base-notebook:${JUPYTER_VERSION} AS jupyter
# Fix: https://github.com/hadolint/hadolint/wiki/DL4006
# Fix: https://github.com/koalaman/shellcheck/wiki/SC3014
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER root

RUN apt-get update \
 && apt-get install --yes --quiet --no-install-recommends \
      libgomp1 \
      libmagic1 \
      file \
      curl \
      zip \
      unzip \
      git \
      # `nbconvert` dependencies
      # https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex
      texlive-xetex \
      texlive-fonts-recommended \
      texlive-plain-generic \
      # clean cache and logs
      && rm -rf /var/lib/apt/lists/* /var/log/* /var/tmp/* ~/.npm

# Switch back to jovyan to avoid accidental container runs as root
USER ${NB_UID}
WORKDIR "${HOME}"

COPY --from=uv_image /uv /bin/uv
COPY --from=jupyter_builder /opt/conda /opt/conda


# Get rid ot the following message when you open a terminal in jupyterlab:
# groups: cannot find name for group ID 11320
RUN touch ${HOME}/.hushlogin
