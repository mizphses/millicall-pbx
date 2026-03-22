FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    asterisk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create venv and install dependencies
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Copy the rest
COPY alembic.ini .
COPY migrations/ migrations/
COPY asterisk_templates/ asterisk_templates/
COPY templates/ templates/
COPY static/ static/
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000 5060/udp 5060/tcp 10000-10100/udp

ENTRYPOINT ["/entrypoint.sh"]
