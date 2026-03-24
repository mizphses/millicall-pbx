FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    asterisk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user for the application
RUN groupadd -r millicall && useradd -r -g millicall -G asterisk -s /bin/bash millicall

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

# Create data directory and set permissions
RUN mkdir -p /app/data \
    && mkdir -p /usr/share/asterisk/sounds/en/millicall \
    && mkdir -p /var/spool/asterisk/recording \
    && mkdir -p /var/log/asterisk/cdr-custom \
    && chown -R millicall:millicall /app/data \
    && chown -R millicall:asterisk /usr/share/asterisk/sounds/en/millicall \
    && chown -R millicall:asterisk /var/spool/asterisk/recording \
    && chown -R asterisk:asterisk /var/log/asterisk/cdr-custom

EXPOSE 8000 5060/udp 5060/tcp 10000-10100/udp

ENTRYPOINT ["/entrypoint.sh"]
