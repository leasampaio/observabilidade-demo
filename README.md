# Observabilidade Demo — Prometheus · Loki · Grafana · Python

Ambiente local mínimo demonstrando os três pilares da observabilidade:
**métricas** (Prometheus), **logs** (Loki via Promtail) e **visualização
unificada** (Grafana). Stack LGTM parcial, sobe com um único comando.

## Como rodar

```bash
# 1. Subir tudo
docker compose up --build -d

# 2. Gerar tráfego (em outro terminal)
while true; do
  curl -s http://localhost:8001/       > /dev/null
  curl -s http://localhost:8001/buy    > /dev/null
  curl -s http://localhost:8001/error  > /dev/null
  sleep 1
done

# 3. Abrir o Grafana → dashboard "Demo Observabilidade"
#    http://localhost:3000   (login: admin / 1234)
```

## Portas

| Serviço    | URL                     |
|------------|-------------------------|
| Python App | http://localhost:8001   |
| Prometheus | http://localhost:9090   |
| Loki       | http://localhost:3100   |
| Grafana    | http://localhost:3000   |


## Prometheus
Query: http_requests_total


## Endpoints da app

- `GET /` — tráfego normal
- `GET /buy` — latência variável (0.05–0.5s)
- `GET /error` — sempre HTTP 500 (gera log `level=ERROR`)
- `GET /metrics` — métricas Prometheus

## Encerrar

```bash
docker compose down          # mantém volumes
docker compose down -v       # remove dados do Loki/Grafana
```
