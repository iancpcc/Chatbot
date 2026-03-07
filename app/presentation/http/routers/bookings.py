from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.presentation.http.schemas.booking_schema import (
    CreateBookingRequest as HttpCreateBookingRequest,
    CreateBookingResponse as HttpCreateBookingResponse,
    BookingItemResponse as HttpBookingItemResponse,
)
from app.application.dto.create_booking_dto import (
    CreateBookingRequest as DtoCreateBookingRequest,
)

from app.presentation.http.dependencies import (
    get_cancel_booking_use_case,
    get_create_booking_use_case,
    get_get_booking_use_case,
    get_list_bookings_use_case,
)

from app.application.use_cases.cancel_booking import CancelBooking
from app.application.use_cases.create_booking import CreateBooking
from app.application.use_cases.get_booking import GetBooking
from app.application.use_cases.list_bookings import (
    ListBookings,
    ListBookingsRequest,
)


router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=HttpCreateBookingResponse)
def create_booking(
    request: HttpCreateBookingRequest,
    use_case: CreateBooking = Depends(get_create_booking_use_case),
):
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


@router.get("", response_model=list[HttpBookingItemResponse])
def list_bookings(
    tenant_id: str = Query(...),
    resource_id: UUID | None = Query(None),
    start_from: datetime | None = Query(None),
    end_to: datetime | None = Query(None),
    use_case: ListBookings = Depends(get_list_bookings_use_case),
):
    result = use_case.execute(
        ListBookingsRequest(
            tenant_id=tenant_id,
            resource_id=resource_id,
            start_from=start_from,
            end_to=end_to,
        )
    )
    return [
        HttpBookingItemResponse(
            booking_id=item.booking_id,
            tenant_id=item.tenant_id,
            service_id=item.service_id,
            resource_id=item.resource_id,
            customer_name=item.customer_name,
            customer_contact=item.customer_contact,
            start=item.start,
            end=item.end,
            status=item.status,
        )
        for item in result
    ]


@router.get("/{booking_id}", response_model=HttpBookingItemResponse)
def get_booking(
    booking_id: UUID,
    tenant_id: str = Query(...),
    use_case: GetBooking = Depends(get_get_booking_use_case),
):
    item = use_case.execute(tenant_id=tenant_id, booking_id=booking_id)
    return HttpBookingItemResponse(
        booking_id=item.booking_id,
        tenant_id=item.tenant_id,
        service_id=item.service_id,
        resource_id=item.resource_id,
        customer_name=item.customer_name,
        customer_contact=item.customer_contact,
        start=item.start,
        end=item.end,
        status=item.status,
    )


@router.patch("/{booking_id}/cancel", response_model=HttpBookingItemResponse)
def cancel_booking(
    booking_id: UUID,
    tenant_id: str = Query(...),
    cancel_use_case: CancelBooking = Depends(get_cancel_booking_use_case),
    get_use_case: GetBooking = Depends(get_get_booking_use_case),
):
    cancel_use_case.execute(tenant_id=tenant_id, booking_id=booking_id)
    item = get_use_case.execute(tenant_id=tenant_id, booking_id=booking_id)
    return HttpBookingItemResponse(
        booking_id=item.booking_id,
        tenant_id=item.tenant_id,
        service_id=item.service_id,
        resource_id=item.resource_id,
        customer_name=item.customer_name,
        customer_contact=item.customer_contact,
        start=item.start,
        end=item.end,
        status=item.status,
    )
