# syntax=docker/dockerfile:1.7
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project


FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --system --uid 1000 --create-home app

COPY --from=builder /app/.venv /app/.venv
COPY src /app/src
WORKDIR /app/src

# settings.py requires these keys at import; the throwaway .env exists only for this RUN.
RUN --mount=type=bind,source=docker/build.env,target=/app/.env \
    python manage.py collectstatic --noinput

COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint

USER app
EXPOSE 8000
ENTRYPOINT ["entrypoint"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--threads", "8", "--timeout", "60", "--access-logfile", "-"]
