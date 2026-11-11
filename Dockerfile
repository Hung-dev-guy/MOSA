FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.docker.txt ./
RUN pip install --no-cache-dir -r requirements.docker.txt
RUN useradd --create-home --uid 10001 mosa \
    && mkdir -p /app/instance \
    && chown mosa:mosa /app/instance
COPY --chown=mosa:mosa backend/ ./backend/
COPY --chown=mosa:mosa run.py ./
COPY --chown=mosa:mosa scripts/prepare_text_search.py ./scripts/prepare_text_search.py
COPY --from=frontend --chown=mosa:mosa /build/dist/ ./frontend/dist/
COPY --from=frontend --chown=mosa:mosa /build/public/ ./frontend/public/
USER mosa
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile - run:app"]
