FROM python:3.12-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV REFLEX_REDIS_URL=redis://localhost \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml rxconfig.py main.py ./
COPY reflex_ui ./reflex_ui

RUN pip install --no-cache-dir \
    "reflex>=0.9.0,<1" \
    "openai>=1.0.0" \
    "psycopg[binary,pool]>=3.2.0" \
    "bcrypt>=4.0"

RUN reflex init
RUN reflex export --frontend-only --no-zip

STOPSIGNAL SIGKILL

EXPOSE 3000 8000

CMD ["/bin/bash", "-lc", "if [ -f /run/secrets/openai_api_key ]; then export OPENAI_API_KEY=\"$(cat /run/secrets/openai_api_key)\"; fi && if [ -d alembic ]; then reflex db migrate; fi && redis-server --daemonize yes && exec reflex run --env prod"]
