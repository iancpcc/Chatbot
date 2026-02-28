from fastapi import APIRouter, Depends, HTTPException

from app.presentation.http.schemas.booking_schema import (
    CreateBookingRequest as HttpCreateBookingRequest,
    CreateBookingResponse as HttpCreateBookingResponse,
)
from app.application.dto.create_booking_dto import (
    CreateBookingRequest as DtoCreateBookingRequest,
)

from app.presentation.http.dependencies import (
    get_create_booking_use_case,
)

from app.application.use_cases.create_booking import CreateBooking
from app.domain.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)


router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=HttpCreateBookingResponse)
def create_booking(
    request: HttpCreateBookingRequest,
    use_case: CreateBooking = Depends(get_create_booking_use_case),
):
    try:
        use_case_request = DtoCreateBookingRequest(
            tenant_id=request.tenant_id,
            service_id=request.service_id,
            resource_id=request.resource_id,
            customer_name=request.customer_name,
            customer_contact=request.customer_contact,
            start=request.start,
            end=request.end,
        )

        booking_response = use_case.execute(use_case_request)

        return HttpCreateBookingResponse(
            booking_id=booking_response.booking_id,
            status=booking_response.status,
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=422, detail=str(e))
