FROM ubuntu:22.04

# Shared environment variables
ENV POETRY_VIRTUALENVS_PATH=/openhands/poetry \
    MAMBA_ROOT_PREFIX=/openhands/micromamba \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    EDITOR=code \
    VISUAL=code \
    GIT_EDITOR="code --wait" \
    OPENVSCODE_SERVER_ROOT=/openhands/.openvscode-server




RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y software-properties-common && \
    DEBIAN_FRONTEND=noninteractive add-apt-repository ppa:deadsnakes/ppa





# ================================================================
# START: Build Runtime Image from Scratch
# ================================================================
# This is used in cases where the base image is something more generic like nikolaik/python-nodejs
# rather than the current OpenHands release



# Install base system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget curl ca-certificates sudo apt-utils git jq tmux build-essential ripgrep s3fs ffmpeg \
        libgl1-mesa-glx \
        libasound2-plugins libatomic1 && \curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    TZ=Etc/UTC DEBIAN_FRONTEND=noninteractive \
        apt-get install -y --no-install-recommends nodejs python3.12 python-is-python3 python3-pip python3.12-venv && \
    corepack enable yarn && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


RUN ln -s "$(dirname $(which node))/corepack" /usr/local/bin/corepack && \
    npm install -g corepack && corepack enable yarn && \
    curl -fsSL --compressed https://install.python-poetry.org | python -


# Install uv (required by MCP)
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/openhands/bin" sh
# Add /openhands/bin to PATH
ENV PATH="/openhands/bin:${PATH}"

# Remove UID 1000 named pn or ubuntu, so the 'openhands' user can be created from ubuntu hosts
RUN (if getent passwd 1000 | grep -q pn; then userdel pn; fi) && \
    (if getent passwd 1000 | grep -q ubuntu; then userdel ubuntu; fi)


# Create necessary directories
RUN mkdir -p /openhands && \
    mkdir -p /openhands/logs && \
    mkdir -p /openhands/poetry

    # Install micromamba
RUN mkdir -p /openhands/micromamba/bin && \
    /bin/bash -c "PREFIX_LOCATION=/openhands/micromamba BIN_FOLDER=/openhands/micromamba/bin INIT_YES=no CONDA_FORGE_YES=yes $(curl -L https://micro.mamba.pm/install.sh)" && \
    /openhands/micromamba/bin/micromamba config remove channels defaults && \
    /openhands/micromamba/bin/micromamba config list

# Create the openhands virtual environment and install poetry and python
RUN /openhands/micromamba/bin/micromamba create -n openhands -y && \
    /openhands/micromamba/bin/micromamba install -n openhands -c conda-forge poetry python=3.12 -y

# Create a clean openhands directory including only the pyproject.toml, poetry.lock and openhands/__init__.py
RUN \
    if [ -d /openhands/code ]; then rm -rf /openhands/code; fi && \
    mkdir -p /openhands/code/openhands && \
    touch /openhands/code/openhands/__init__.py

# Setup VSCode Server
ARG RELEASE_TAG="openvscode-server-v1.98.2"
ARG RELEASE_ORG="gitpod-io"
# ARG USERNAME=openvscode-server
# ARG USER_UID=1000
# ARG USER_GID=1000

RUN if [ -z "${RELEASE_TAG}" ]; then \
        echo "The RELEASE_TAG build arg must be set." >&2 && \
        exit 1; \
    fi && \
    arch=$(uname -m) && \
    if [ "${arch}" = "x86_64" ]; then \
        arch="x64"; \
    elif [ "${arch}" = "aarch64" ]; then \
        arch="arm64"; \
    elif [ "${arch}" = "armv7l" ]; then \
        arch="armhf"; \
    fi && \
    wget https://github.com/${RELEASE_ORG}/openvscode-server/releases/download/${RELEASE_TAG}/${RELEASE_TAG}-linux-${arch}.tar.gz && \
    tar -xzf ${RELEASE_TAG}-linux-${arch}.tar.gz && \
    if [ -d "${OPENVSCODE_SERVER_ROOT}" ]; then rm -rf "${OPENVSCODE_SERVER_ROOT}"; fi && \
    mv ${RELEASE_TAG}-linux-${arch} ${OPENVSCODE_SERVER_ROOT} && \
    cp ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/openvscode-server ${OPENVSCODE_SERVER_ROOT}/bin/remote-cli/code && \
    rm -f ${RELEASE_TAG}-linux-${arch}.tar.gz
