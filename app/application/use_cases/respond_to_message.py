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
_DATE_TODAY_OPTION = "date_today"
_DATE_TOMORROW_OPTION = "date_tomorrow"
_DATE_OTHER_OPTION = "date_other"
_ASSISTANT_CHAT_OPTION = "assistant_chat"
_BACK_OPTION = "back_to_menu"
_CONFIRM_BOOKING_OPTION = "booking_confirm"
_CHANGE_TIME_OPTION = "booking_change_time"
_CANCEL_BOOKING_OPTION = "booking_cancel"
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

        if self._is_global_back_command(message, action_id):
            payload = self._handle_global_back(conversation)
            self._append_message(conversation, role="assistant", content=payload.message)
            self.conversation_repository.save(conversation)
            return RespondToMessageResponse(
                conversation_id=conversation.id,
                reply=payload.message,
                response=payload,
            )

        payload = self._try_handle_transactional_message(
            request=request,
            conversation=conversation,
            message=input_text,
            action_id=action_id or None,
        )
        if payload is None:
            if str(conversation.state.get("flow", "")).lower() == "assistant":
                payload = self._handle_assistant_chat(
                    request=request, conversation=conversation, message=message
                )
            else:
                payload = self._handle_assistant_entry(
                    request=request,
                    conversation=conversation,
                    message=message,
                    action_id=action_id or None,
                )

        if payload is None:
            llm_messages = self._build_llm_messages(
                conversation=conversation,
                tenant_id=request.tenant_id,
                user_message=message,
            )
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

    def _build_llm_messages(
        self,
        *,
        conversation: Conversation,
        tenant_id: str,
        user_message: str,
    ) -> list[dict[str, str]]:
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
        selected_value = self._resolve_selected_value(
            conversation=conversation,
            message=message,
            action_id=action_id,
        )
        lower_selected_value = selected_value.lower().strip()
        effective_action_id = action_id or (
            selected_value if selected_value != message.strip() else None
        )

        if (
            selected_value == _ASSISTANT_CHAT_OPTION
            or self._is_assistant_intent(lower_message)
        ):
            conversation.state["flow"] = "assistant"
            conversation.state["step"] = "assistant_chat"
            conversation.state.pop("booking_draft", None)
            conversation.state.pop("active_options", None)
            return ResponsePayload(
                type="text",
                message=(
                    "Perfecto. Estás hablando con el asistente.\n"
                    "Escribe tu consulta y te respondo. Para volver al menú, escribe 'menu'."
                ),
            )

        if (
            flow == "booking"
            or selected_value == "booking"
            or (self._is_booking_intent(lower_message) and not self._is_cancel_intent(lower_message))
        ):
            if selected_value == _BACK_OPTION:
                return self._handle_global_back(conversation)
            return self._handle_create_booking(
                tenant_id=request.tenant_id,
                conversation=conversation,
                message=selected_value if selected_value else message,
                action_id=effective_action_id,
            )

        if selected_value == "catalog" or self._is_catalog_intent(lower_message):
            return self._render_catalog(request.tenant_id)

        if selected_value == "my_bookings" or self._is_list_bookings_intent(
            lower_message
        ):
            return self._render_bookings(request.tenant_id)

        if selected_value == _BACK_OPTION:
            return self._handle_global_back(conversation)

        if self._is_cancel_intent(lower_message):
            if flow == "booking" or self._extract_first_uuid(selected_value):
                return self._handle_cancel(request.tenant_id, conversation, selected_value)
            return self._render_main_menu(conversation)

        if self._is_greeting_intent(lower_message) or lower_selected_value == "hola":
            return self._render_main_menu(conversation)

        return None

    def _handle_assistant_entry(
        self,
        *,
        request: RespondToMessageRequest,
        conversation: Conversation,
        message: str,
        action_id: str | None,
    ) -> ResponsePayload | None:
        if action_id == _ASSISTANT_CHAT_OPTION or self._is_assistant_intent(
            message.lower()
        ):
            conversation.state["flow"] = "assistant"
            conversation.state["step"] = "assistant_chat"
            conversation.state.pop("booking_draft", None)
            conversation.state.pop("active_options", None)
            return ResponsePayload(
                type="text",
                message=(
                    "Perfecto. Estás hablando con el asistente.\n"
                    "Escribe tu consulta y te respondo. Para volver al menú, escribe 'menu'."
                ),
            )

        if self._is_booking_intent(message.lower()):
            return self._handle_create_booking(
                tenant_id=request.tenant_id,
                conversation=conversation,
                message=message,
                action_id=action_id,
            )

        if self._is_catalog_intent(message.lower()):
            return self._render_catalog(request.tenant_id)

        if self._is_list_bookings_intent(message.lower()):
            return self._render_bookings(request.tenant_id)

        if self._is_greeting_intent(message.lower()):
            return self._render_main_menu(conversation)

        return None

    def _handle_assistant_chat(
        self,
        *,
        request: RespondToMessageRequest,
        conversation: Conversation,
        message: str,
    ) -> ResponsePayload:
        if message.lower().strip() == "menu":
            conversation.state.pop("flow", None)
            conversation.state.pop("step", None)
            conversation.state.pop("active_options", None)
            return self._render_main_menu(conversation)

        llm_messages = self._build_llm_messages(
            conversation=conversation,
            tenant_id=request.tenant_id,
            user_message=message,
        )
        try:
            llm_reply = self.llm_client.generate_reply(messages=llm_messages)
        except InfrastructureError:
            raise
        except Exception as exc:
            raise InfrastructureError(str(exc)) from exc
        return ResponsePayload(type="text", message=llm_reply)

    def _is_global_back_command(self, message: str, action_id: str | None) -> bool:
        normalized_message = message.lower().strip()
        normalized_action = (action_id or "").strip().lower()
        return normalized_action in {"back", "menu", "home"} or normalized_message in {
            "volver",
            "atrás",
            "atras",
            "menu",
            "inicio",
            "volver al menú",
        }

    def _handle_global_back(self, conversation: Conversation) -> ResponsePayload:
        history = conversation.state.get("wizard_history")
        if not isinstance(history, list) or not history:
            self._clear_booking_flow_state(conversation)
            return self._render_main_menu(conversation)

        previous_step = str(history.pop() or "").strip()
        if not previous_step:
            self._clear_booking_flow_state(conversation)
            return self._render_main_menu(conversation)

        conversation.state["wizard_history"] = history
        conversation.state["suppress_history_push"] = True
        return self._render_step_from_history(conversation, previous_step)

    def _render_step_from_history(
        self, conversation: Conversation, step: str
    ) -> ResponsePayload:
        draft = self._get_booking_draft(conversation)

        if step == "main_menu":
            self._clear_booking_flow_state(conversation)
            return self._render_main_menu(conversation)

        if step == "select_service":
            services = self.list_services_use_case.execute(
                ListServicesRequest(tenant_id=conversation.tenant_id)
            )
            return self._build_option_payload(
                conversation=conversation,
                step="select_service",
                prompt="Perfecto. ¿Qué servicio deseas?",
                options=[
                    ResponseOption(
                        id=str(service.service_id),
                        label=(
                            f"{service.name} - ${service.price:.2f} - "
                            f"{service.duration_minutes} min"
                        ),
                    )
                    for service in services[:10]
                ],
                include_back_option=True,
            )

        if step == "select_date":
            services = self.list_services_use_case.execute(
                ListServicesRequest(tenant_id=conversation.tenant_id)
            )
            resources = self.list_resources_use_case.execute(
                ListResourcesRequest(tenant_id=conversation.tenant_id)
            )
            return self._build_option_payload(
                conversation=conversation,
                step="select_date",
                prompt="Genial.\nSelecciona una fecha:",
                options=self._build_date_choice_options(
                    tenant_id=conversation.tenant_id,
                    draft=draft,
                    services=services,
                    resources=resources,
                ),
                include_back_option=True,
            )

        if step == "select_time":
            services = self.list_services_use_case.execute(
                ListServicesRequest(tenant_id=conversation.tenant_id)
            )
            resources = self.list_resources_use_case.execute(
                ListResourcesRequest(tenant_id=conversation.tenant_id)
            )
            selected_date = self._parse_datetime(draft.get("selected_date", ""))
            if selected_date is None:
                selected_date = self._parse_datetime(draft.get("start", ""))
            slot_options = self._build_available_slot_options(
                tenant_id=conversation.tenant_id,
                draft=draft,
                services=services,
                resources=resources,
                selected_date=selected_date,
            )
            date_label = self._format_relative_date_label(selected_date)
            return self._build_option_payload(
                conversation=conversation,
                step="select_time",
                prompt=f"Disponibilidad para {date_label.lower()}:",
                options=slot_options,
                include_back_option=True,
            )

        if step == "select_resource":
            services = self.list_services_use_case.execute(
                ListServicesRequest(tenant_id=conversation.tenant_id)
            )
            resources = self.list_resources_use_case.execute(
                ListResourcesRequest(tenant_id=conversation.tenant_id)
            )
            service_id = self._parse_uuid(draft.get("service_id"))
            start = self._parse_datetime(draft.get("start", ""))
            if service_id is None or start is None:
                return self._render_main_menu(conversation)

            selected_service = self._find_service_by_id(services, service_id)
            if selected_service is None:
                return self._render_main_menu(conversation)

            available_resources = self._available_resources_for_slot(
                tenant_id=conversation.tenant_id,
                resources=resources,
                slot_start=start,
                duration_minutes=selected_service.duration_minutes,
            )
            return self._build_option_payload(
                conversation=conversation,
                step="select_resource",
                prompt="Hay varios recursos disponibles. Elige uno",
                options=[
                    ResponseOption(id=str(item.resource_id), label=item.name)
                    for item in available_resources[:10]
                ],
                include_back_option=True,
            )

        if step == "confirm_booking":
            services = self.list_services_use_case.execute(
                ListServicesRequest(tenant_id=conversation.tenant_id)
            )
            resources = self.list_resources_use_case.execute(
                ListResourcesRequest(tenant_id=conversation.tenant_id)
            )
            return self._build_confirmation_payload(
                conversation=conversation,
                draft=draft,
                services=services,
                resources=resources,
            )

        return self._render_main_menu(conversation)

    def _is_booking_intent(self, lower_message: str) -> bool:
        return any(
            keyword in lower_message for keyword in ("reserv", "agend", "cita", "book")
        )

    def _is_cancel_intent(self, lower_message: str) -> bool:
        return bool(
            re.search(r"\b(cancelar|cancel|anular|anul)\b", lower_message, re.IGNORECASE)
        )

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

    def _is_assistant_intent(self, lower_message: str) -> bool:
        return any(
            keyword in lower_message
            for keyword in ("asistente", "chat", "conversar", "hablar")
        )

    def _render_main_menu(self, conversation: Conversation) -> ResponsePayload:
        return self._build_option_payload(
            conversation=conversation,
            step="main_menu",
            prompt="¡Hola! Bienvenida a Nails Studio\n¿En qué puedo ayudarte?",
            options=[
                ResponseOption(id="booking", label="Reservar cita"),
                ResponseOption(id="catalog", label="Ver servicios"),
                ResponseOption(id="my_bookings", label="Mis citas"),
                ResponseOption(id=_ASSISTANT_CHAT_OPTION, label="Chatear con asistente"),
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

        current_step = conversation.state.get("step")
        conversation.state["flow"] = "booking"
        draft = self._get_booking_draft(conversation)
        if not draft["customer_contact"].strip():
            draft["customer_contact"] = conversation.user_id
        self._merge_booking_draft(
            draft=draft,
            message=message,
            action_id=action_id,
            services=services,
            resources=resources,
            step=current_step,
        )

        if not draft["service_id"].strip():
            conversation.state["booking_draft"] = draft
            return self._build_option_payload(
                conversation=conversation,
                step="select_service",
                prompt="Perfecto. ¿Qué servicio deseas?",
                options=[
                    ResponseOption(
                        id=str(service.service_id),
                        label=(
                            f"{service.name} - ${service.price:.2f} - "
                            f"{service.duration_minutes} min"
                        ),
                    )
                    for service in services[:10]
                ],
                include_back_option=True,
            )

        if not draft["start"].strip() and current_step not in {
            "select_date",
            "select_datetime",
            "select_time",
        }:
            conversation.state["booking_draft"] = draft
            return self._build_option_payload(
                conversation=conversation,
                step="select_date",
                prompt="Genial.\nSelecciona una fecha:",
                options=self._build_date_choice_options(
                    tenant_id=tenant_id,
                    draft=draft,
                    services=services,
                    resources=resources,
                ),
                include_back_option=True,
            )

        if not draft["start"].strip():
            conversation.state["booking_draft"] = draft
            selected_date = self._resolve_selected_date(
                message=message,
                action_id=action_id,
            )
            slot_options = self._build_available_slot_options(
                tenant_id=tenant_id,
                draft=draft,
                services=services,
                resources=resources,
                selected_date=selected_date,
            )
            if slot_options:
                date_label = self._format_relative_date_label(selected_date)
                return self._build_option_payload(
                    conversation=conversation,
                    step="select_time",
                    prompt=f"Disponibilidad para {date_label.lower()}:",
                    options=slot_options,
                    include_back_option=True,
                )
            conversation.state["step"] = "select_datetime"
            if action_id == _DATE_OTHER_OPTION:
                return ResponsePayload(
                    type="text",
                    message=(
                        "Escribe la fecha que prefieres en formato YYYY-MM-DD.\n"
                        "También puedes escribir 'volver' para regresar al menú."
                    ),
                )
            return ResponsePayload(
                type="text",
                message=(
                    "¿Qué día te viene bien? Puedes escribir 'mañana a las 10' "
                    "o una fecha YYYY-MM-DD.\n"
                    "Escribe 'volver' para regresar al menú."
                ),
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
                    item.resource_id == parsed_resource_id
                    for item in available_resources
                ):
                    draft["resource_id"] = ""
                    conversation.state["step"] = "select_resource"
                    conversation.state["booking_draft"] = draft
                    return ResponsePayload(
                        type="text",
                        message=(
                            "Ese recurso no está disponible en ese horario. "
                            "Elige otro recurso u hora o escribe 'volver'."
                        ),
                    )
            else:
                if len(available_resources) == 1:
                    draft["resource_id"] = str(available_resources[0].resource_id)
                elif len(available_resources) > 1:
                    conversation.state["booking_draft"] = draft
                    return self._build_option_payload(
                        conversation=conversation,
                        step="select_resource",
                        prompt="Hay varios recursos disponibles. Elige uno",
                        options=[
                            ResponseOption(id=str(item.resource_id), label=item.name)
                            for item in available_resources[:10]
                        ],
                        include_back_option=True,
                    )
                else:
                    draft["start"] = ""
                    conversation.state["booking_draft"] = draft
                    slot_options = self._build_available_slot_options(
                        tenant_id=tenant_id,
                        draft=draft,
                        services=services,
                        resources=resources,
                        selected_date=None,
                    )
                    if slot_options:
                        return self._build_option_payload(
                            conversation=conversation,
                            step="select_time",
                            prompt="No hay disponibilidad en ese horario. Elige otra hora",
                            options=slot_options,
                            include_back_option=True,
                        )
                    conversation.state["step"] = "select_datetime"
                    return ResponsePayload(
                        type="text",
                        message=(
                            "No hay disponibilidad en ese horario. "
                            "¿Qué otra fecha prefieres? También puedes escribir 'volver'."
                        ),
                    )

        if not draft["customer_name"].strip():
            conversation.state["step"] = "customer_name"
            conversation.state["booking_draft"] = draft
            return ResponsePayload(
                type="text",
                message="Ahora necesito tu nombre. Escribe 'volver' para regresar al menú.",
            )

        if conversation.state.get("step") != "confirm_booking":
            conversation.state["booking_draft"] = draft
            return self._build_confirmation_payload(
                conversation=conversation,
                draft=draft,
                services=services,
                resources=resources,
            )

        lower_message = message.lower().strip()
        if action_id == _CANCEL_BOOKING_OPTION or self._is_cancel_confirmation_intent(
            lower_message, action_id
        ):
            self._clear_booking_flow_state(conversation)
            return ResponsePayload(
                type="text", message="Reserva cancelada. Si quieres, empezamos otra."
            )

        if action_id == _CHANGE_TIME_OPTION:
            draft["start"] = ""
            draft["resource_id"] = ""
            conversation.state["booking_draft"] = draft
            return self._build_option_payload(
                conversation=conversation,
                step="select_date",
                prompt="Perfecto. Selecciona una nueva fecha:",
                options=self._build_date_choice_options(
                    tenant_id=tenant_id,
                    draft=draft,
                    services=services,
                    resources=resources,
                ),
                include_back_option=True,
            )

        if not self._is_confirm_intent(lower_message, action_id):
            return self._build_confirmation_payload(
                conversation=conversation,
                draft=draft,
                services=services,
                resources=resources,
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
        return ResponsePayload(
            type="text",
            message=(
                "Reserva confirmada.\n\n"
                f"Fecha: {self._format_human_slot(start)}\n"
                f"Servicio: {selected_service.name}\n"
                f"Nombre: {customer_name}\n"
                "Se enviará un recordatorio 30 min antes para confirmar la cita.\n"
                f"booking_id={response.booking_id}"
            ),
        )

    def _build_confirmation_payload(
        self,
        *,
        conversation: Conversation,
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
            start_label = self._format_human_slot(start)

        price_line = ""
        for service in services:
            if service_id is not None and service.service_id == service_id:
                price_line = f"\nPrecio: ${service.price:.2f}"
                break

        return self._build_option_payload(
            conversation=conversation,
            step="confirm_booking",
            prompt=(
                "Gracias.\n\n"
                f"Fecha: {start_label}\n"
                f"Servicio: {service_label}{price_line}\n"
                f"Recurso: {resource_label}\n"
                f"Nombre: {draft['customer_name']}\n\n"
                "¿Deseas confirmar tu cita?"
            ),
            options=[
                ResponseOption(id=_CONFIRM_BOOKING_OPTION, label="Sí confirmar"),
                ResponseOption(id=_CHANGE_TIME_OPTION, label="Cambiar horario"),
                ResponseOption(id=_CANCEL_BOOKING_OPTION, label="Cancelar"),
            ],
            include_back_option=True,
        )

    def _clear_booking_flow_state(self, conversation: Conversation) -> None:
        conversation.state.pop("flow", None)
        conversation.state.pop("step", None)
        conversation.state.pop("booking_draft", None)
        conversation.state.pop("active_options", None)
        conversation.state.pop("wizard_history", None)

    def _get_booking_draft(self, conversation: Conversation) -> dict[str, str]:
        current = conversation.state.get("booking_draft")
        if isinstance(current, dict):
            return {
                "service_id": str(current.get("service_id", "")),
                "resource_id": str(current.get("resource_id", "")),
                "start": str(current.get("start", "")),
                "customer_name": str(current.get("customer_name", "")),
                "customer_contact": str(current.get("customer_contact", "")),
                "selected_date": str(current.get("selected_date", "")),
            }
        return {
            "service_id": "",
            "resource_id": "",
            "start": "",
            "customer_name": "",
            "customer_contact": "",
            "selected_date": "",
        }

    def _merge_booking_draft(
        self,
        *,
        draft: dict[str, str],
        message: str,
        action_id: str | None,
        services: list[ServiceItem],
        resources: list[ResourceItem],
        step: str | None = None,
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

        selected_date = self._resolve_selected_date(message=message, action_id=action_id)
        if selected_date is not None:
            draft["selected_date"] = selected_date.isoformat()

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
        elif step == "customer_name" and message.strip():
            draft["customer_name"] = message.strip()

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
        selected_date: datetime | None,
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
        candidates: list[tuple[datetime, int]] = []

        dates = [selected_date.date()] if selected_date is not None else []
        if not dates:
            dates = [(now + timedelta(days=day_offset)).date() for day_offset in range(0, 5)]

        for date in dates:
            availability_count = 0
            slots_for_date: list[datetime] = []
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
                    availability_count += 1
                    slots_for_date.append(slot_start)
            if selected_date is not None:
                candidates.extend((slot, availability_count) for slot in slots_for_date)
                break
            if availability_count > 0:
                best_slot = slots_for_date[0]
                candidates.append((best_slot, availability_count))

        if selected_date is None:
            candidates.sort(
                key=lambda item: (-item[1], item[0].astimezone(timezone.utc))
            )

        options: list[ResponseOption] = []
        for slot, availability_count in candidates[:3]:
            label = slot.astimezone(timezone.utc).strftime("%H:%M")
            if selected_date is None:
                label = f"{label} - {availability_count} disponibles"
            options.append(
                ResponseOption(
                    id=slot.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    label=label,
                )
            )
        return options

    def _build_date_choice_options(
        self,
        *,
        tenant_id: str,
        draft: dict[str, str],
        services: list[ServiceItem],
        resources: list[ResourceItem],
    ) -> list[ResponseOption]:
        today = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        choices = [
            (_DATE_TODAY_OPTION, today, "Hoy"),
            (_DATE_TOMORROW_OPTION, today + timedelta(days=1), "Mañana"),
            (_DATE_OTHER_OPTION, None, "Elegir otra fecha"),
        ]

        scored_choices: list[tuple[int, ResponseOption]] = []
        for option_id, date_value, base_label in choices:
            if option_id == _DATE_OTHER_OPTION:
                continue

            slot_options = self._build_available_slot_options(
                tenant_id=tenant_id,
                draft=draft,
                services=services,
                resources=resources,
                selected_date=date_value,
            )
            count = len(slot_options)
            if count == 0:
                continue
            label = f"{base_label} ({count} disponibles)"
            scored_choices.append((count, ResponseOption(id=option_id, label=label)))

        scored_choices.sort(key=lambda item: (-item[0], item[1].id))
        options = [item[1] for item in scored_choices]
        if not options:
            options.append(ResponseOption(id=_DATE_OTHER_OPTION, label="Elegir otra fecha"))
        return options

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

    def _build_option_payload(
        self,
        *,
        conversation: Conversation,
        step: str,
        prompt: str,
        options: list[ResponseOption],
        include_back_option: bool = False,
    ) -> ResponsePayload:
        rendered_options = list(options)
        if include_back_option:
            rendered_options.append(ResponseOption(id=_BACK_OPTION, label="Volver"))

        history = conversation.state.get("wizard_history")
        if not isinstance(history, list):
            history = []
        if not conversation.state.pop("suppress_history_push", False):
            current_step = conversation.state.get("step")
            if isinstance(current_step, str) and current_step:
                history = list(history)
                if not history or history[-1] != current_step:
                    history.append(current_step)
        conversation.state["wizard_history"] = history
        conversation.state["step"] = step
        conversation.state["active_options"] = {
            "step": step,
            "map": {
                str(index): option.id
                for index, option in enumerate(rendered_options, start=1)
            },
        }
        return ResponsePayload(
            type="options",
            message=prompt,
            options=rendered_options,
        )

    def _resolve_selected_value(
        self,
        *,
        conversation: Conversation,
        message: str,
        action_id: str | None,
    ) -> str:
        if action_id:
            return action_id.strip()

        active_options = conversation.state.get("active_options")
        if not isinstance(active_options, dict):
            return message.strip()

        option_map = active_options.get("map")
        if not isinstance(option_map, dict):
            return message.strip()

        return str(option_map.get(message.strip(), message.strip()))

    def _resolve_selected_date(
        self, *, message: str, action_id: str | None
    ) -> datetime | None:
        normalized = (action_id or message).strip().lower()
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        if normalized == _DATE_TODAY_OPTION:
            return now
        if normalized == _DATE_TOMORROW_OPTION:
            return now + timedelta(days=1)
        if normalized == _DATE_OTHER_OPTION:
            return None

        parsed = self._parse_datetime(message)
        if parsed is not None:
            return parsed

        raw = message.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return self._parse_datetime(f"{raw}T09:00:00Z")
        return None

    def _format_relative_date_label(self, value: datetime | None) -> str:
        if value is None:
            return "la fecha seleccionada"
        today = datetime.now(timezone.utc).date()
        if value.date() == today:
            return "Hoy"
        if value.date() == today + timedelta(days=1):
            return "Mañana"
        return value.strftime("%Y-%m-%d")

    def _format_human_slot(self, value: datetime) -> str:
        return (
            f"{self._format_relative_date_label(value)} "
            f"{value.astimezone(timezone.utc).strftime('%H:%M')}"
        )
