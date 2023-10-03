# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10.12
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Create the user that will run the applications
ARG UID=10001
ARG GID=10001
RUN addgroup --gid ${GID} appgroup
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    --gid "${GID}" \
    appuser

# Create the directory for the application to live in
WORKDIR /app

# Copy dependencies list from source
COPY requirements.txt /app/

# Download Dependencies
RUN pip install -r requirements.txt

# Copy the source code into the container.
COPY . /app/

# Change ownership and permissions of workdir
RUN chown -R appuser:appgroup /app

# Switch users
USER appuser


