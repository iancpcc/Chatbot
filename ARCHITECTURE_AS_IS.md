# Architecture AS-IS

## Overview
El proyecto sigue una arquitectura en capas con separación entre `presentation`, `application`, `domain` e `infrastructure`, usando FastAPI como entrada HTTP y repositorios en memoria como persistencia actual.

## Project Structure
```text
Chatbot/
├── app/
│   ├── main.py
│   ├── presentation/http/
│   │   ├── routers/
│   │   │   └── bookings.py
│   │   ├── schemas/
│   │   │   └── booking_schema.py
│   │   └── dependencies.py
│   ├── application/
│   │   ├── dto/
│   │   │   └── create_booking_dto.py
│   │   └── use_cases/
│   │       ├── create_booking.py
│   │       └── cancel_booking.py
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── booking.py
│   │   │   ├── conversation.py
│   │   │   ├── customer.py
│   │   │   ├── resource.py
│   │   │   └── service.py
│   │   ├── repositories/
│   │   │   ├── booking_repository.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── resource_repository.py
│   │   │   └── service_repository.py
│   │   ├── services/
│   │   │   └── availability_policy.py
│   │   └── value_objects/
│   │       ├── booking_status.py
│   │       ├── conversation.py
│   │       └── time_slot.py
│   └── infrastructure/
│       └── persistence/
│           ├── in_memory_booking_repository.py
│           ├── in_memory_conversation_repository.py
│           ├── in_memory_resource_repository.py
│           └── in_memory_service_repository.py
├── main.py
├── pyproject.toml
├── dockerfile
└── docker-compose.yaml
```

## Layered Component Diagram
```mermaid
flowchart LR
  Client[HTTP Client] --> FastAPI[FastAPI app/main.py]
  FastAPI --> Router[bookings router]
  Router --> UC1[CreateBooking use case]
  Router --> UC2[CancelBooking use case]

  UC1 --> BRepoContract[BookingRepository contract]
  UC1 --> SRepoContract[ServiceRepository contract]
  UC1 --> RRepoContract[ResourceRepository contract]
  UC1 --> Policy[AvailabilityPolicy]

  UC2 --> BRepoContract

  BRepoContract --> BRepoImpl[InMemoryBookingRepository]
  SRepoContract --> SRepoImpl[InMemoryServiceRepository]
  RRepoContract --> RRepoImpl[InMemoryResourceRepository]

  UC1 --> BookingEntity[Booking]
  UC1 --> CustomerEntity[Customer]
  UC1 --> ServiceEntity[Service]
  UC1 --> ResourceEntity[Resource]
  UC1 --> TimeSlotVO[TimeSlot]
  BookingEntity --> BookingStatusVO[BookingStatus]
```

## Runtime Request Flow (Create Booking)
```mermaid
sequenceDiagram
  participant C as Client
  participant API as FastAPI Router
  participant U as CreateBooking
  participant SR as ServiceRepository
  participant RR as ResourceRepository
  participant BR as BookingRepository
  participant P as AvailabilityPolicy

  C->>API: POST /bookings
  API->>U: execute(CreateBookingRequest DTO)
  U->>SR: get(tenant_id, service_id)
  U->>RR: get(tenant_id, resource_id)
  U->>BR: get_by_resource(tenant_id, resource_id)
  U->>P: ensure_available(existing_bookings, requested_slot)
  U->>BR: save(Booking)
  U-->>API: CreateBookingResponse
  API-->>C: 200 {booking_id, status}
```

## Dependency Direction
- `presentation` depende de `application`.
- `application` depende de contratos en `domain`.
- `infrastructure` implementa contratos de `domain`.
- `domain` no depende de capas externas.

## Current Notes
- Persistencia actual: solo en memoria (`in_memory_*`), no base de datos activa.
- Existen carpetas preparadas para crecimiento (`application/conversational`, `application/interfaces`, `infrastructure/providers/*`) sin implementación todavía.
- `main.py` de la raíz es un entrypoint auxiliar y no participa en la API HTTP principal (`app/main.py`).
