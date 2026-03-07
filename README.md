# Booking Engine MVP

API base para reservas con arquitectura por capas (`presentation`, `application`, `domain`, `infrastructure`).
Versión actual de endpoints: `/v1`.

## Ejecutar

```bash
UV_CACHE_DIR=.uv-cache uv run uvicorn app.main:app --reload
```

## Atajos (estilo scripts)

```bash
make run
make test
make lint
make typecheck
make check
```

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
  "code": "validation_error|not_found|conflict|domain_error|request_validation_error",
  "message": "Human readable message",
  "details": null,
  "request_id": "uuid"
}
```
