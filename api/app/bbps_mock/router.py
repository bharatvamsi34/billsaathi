"""Read-only HTTP endpoints for the MOCK BBPS service (synthetic data only)."""

from fastapi import APIRouter, HTTPException, Response

from app.bbps_mock import MOCK_NOTICE, service
from app.bbps_mock.bills import Bill
from app.bbps_mock.registry import Biller

router = APIRouter(prefix="/api/v1/bbps-mock", tags=["bbps-mock (synthetic)"])


@router.get("/billers")
def billers(response: Response) -> dict[str, object]:
    response.headers["X-Mock"] = MOCK_NOTICE
    return {"mock": MOCK_NOTICE, "billers": list(service.list_billers())}


@router.get("/billers/{biller_id}")
def biller(biller_id: str, response: Response) -> Biller:
    response.headers["X-Mock"] = MOCK_NOTICE
    found = service.get_biller(biller_id)
    if found is None:
        raise HTTPException(404, "unknown biller")
    return found


@router.get("/bills/{biller_id}/{consumer_number}")
def bill(biller_id: str, consumer_number: str, response: Response) -> Bill:
    response.headers["X-Mock"] = MOCK_NOTICE
    found = service.current_bill(biller_id, consumer_number)
    if found is None:
        raise HTTPException(404, "no bill for this biller and consumer number")
    return found


@router.get("/bills/{biller_id}/{consumer_number}/history")
def history(biller_id: str, consumer_number: str, response: Response) -> dict[str, object]:
    response.headers["X-Mock"] = MOCK_NOTICE
    found = service.bill_history(biller_id, consumer_number)
    if found is None:
        raise HTTPException(404, "no bills for this biller and consumer number")
    return {"mock": MOCK_NOTICE, "bills": found}
