# ADR-0002: Contrato de arquitectura v1 (congelado)

## Estado
Aceptado

## Decisión
Se congela el contrato de arquitectura v1 con estas reglas:

- `presentation` solo transforma I/O y delega en casos de uso.
- `application` orquesta casos de uso y depende de contratos de `domain`.
- `domain` contiene reglas de negocio, entidades, value objects y contratos.
- `infrastructure` implementa contratos de `domain` y no contiene reglas de negocio.

No se permite romper estas fronteras sin nueva ADR.

## Dependencias permitidas

- `presentation -> application, domain(value objects/schemas de salida solo si es imprescindible)`
- `application -> domain`
- `domain -> (sin dependencias a application/presentation/infrastructure)`
- `infrastructure -> domain`

Dependencias no permitidas:
- `domain -> infrastructure`
- `domain -> application`
- `application -> presentation`
- lógica de negocio en `presentation` o `infrastructure`

## Interfaces congeladas (v1)

### Repositories (`app/domain/repositories`)

`BookingRepository`
- `save(booking: Booking) -> None`
- `get_by_id(booking_id: UUID) -> Optional[Booking]`
- `get_by_resource(tenant_id: str, resource_id: UUID) -> List[Booking]`

`ServiceRepository`
- `get(tenant_id: str, service_id: UUID) -> Optional[Service]`

`ResourceRepository`
- `get(tenant_id: str, resource_id: UUID) -> Optional[Resource]`

`ConversationRepository`
- `save(conversation: Conversation) -> None`
- `get(conversation_id: UUID) -> Optional[Conversation]`

### DTOs (`app/application/dto`)

`CreateBookingRequest`
- `tenant_id: str`
- `service_id: UUID`
- `resource_id: UUID`
- `customer_name: str`
- `customer_contact: str`
- `start: datetime`
- `end: datetime`

`CreateBookingResponse`
- `booking_id: UUID`
- `status: str`

## Política de cambio

Cualquier cambio de firma en interfaces o DTOs requiere:
- Nueva ADR con motivación y compatibilidad.
- Actualización de implementaciones de infraestructura.
- Actualización de tests de caso de uso y API.

## Impacto

- Reduce retrabajo y deriva arquitectónica.
- Protege el núcleo de negocio frente a cambios de transporte o persistencia.
- Hace explícito dónde se discuten cambios contractuales.
