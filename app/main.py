"""
Aplicação de demonstração de observabilidade.

Expõe métricas no formato Prometheus em /metrics e emite um log JSON
estruturado (uma linha por requisição) no stdout, coletado pelo Promtail
e enviado ao Loki.
"""
import asyncio
import logging
import random
import sys
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pythonjsonlogger import jsonlogger

SERVICE_NAME = "demo-app"

# --------------------------------------------------------------------------- #
# Logging estruturado (JSON, uma linha por evento, no stdout)
# --------------------------------------------------------------------------- #
logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.propagate = False

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(_handler)


def emit_log(level: str, method: str, endpoint: str, status_code: int,
             duration_ms: int, error_detail: str | None = None) -> None:
    """Emite uma linha de log JSON no stdout."""
    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "level": level,
        "service": SERVICE_NAME,
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    if error_detail is not None:
        payload["error_detail"] = error_detail
    logger.info("request", extra=payload)


# --------------------------------------------------------------------------- #
# Métricas Prometheus
# --------------------------------------------------------------------------- #
http_requests_total = Counter(
    "http_requests_total",
    "Total de requisições HTTP",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Duração das requisições em segundos",
    ["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Requisições em andamento no momento",
)

# --------------------------------------------------------------------------- #
# Aplicação FastAPI
# --------------------------------------------------------------------------- #
app = FastAPI(title="Observabilidade Demo")


@app.middleware("http")
async def metrics_and_logging(request: Request, call_next):
    """Aplica métricas e logging estruturado a todas as requisições."""
    endpoint = request.url.path

    # O endpoint /metrics não deve ser instrumentado para evitar ruído.
    if endpoint == "/metrics":
        return await call_next(request)

    http_requests_in_progress.inc()
    start = time.perf_counter()
    error_detail = None
    try:
        response = await call_next(request)
        status_code = response.status_code
    finally:
        duration = time.perf_counter() - start
        http_requests_in_progress.dec()

    duration_ms = int(duration * 1000)
    http_request_duration_seconds.labels(endpoint=endpoint).observe(duration)
    http_requests_total.labels(
        method=request.method, endpoint=endpoint, status_code=status_code
    ).inc()

    if status_code >= 500:
        error_detail = "Erro simulado para demonstração"
        emit_log("ERROR", request.method, endpoint, status_code,
                 duration_ms, error_detail)
    else:
        emit_log("INFO", request.method, endpoint, status_code, duration_ms)

    return response


@app.get("/")
async def root():
    """Tráfego normal."""
    return {"message": "ok"}


@app.get("/buy")
async def buy():
    """Simula uma compra com latência variável."""
    await asyncio.sleep(random.uniform(0.05, 0.5))
    return {"message": "compra realizada"}


@app.get("/error")
async def error():
    """Sempre falha — gera HTTP 500 e log de erro."""
    return JSONResponse(
        status_code=500,
        content={"error": "Erro simulado para demonstração"},
    )


@app.get("/metrics")
async def metrics():
    """Expõe as métricas no formato Prometheus."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
