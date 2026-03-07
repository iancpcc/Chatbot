# ADR-0001: Demo interna y flujo evolutivo

## Estado
Aceptado

## Objetivo
Tener una demo funcional interna de forma rápida, pero con un camino claro para evolucionar sin reescribir el core.

## Base actual de demo (mínimo viable)

- Canal: web chat/API simple.
- Backend/API: FastAPI monolítico.
- Persistencia inicial: in-memory (actual) o SQLite local según necesidad de estabilidad.
- LLM: OpenAI `gpt-4.1-mini`.

Racional:
- Prioriza velocidad de validación end-to-end para 1-3 usuarios.
- Minimiza operación y puntos de fallo.

## Flujo futuro propuesto (punta a punta)

1. Cerrar contrato de arquitectura
- Confirmar límites entre `presentation -> application -> domain -> infrastructure`.
- Congelar interfaces de repositorio y DTOs para evitar retrabajo.

2. Blindar con pruebas
- Tests de dominio (reglas de booking/availability).
- Tests de casos de uso.
- Tests API básicos (happy path + errores).
- CI local mínima con `ruff + mypy + pytest`.

3. Sustituir in-memory por persistencia real
- Modelo SQLAlchemy + Alembic.
- Repositorios DB que implementen los contratos actuales.
- Mantener compatibilidad de casos de uso sin tocar lógica de negocio.

4. Completar API operacional
- Endpoints: crear/cancelar/consultar/listar bookings.
- Errores estandarizados, validación y trazabilidad.

5. Incorporar capa conversacional
- Caso de uso de `Conversation` (iniciar, actualizar estado, cerrar).
- Orquestación: mensaje entrante -> intención -> caso de uso -> respuesta.
- Adaptadores de providers (LLM/mensajería/speech) detrás de interfaces.

6. Integración completa de flujo
- Canal de entrada (chat/API) llama a `application`.
- `application` usa `domain + repositorios`.
- `infrastructure` persiste y conecta servicios externos.
- `presentation` solo expone y transforma I/O.

7. Operación y escalado
- Configuración por entorno, Docker sólido, healthchecks.
- Logging/metrics básicos.
- Documentación de ejecución y despliegue.

## Cambios tempranos a decidir

- DB objetivo (`PostgreSQL` recomendado).
- Modelo multi-tenant (aislamiento por `tenant_id`).
- Estado final del dominio de booking (`pending/confirmed` y cuándo transiciona).
- Prioridad real de módulo conversacional vs booking core.

## Impacto de esta decisión

- Alinea visión de corto plazo (demo rápida) con evolución técnica estructurada.
- Reduce riesgo de retrabajo al fijar contratos y orden de implementación.
- Permite mejoras incrementales sin bloquear entrega temprana.
