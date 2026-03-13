from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.application.dto.create_booking_dto import CreateBookingRequest
from app.application.dto.respond_to_message_dto import (
    ResponseOption,
    ResponsePayload,
    RespondToMessageRequest,
    RespondToMessageResponse,
)
from app.application.ports.llm_client import LLMClient
from app.application.use_cases.cancel_booking import CancelBooking
from app.application.use_cases.create_booking import CreateBooking
from app.application.use_cases.list_bookings import (
    ListBookings,
    ListBookingsRequest,
)
from app.application.use_cases.list_resources import (
    ListResources,
    ListResourcesRequest,
    ResourceItem,
)
from app.application.use_cases.list_services import (
    ListServices,
    ListServicesRequest,
    ServiceItem,
)
from app.domain.entities.conversation import Conversation
from app.domain.exceptions import (
    DomainError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
)
from app.domain.repositories.conversation_repository import ConversationRepository


_SYSTEM_PROMPT = (
    "You are a helpful booking assistant. Ask clarifying questions when needed. "
    "When you don't have enough information, ask for it instead of guessing."
)
_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_ISO_DATETIME_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?\b"
)
_NATURAL_DATETIME_PATTERN = re.compile(
    r"\b(hoy|mañana|manana)\b(?:\s*(?:a\s*las?)?\s*(\d{1,2})(?::(\d{2}))?)?",
    re.IGNORECASE,
)


class RespondToMessage:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        llm_client: LLMClient,
        create_booking_use_case: CreateBooking | None = None,
        cancel_booking_use_case: CancelBooking | None = None,
        list_bookings_use_case: ListBookings | None = None,
        list_services_use_case: ListServices | None = None,
        list_resources_use_case: ListResources | None = None,
    ):
        self.conversation_repository = conversation_repository
        self.llm_client = llm_client
        self.create_booking_use_case = create_booking_use_case
        self.cancel_booking_use_case = cancel_booking_use_case
        self.list_bookings_use_case = list_bookings_use_case
        self.list_services_use_case = list_services_use_case
        self.list_resources_use_case = list_resources_use_case

    def execute(self, request: RespondToMessageRequest) -> RespondToMessageResponse:
        message = request.message.strip()
        action_id = (request.action_id or "").strip()
        if not message and not action_id:
            raise ValidationError("Message must not be empty")

        input_text = action_id or message
        conversation = self._load_or_create_conversation(request)
        self._append_message(
            conversation,
            role="user",
            content=message if message else f"[action:{action_id}]",
        )
        self.conversation_repository.save(conversation)

        payload = self._try_handle_transactional_message(
            request=request,
            conversation=conversation,
            message=input_text,
            action_id=action_id or None,
        )
        if payload is None:
            llm_messages = self._build_llm_messages(conversation)
            try:
                llm_reply = self.llm_client.generate_reply(messages=llm_messages)
            except InfrastructureError:
                raise
            except Exception as exc:
                raise InfrastructureError(str(exc)) from exc
            payload = ResponsePayload(type="text", message=llm_reply)

        self._append_message(conversation, role="assistant", content=payload.message)
        self.conversation_repository.save(conversation)

        return RespondToMessageResponse(
            conversation_id=conversation.id,
            reply=payload.message,
            response=payload,
        )

    def _load_or_create_conversation(
        self, request: RespondToMessageRequest
    ) -> Conversation:
        if request.conversation_id is None:
            return Conversation(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                channel=request.channel,
                state={"messages": []},
            )

        conversation = self.conversation_repository.get(request.conversation_id)
        if conversation is None or conversation.tenant_id != request.tenant_id:
            raise NotFoundError("Conversation not found")
        return conversation

    def _append_message(
        self, conversation: Conversation, *, role: str, content: str
    ) -> None:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        existing = conversation.state.get("messages", [])
        if not isinstance(existing, list):
            raise ValidationError("Conversation state is corrupted (messages)")

        messages = list(existing)
        messages.append({"role": role, "content": content, "at": now})
        conversation.state["messages"] = messages

    def _build_llm_messages(self, conversation: Conversation) -> list[dict[str, str]]:
        raw_messages = conversation.state.get("messages", [])
        if not isinstance(raw_messages, list):
            raw_messages = []

        history = raw_messages[-20:]

        messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({"role": role, "content": content})
        return messages

    def _try_handle_transactional_message(
        self,
        *,
        request: RespondToMessageRequest,
        conversation: Conversation,
        message: str,
        action_id: str | None,
    ) -> ResponsePayload | None:
        lower_message = message.lower().strip()
        flow = str(conversation.state.get("flow", "")).strip().lower()

        if action_id == "cancel" or self._is_cancel_intent(lower_message):
            return self._handle_cancel(request.tenant_id, conversation, message)

        if (
            flow == "booking"
            or action_id == "booking"
            or self._is_booking_intent(lower_message)
        ):
            return self._handle_create_booking(
                tenant_id=request.tenant_id,
                conversation=conversation,
                message=message,
                action_id=action_id,
            )

        if action_id == "catalog" or self._is_catalog_intent(lower_message):
            return self._render_catalog(request.tenant_id)

        if action_id == "my_bookings" or self._is_list_bookings_intent(lower_message):
            return self._render_bookings(request.tenant_id)

        if self._is_greeting_intent(lower_message):
            return self._render_main_menu()

        return None

    def _is_booking_intent(self, lower_message: str) -> bool:
        return any(
            keyword in lower_message for keyword in ("reserv", "agend", "cita", "book")
        )

    def _is_cancel_intent(self, lower_message: str) -> bool:
        return any(keyword in lower_message for keyword in ("cancel", "anul"))

    def _is_confirm_intent(self, lower_message: str, action_id: str | None) -> bool:
        if action_id in {"confirm", "booking_confirm"}:
            return True
        return lower_message in {"confirmar", "confirmo", "si", "sí", "ok"}

    def _is_cancel_confirmation_intent(
        self, lower_message: str, action_id: str | None
    ) -> bool:
        if action_id in {"cancel", "booking_cancel"}:
            return True
        return lower_message in {"cancelar", "no", "anular"}

    def _is_list_bookings_intent(self, lower_message: str) -> bool:
        if "mis reservas" in lower_message:
            return True
        if "list" in lower_message and "reserv" in lower_message:
            return True
        return "bookings" in lower_message and "list" in lower_message

    def _is_catalog_intent(self, lower_message: str) -> bool:
        has_listing_verb = any(
            keyword in lower_message
            for keyword in ("lista", "list", "mostrar", "ver", "catalog")
        )
        return has_listing_verb and any(
            keyword in lower_message
            for keyword in ("servicios", "servicio", "resources", "recursos")
        )

    def _is_greeting_intent(self, lower_message: str) -> bool:
        return lower_message in {"hola", "buenas", "hello", "hi", "hey"}

    def _render_main_menu(self) -> ResponsePayload:
        return ResponsePayload(
            type="options",
            message="¿En qué puedo ayudarte?",
            options=[
                ResponseOption(id="catalog", label="Ver servicios"),
                ResponseOption(id="booking", label="Reservar cita"),
                ResponseOption(id="my_bookings", label="Mis reservas"),
                ResponseOption(id="cancel", label="Cancelar reserva"),
            ],
        )

    def _render_catalog(self, tenant_id: str) -> ResponsePayload | None:
        if self.list_services_use_case is None or self.list_resources_use_case is None:
            return None

        services = self.list_services_use_case.execute(
            ListServicesRequest(tenant_id=tenant_id)
        )
        resources = self.list_resources_use_case.execute(
            ListResourcesRequest(tenant_id=tenant_id)
        )
        service_lines = (
            [
                f"- {service.name} ({service.duration_minutes} min, {service.price:.2f} EUR) [{service.service_id}]"
                for service in services[:10]
            ]
            if services
            else ["- No hay servicios cargados"]
        )
        resource_lines = (
            [
                f"- {resource.name} [{resource.resource_id}]"
                for resource in resources[:10]
            ]
            if resources
            else ["- No hay recursos cargados"]
        )
        return ResponsePayload(
            type="text",
            message=(
                "Catalogo disponible:\n"
                "Servicios:\n"
                f"{chr(10).join(service_lines)}\n"
                "Recursos:\n"
                f"{chr(10).join(resource_lines)}"
            ),
        )

    def _render_bookings(self, tenant_id: str) -> ResponsePayload | None:
        if self.list_bookings_use_case is None:
            return None
        items = self.list_bookings_use_case.execute(
            ListBookingsRequest(tenant_id=tenant_id)
        )
        if not items:
            return ResponsePayload(
                type="text", message="No tienes reservas para este tenant."
            )

        lines = []
        for item in items[:5]:
            start = (
                item.start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            lines.append(
                f"- {item.booking_id} | {start} | estado={item.status} | contacto={item.customer_contact}"
            )
        return ResponsePayload(type="text", message="Reservas:\n" + "\n".join(lines))

    def _handle_cancel(
        self,
        tenant_id: str,
        conversation: Conversation,
        message: str,
    ) -> ResponsePayload | None:
        if self.cancel_booking_use_case is None:
            return None

        booking_id = self._extract_first_uuid(message)
        if booking_id is None:
            last_booking_id = conversation.state.get("last_booking_id")
            booking_id = (
                self._parse_uuid(last_booking_id)
                if isinstance(last_booking_id, str)
                else None
            )

        if booking_id is None:
            return ResponsePayload(
                type="text", message="Para cancelar necesito el booking_id (UUID)."
            )

        try:
            self.cancel_booking_use_case.execute(
                tenant_id=tenant_id, booking_id=booking_id
            )
        except DomainError as exc:
            return ResponsePayload(
                type="text", message=f"No pude cancelar la reserva: {exc}"
            )

        conversation.state["last_booking_id"] = str(booking_id)
        return ResponsePayload(
            type="text",
            message=f"Reserva {booking_id} cancelada correctamente.",
        )

    def _handle_create_booking(
        self,
        *,
        tenant_id: str,
        conversation: Conversation,
        message: str,
        action_id: str | None,
    ) -> ResponsePayload | None:
        if (
            self.create_booking_use_case is None
            or self.list_services_use_case is None
            or self.list_resources_use_case is None
        ):
            return None

        services = self.list_services_use_case.execute(
            ListServicesRequest(tenant_id=tenant_id)
        )
        resources = self.list_resources_use_case.execute(
            ListResourcesRequest(tenant_id=tenant_id)
        )
        if not services:
            return ResponsePayload(
                type="text",
                message="No hay servicios disponibles para este tenant. Crea uno antes de reservar.",
            )
        if not resources:
            return ResponsePayload(
                type="text",
                message="No hay recursos disponibles para este tenant. Crea uno antes de reservar.",
            )

        conversation.state["flow"] = "booking"
        draft = self._get_booking_draft(conversation)
        self._merge_booking_draft(
            draft=draft,
            message=message,
            action_id=action_id,
            services=services,
            resources=resources,
        )

        if not draft["service_id"].strip():
            conversation.state["step"] = "select_service"
            conversation.state["booking_draft"] = draft
            return ResponsePayload(
                type="options",
                message="Selecciona un servicio",
                options=[
                    ResponseOption(
                        id=str(service.service_id),
                        label=f"{service.name} ({service.duration_minutes} min)",
                    )
                    for service in services[:10]
                ],
            )

        if not draft["start"].strip():
            conversation.state["step"] = "select_datetime"
            conversation.state["booking_draft"] = draft
            slot_options = self._build_available_slot_options(
                tenant_id=tenant_id,
                draft=draft,
                services=services,
                resources=resources,
            )
            if slot_options:
                return ResponsePayload(
                    type="options",
                    message="Selecciona un horario",
                    options=slot_options,
                )
            return ResponsePayload(
                type="text",
                message="¿Qué día y hora te viene bien? (ej:'mañana a las 10')",
            )

        service_id = self._parse_uuid(draft["service_id"])
        start = self._parse_datetime(draft["start"])
        if service_id is None or start is None:
            conversation.state["booking_draft"] = draft
            return ResponsePayload(
                type="text",
                message="No pude interpretar el servicio o la fecha. Inténtalo otra vez.",
            )

        selected_service = self._find_service_by_id(services, service_id)
        if selected_service is None:
            conversation.state["booking_draft"] = draft
            return ResponsePayload(
                type="text", message="El service_id no existe en este tenant."
            )

        if resources:
            parsed_resource_id = self._parse_uuid(draft["resource_id"])
            available_resources = self._available_resources_for_slot(
                tenant_id=tenant_id,
                resources=resources,
                slot_start=start,
                duration_minutes=selected_service.duration_minutes,
            )

            if parsed_resource_id is not None:
                if not any(
                    item.resource_id == parsed_resource_id for item in available_resources
                ):
                    draft["resource_id"] = ""
                    conversation.state["step"] = "select_resource"
                    conversation.state["booking_draft"] = draft
                    return ResponsePayload(
                        type="text",
                        message="Ese recurso no está disponible en ese horario. Elige otro recurso u hora.",
                    )
            else:
                if len(available_resources) == 1:
                    draft["resource_id"] = str(available_resources[0].resource_id)
                elif len(available_resources) > 1:
                    conversation.state["step"] = "select_resource"
                    conversation.state["booking_draft"] = draft
                    return ResponsePayload(
                        type="options",
                        message="Hay varios recursos disponibles. Elige uno",
                        options=[
                            ResponseOption(id=str(item.resource_id), label=item.name)
                            for item in available_resources[:10]
                        ],
                    )
                else:
                    draft["start"] = ""
                    conversation.state["step"] = "select_datetime"
                    conversation.state["booking_draft"] = draft
                    slot_options = self._build_available_slot_options(
                        tenant_id=tenant_id,
                        draft=draft,
                        services=services,
                        resources=resources,
                    )
                    if slot_options:
                        return ResponsePayload(
                            type="options",
                            message="No hay disponibilidad en ese horario. Elige otra hora",
                            options=slot_options,
                        )
                    return ResponsePayload(
                        type="text",
                        message="No hay disponibilidad en ese horario. ¿Qué otra fecha prefieres?",
                    )

        if not draft["customer_name"].strip():
            conversation.state["step"] = "customer_name"
            conversation.state["booking_draft"] = draft
            return ResponsePayload(type="text", message="Necesito tu nombre")

        if not draft["customer_contact"].strip():
            conversation.state["step"] = "customer_contact"
            conversation.state["booking_draft"] = draft
            return ResponsePayload(type="text", message="Teléfono de contacto")

        if conversation.state.get("step") != "confirm_booking":
            conversation.state["step"] = "confirm_booking"
            conversation.state["booking_draft"] = draft
            return self._build_confirmation_payload(
                draft=draft, services=services, resources=resources
            )

        lower_message = message.lower().strip()
        if self._is_cancel_confirmation_intent(lower_message, action_id):
            self._clear_booking_flow_state(conversation)
            return ResponsePayload(
                type="text", message="Reserva cancelada. Si quieres, empezamos otra."
            )

        if not self._is_confirm_intent(lower_message, action_id):
            return self._build_confirmation_payload(
                draft=draft, services=services, resources=resources
            )

        resource_id = self._parse_uuid(draft["resource_id"])
        customer_name = draft["customer_name"].strip()
        customer_contact = draft["customer_contact"].strip()
        if service_id is None or start is None or resource_id is None:
            conversation.state["booking_draft"] = draft
            return ResponsePayload(
                type="text",
                message="No pude interpretar los datos de la reserva. Reenvía fecha/ids.",
            )

        end = start + timedelta(minutes=selected_service.duration_minutes)
        try:
            response = self.create_booking_use_case.execute(
                CreateBookingRequest(
                    tenant_id=tenant_id,
                    service_id=service_id,
                    resource_id=resource_id,
                    customer_name=customer_name,
                    customer_contact=customer_contact,
                    start=start,
                    end=end,
                )
            )
        except DomainError as exc:
            conversation.state["booking_draft"] = draft
            return ResponsePayload(
                type="text", message=f"No pude crear la reserva: {exc}"
            )

        self._clear_booking_flow_state(conversation)
        conversation.state["last_booking_id"] = str(response.booking_id)
        start_iso = start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        end_iso = end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return ResponsePayload(
            type="text",
            message=(
                f"Reserva confirmada. booking_id={response.booking_id}, "
                f"estado={response.status}, inicio={start_iso}, fin={end_iso}."
            ),
        )

    def _build_confirmation_payload(
        self,
        *,
        draft: dict[str, str],
        services: list[ServiceItem],
        resources: list[ResourceItem],
    ) -> ResponsePayload:
        service_id = self._parse_uuid(draft["service_id"])
        resource_id = self._parse_uuid(draft["resource_id"])
        start = self._parse_datetime(draft["start"])

        service_label = draft["service_id"]
        resource_label = draft["resource_id"]
        for service in services:
            if service_id is not None and service.service_id == service_id:
                service_label = service.name
                break
        for resource in resources:
            if resource_id is not None and resource.resource_id == resource_id:
                resource_label = resource.name
                break

        start_label = draft["start"]
        if start is not None:
            start_label = start.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        return ResponsePayload(
            type="confirmation",
            message=(
                "Confirma tu reserva:\n"
                f"Servicio: {service_label}\n"
                f"Recurso: {resource_label}\n"
                f"Fecha: {start_label}\n"
                f"Nombre: {draft['customer_name']}\n"
                f"Contacto: {draft['customer_contact']}"
            ),
            confirm_label="Confirmar",
            cancel_label="Cancelar",
        )

    def _clear_booking_flow_state(self, conversation: Conversation) -> None:
        conversation.state.pop("flow", None)
        conversation.state.pop("step", None)
        conversation.state.pop("booking_draft", None)

    def _get_booking_draft(self, conversation: Conversation) -> dict[str, str]:
        current = conversation.state.get("booking_draft")
        if isinstance(current, dict):
            return {
                "service_id": str(current.get("service_id", "")),
                "resource_id": str(current.get("resource_id", "")),
                "start": str(current.get("start", "")),
                "customer_name": str(current.get("customer_name", "")),
                "customer_contact": str(current.get("customer_contact", "")),
            }
        return {
            "service_id": "",
            "resource_id": "",
            "start": "",
            "customer_name": "",
            "customer_contact": "",
        }

    def _merge_booking_draft(
        self,
        *,
        draft: dict[str, str],
        message: str,
        action_id: str | None,
        services: list[ServiceItem],
        resources: list[ResourceItem],
    ) -> None:
        selection_input = action_id or message
        service_id = self._resolve_service_id(
            message=selection_input, services=services
        )
        if service_id is not None:
            draft["service_id"] = str(service_id)

        resource_id = self._resolve_resource_id(
            message=selection_input, resources=resources
        )
        if resource_id is not None:
            draft["resource_id"] = str(resource_id)

        start = self._extract_datetime(selection_input)
        if start is None:
            start = self._extract_datetime(message)
        if start is not None:
            draft["start"] = (
                start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            )

        name = self._extract_labeled_value(message, labels=("nombre", "name"))
        if name is not None:
            draft["customer_name"] = name

        contact = self._extract_labeled_value(
            message,
            labels=("contacto", "telefono", "teléfono", "phone"),
        )
        if contact is not None:
            draft["customer_contact"] = contact

    def _resolve_service_id(
        self, *, message: str, services: list[ServiceItem]
    ) -> UUID | None:
        for candidate in self._extract_uuids(message):
            if self._find_service_by_id(services, candidate) is not None:
                return candidate
        normalized_message = self._normalize_text(message)
        for service in services:
            if self._normalize_text(service.name) in normalized_message:
                return service.service_id
        return None

    def _resolve_resource_id(
        self, *, message: str, resources: list[ResourceItem]
    ) -> UUID | None:
        for candidate in self._extract_uuids(message):
            if self._find_resource_by_id(resources, candidate) is not None:
                return candidate
        normalized_message = self._normalize_text(message)
        for resource in resources:
            if self._normalize_text(resource.name) in normalized_message:
                return resource.resource_id
        return None

    def _find_service_by_id(
        self,
        services: list[ServiceItem],
        service_id: UUID,
    ) -> ServiceItem | None:
        for service in services:
            if service.service_id == service_id:
                return service
        return None

    def _find_resource_by_id(
        self,
        resources: list[ResourceItem],
        resource_id: UUID,
    ) -> ResourceItem | None:
        for resource in resources:
            if resource.resource_id == resource_id:
                return resource
        return None

    def _extract_labeled_value(
        self, message: str, *, labels: tuple[str, ...]
    ) -> str | None:
        for label in labels:
            pattern = re.compile(
                rf"{re.escape(label)}\s*[:=]\s*([^,\n;]+)", re.IGNORECASE
            )
            match = pattern.search(message)
            if match:
                value = match.group(1).strip()
                if value:
                    return value
        return None

    def _extract_datetime(self, message: str) -> datetime | None:
        for match in _ISO_DATETIME_PATTERN.finditer(message):
            parsed = self._parse_datetime(match.group(0))
            if parsed is not None:
                return parsed

        lower_message = message.lower()
        natural_match = _NATURAL_DATETIME_PATTERN.search(lower_message)
        if natural_match is None:
            return None

        day_token = natural_match.group(1).lower()
        hour_token = natural_match.group(2)
        minute_token = natural_match.group(3)
        hour = int(hour_token) if hour_token is not None else 9
        minute = int(minute_token) if minute_token is not None else 0
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None

        now_utc = datetime.now(timezone.utc)
        target_date = now_utc.date()
        if day_token in {"mañana", "manana"}:
            target_date = target_date + timedelta(days=1)

        return datetime(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=hour,
            minute=minute,
            tzinfo=timezone.utc,
        )

    def _build_available_slot_options(
        self,
        *,
        tenant_id: str,
        draft: dict[str, str],
        services: list[ServiceItem],
        resources: list[ResourceItem],
    ) -> list[ResponseOption]:
        service_id = self._parse_uuid(draft.get("service_id"))
        if service_id is None:
            return []

        selected_service = self._find_service_by_id(services, service_id)
        if selected_service is None:
            return []

        preferred_resource_id = self._parse_uuid(draft.get("resource_id"))
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        duration = timedelta(minutes=selected_service.duration_minutes)
        candidates: list[datetime] = []

        for day_offset in range(0, 5):
            date = (now + timedelta(days=day_offset)).date()
            for hour in range(10, 20):
                slot_start = datetime(
                    year=date.year,
                    month=date.month,
                    day=date.day,
                    hour=hour,
                    minute=0,
                    tzinfo=timezone.utc,
                )
                if slot_start < now:
                    continue
                slot_end = slot_start + duration
                if slot_end.hour > 20 or (slot_end.hour == 20 and slot_end.minute > 0):
                    continue
                available_resources = self._available_resources_for_slot(
                    tenant_id=tenant_id,
                    resources=resources,
                    slot_start=slot_start,
                    duration_minutes=selected_service.duration_minutes,
                    preferred_resource_id=preferred_resource_id,
                )
                if available_resources:
                    candidates.append(slot_start)
                if len(candidates) >= 3:
                    break
            if len(candidates) >= 3:
                break

        return [
            ResponseOption(
                id=slot.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                label=slot.astimezone(timezone.utc).strftime("%d %b %H:%M"),
            )
            for slot in candidates
        ]

    def _available_resources_for_slot(
        self,
        *,
        tenant_id: str,
        resources: list[ResourceItem],
        slot_start: datetime,
        duration_minutes: int,
        preferred_resource_id: UUID | None = None,
    ) -> list[ResourceItem]:
        if self.list_bookings_use_case is None:
            return []

        bookings = self.list_bookings_use_case.execute(
            ListBookingsRequest(tenant_id=tenant_id)
        )
        slot_end = slot_start + timedelta(minutes=duration_minutes)
        pool = resources
        if preferred_resource_id is not None:
            pool = [
                resource
                for resource in resources
                if resource.resource_id == preferred_resource_id
            ]

        available: list[ResourceItem] = []
        for resource in pool:
            overlaps = any(
                booking.resource_id == resource.resource_id
                and booking.status != "cancelled"
                and slot_start < booking.end
                and booking.start < slot_end
                for booking in bookings
            )
            if not overlaps:
                available.append(resource)
        return available

    def _parse_datetime(self, raw: str) -> datetime | None:
        value = raw.strip()
        if not value:
            return None
        normalized = value.replace(" ", "T")
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _extract_uuids(self, message: str) -> list[UUID]:
        parsed: list[UUID] = []
        for token in _UUID_PATTERN.findall(message):
            value = self._parse_uuid(token)
            if value is not None:
                parsed.append(value)
        return parsed

    def _extract_first_uuid(self, message: str) -> UUID | None:
        uuids = self._extract_uuids(message)
        return uuids[0] if uuids else None

    def _parse_uuid(self, raw: str | None) -> UUID | None:
        if raw is None:
            return None
        value = raw.strip()
        if not value:
            return None
        try:
            return UUID(value)
        except (TypeError, ValueError):
            return None

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.lower().split())
