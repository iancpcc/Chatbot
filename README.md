# Booking Engine MVP

API base para reservas con arquitectura por capas (`presentation`, `application`, `domain`, `infrastructure`).

## Ejecutar

```bash
UV_CACHE_DIR=.uv-cache uv run uvicorn app.main:app --reload
```

## Datos demo cargados por defecto

- `tenant_id`: `demo-salon`
- `service_id`: `11111111-1111-1111-1111-111111111111`
- `resource_id`: `22222222-2222-2222-2222-222222222222`

## Crear una reserva

```bash
curl -X POST http://127.0.0.1:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-salon",
    "service_id": "11111111-1111-1111-1111-111111111111",
    "resource_id": "22222222-2222-2222-2222-222222222222",
    "customer_name": "Ana Perez",
    "customer_contact": "+34123456789",
    "start": "2026-03-01T10:00:00Z",
    "end": "2026-03-01T10:30:00Z"
  }'
```
