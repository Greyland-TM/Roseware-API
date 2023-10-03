# Use Python version specified in the ARG as the base image.
ARG PYTHON_VERSION=3.10.12
FROM python:${PYTHON_VERSION}-slim as base

# Configure Python to prevent writing .pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Configure Python to unbuffer stdout and stderr for immediate log output.
ENV PYTHONUNBUFFERED=1

# Create a non-root user and group for running the application.
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

# Set the working directory for the application.
WORKDIR /app

# Copy the list of dependencies from the source into the container.
COPY requirements.txt /app/

# Install the application dependencies.
RUN pip install -r requirements.txt

# Copy the application source code into the container.
COPY . /app/

# Change ownership and permissions of the working directory to the appuser.
RUN chown -R appuser:appgroup /app

# Switch to the appuser for running the application.
USER appuser

