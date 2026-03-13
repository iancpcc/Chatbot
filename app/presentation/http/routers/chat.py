from fastapi import APIRouter, Depends

from app.application.dto.respond_to_message_dto import ResponsePayload, RespondToMessageRequest
from app.application.use_cases.respond_to_message import RespondToMessage
from app.presentation.http.dependencies import get_respond_to_message_use_case
from app.presentation.http.schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    ChatResponseOption,
    ChatResponsePayload,
)


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    use_case: RespondToMessage = Depends(get_respond_to_message_use_case),
):
    result = use_case.execute(
        RespondToMessageRequest(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            channel=request.channel,
            message=request.message,
            conversation_id=request.conversation_id,
            action_id=request.action_id,
        )
    )
    return ChatResponse(
        conversation_id=result.conversation_id,
        reply=result.reply,
        response=_to_http_payload(result.response),
    )


def _to_http_payload(payload: ResponsePayload | None) -> ChatResponsePayload | None:
    if payload is None:
        return None
    options = None
    if payload.options is not None:
        options = [ChatResponseOption(id=item.id, label=item.label) for item in payload.options]
    return ChatResponsePayload(
        type=payload.type,
        message=payload.message,
        text=payload.message,
        options=options,
        confirm_label=payload.confirm_label,
        cancel_label=payload.cancel_label,
    )
