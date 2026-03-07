# ADR-0003: Política de ciclo de vida de Booking v1

## Estado
Aceptado

## Decisión
Se establece el ciclo de vida de `Booking` para la demo v1:

- `create_booking` crea reservas en estado `pending`.
- `confirm` es una transición explícita (no implícita en creación).
- `cancel` se permite desde `pending` y `confirmed`.
- `complete` solo se permite desde `confirmed`.
- Reservas `cancelled` y `completed` no bloquean disponibilidad futura.
- Reservas `pending` y `confirmed` sí bloquean disponibilidad.

## Máquina de estados

- Estado inicial: `pending`.
- Transiciones válidas:
  - `pending -> confirmed`
  - `pending -> cancelled`
  - `confirmed -> completed`
  - `confirmed -> cancelled`
- Transiciones inválidas:
  - Cualquier transición desde `cancelled`
  - `pending -> completed`
  - `completed -> any`

## Justificación arquitectónica

- Separar creación y confirmación evita asumir confirmación automática en flujos conversacionales o integraciones futuras.
- Mantener `pending` como bloqueante protege contra doble reserva mientras existe intención activa.
- `completed` y `cancelled` no deben bloquear agenda futura para evitar degradación de capacidad.

## Implicaciones de diseño

- La política de disponibilidad debe considerar bloqueantes solo `pending|confirmed`.
- Los casos de uso de cancelación/completado deben validar transición de estado.
- API debe exponer estado actual de forma explícita en cada respuesta relevante.

## Impacto

- Unifica criterio funcional para API, dominio y futura capa conversacional.
- Reduce ambigüedad en conflictos de agenda y en reglas de transición.
