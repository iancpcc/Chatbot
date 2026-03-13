# Booking Engine MVP

API base para reservas con arquitectura por capas (`presentation`, `application`, `domain`, `infrastructure`).
Versión actual de endpoints: `/v1`.

## Ejecutar

```bash
make run
```

## Atajos (estilo scripts)

```bash
make run
make test
make lint
make typecheck
make check
make db-upgrade
make db-revision m="add_table_x"
make docker-up
make docker-prod-up
```

## Configuracion

Variables principales (ver `.env.example`):

- `APP_ENV=dev|staging|prod` selecciona el provider de LLM (dev->Ollama, staging->Groq, prod->OpenAI).
- `LLM_PROVIDER=ollama|groq|openai` fuerza un provider (opcional).
- `DATABASE_URL` URL de Postgres/SQLite.
- `AUTO_APPLY_MIGRATIONS` aplica `alembic upgrade head` al iniciar la API (por defecto: `true` en `dev/staging`, `false` en `prod`).
- `SEED_DEMO_DATA` inserta catálogo demo al iniciar (por defecto: `true` en `dev/staging`, `false` en `prod`).
- `API_KEY` activa autenticación básica por header `x-api-key` en `/v1/*` (excepto `/v1/health`).
- `CORS_ALLOWED_ORIGINS` orígenes permitidos para CORS (lista separada por comas).
- `WEB_CONCURRENCY` número de workers Uvicorn para runtime en contenedor.
- `OLLAMA_BASE_URL` y `OLLAMA_MODEL` para Ollama; `OLLAMA_API_KEY` es opcional (local suele funcionar con token dummy).

Nota: no guardes keys reales en `.env` si lo versionas. Define `OPENAI_API_KEY`/`GROQ_API_KEY` como variables de entorno (shell/CI/CD).

Ejemplos Ollama:

- Local: `OLLAMA_BASE_URL=http://localhost:11434/v1` y sin key real.
- API remota: `OLLAMA_BASE_URL=https://tu-endpoint-ollama/v1` y `OLLAMA_API_KEY=<tu_key>`.

## Probar chat

Endpoint:

- `POST /v1/chat` con body `{tenant_id,user_id,channel,message,conversation_id?}`.
- `GET /health` (liveness).
- `GET /v1/health` para verificar estado de API/DB/LLM (readiness).

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: <API_KEY>" \
  -d '{
    "tenant_id": "mi-negocio",
    "user_id": "user-1",
    "channel": "web",
    "message": "Hola, quiero reservar un corte"
  }'
```

## Postgres con Podman (dev)

Levantar Postgres en contenedor y ejecutar la API local (host):

```bash
podman run --name booking_engine_postgres -d \
  -e POSTGRES_USER=chatbot \
  -e POSTGRES_PASSWORD=chatbot \
  -e POSTGRES_DB=chatbot \
  -p 5432:5432 \
  postgres:16-alpine
```

En tu `.env` (para `make run`) usa:

```bash
DATABASE_URL=postgresql+psycopg://chatbot:chatbot@localhost:5432/chatbot
```

Luego:

```bash
make run
```

## Migraciones (Alembic)

Aplicar migraciones en el entorno actual:

```bash
make db-upgrade
```

Crear nueva migración autogenerada:

```bash
make db-revision m="describe_change"
```

Recomendado para STG/PROD:

- Ejecutar `make db-upgrade` en el pipeline/deploy antes de levantar la nueva versión.
- Mantener `AUTO_APPLY_MIGRATIONS=false` en `prod` para evitar cambios de esquema automáticos en runtime.
- Mantener `SEED_DEMO_DATA=false` en `prod`.

## Docker Compose

Desarrollo (hot reload):

```bash
docker compose up --build
```

Producción (sin bind mounts de código):

```bash
docker compose -f docker-compose.prod.yaml up -d --build
```

Para PROD, ejecuta migraciones antes de levantar la nueva versión:

```bash
make db-upgrade
```

El contenedor de API corre como usuario no-root y usa `WEB_CONCURRENCY` para escalar workers.

## CI

Se añadió workflow de GitHub Actions en `.github/workflows/ci.yml` con:

- `ruff`
- `mypy`
- `pytest`
- `docker build` (validación de empaquetado)

## Datos demo cargados por defecto

- `tenant_id`: `demo-salon`
- `service_id`: `11111111-1111-1111-1111-111111111111`
- `resource_id`: `22222222-2222-2222-2222-222222222222`

## Crear una reserva

Primero crea un servicio y un recurso para tu tenant (o usa los datos demo).

```bash
curl -X POST http://127.0.0.1:8000/v1/services \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "mi-negocio",
    "name": "Corte clásico",
    "duration_minutes": 30,
    "price": 20.0
  }'
```

```bash
curl -X POST http://127.0.0.1:8000/v1/resources \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "mi-negocio",
    "name": "Silla 1"
  }'
```

Luego usa los IDs devueltos:

```bash
curl -X POST http://127.0.0.1:8000/v1/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "mi-negocio",
    "service_id": "SERVICE_ID",
    "resource_id": "RESOURCE_ID",
    "customer_name": "Ana Perez",
    "customer_contact": "+34123456789",
    "start": "2026-03-01T10:00:00Z",
    "end": "2026-03-01T10:30:00Z"
  }'
```

## Listar reservas

```bash
curl "http://127.0.0.1:8000/v1/bookings?tenant_id=mi-negocio"
```

Con filtros:

```bash
curl "http://127.0.0.1:8000/v1/bookings?tenant_id=mi-negocio&resource_id=RESOURCE_ID&start_from=2026-03-01T00:00:00Z&end_to=2026-03-02T00:00:00Z"
```

## Obtener y cancelar una reserva

```bash
curl "http://127.0.0.1:8000/v1/bookings/BOOKING_ID?tenant_id=mi-negocio"
```

```bash
curl -X PATCH "http://127.0.0.1:8000/v1/bookings/BOOKING_ID/cancel?tenant_id=mi-negocio"
```

## Formato de error (estándar)

```json
{
  "code": "validation_error|not_found|conflict|domain_error|request_validation_error|unauthorized",
  "message": "Human readable message",
  "details": null,
  "request_id": "uuid"
}
```
