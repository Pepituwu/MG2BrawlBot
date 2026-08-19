# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt


FROM python:3.12-slim

RUN groupadd --system brawlbot && \
    useradd --system --create-home --gid brawlbot brawlbot

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --chown=brawlbot:brawlbot . .

RUN mkdir -p /app/.logs && \
    chown -R brawlbot:brawlbot /app

USER brawlbot

ENTRYPOINT ["python", "main.py"]
