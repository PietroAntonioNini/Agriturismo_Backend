from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import BillingDefaultsRead, BillingDefaultsUpdate, InvoiceAutomationRead, InvoiceAutomationUpdate
from app.core.auth import get_current_user
from app.models.models import User
from app.services.billing_defaults_service import get_defaults, upsert_defaults

router = APIRouter(prefix="/settings", tags=["settings"])


def to_read_schema(obj) -> BillingDefaultsRead:
    return BillingDefaultsRead(
        tari=float(obj.tari),
        meterFee=float(obj.meterFee),
        unitCosts={
            "electricity": float(obj.unitCostElectricity),
            "water": float(obj.unitCostWater),
            "gas": float(obj.unitCostGas),
        },
    )


@router.get("/billing-defaults", response_model=BillingDefaultsRead)
async def get_billing_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    obj = get_defaults(db, user_id=current_user.id)
    return to_read_schema(obj)


@router.put("/billing-defaults", response_model=BillingDefaultsRead, status_code=status.HTTP_200_OK)
async def set_billing_defaults(
    payload: BillingDefaultsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    obj = upsert_defaults(db, payload.model_dump(exclude_none=True), user_id=current_user.id, updated_by=current_user.id)
    return to_read_schema(obj)


@router.get("/automation", response_model=InvoiceAutomationRead)
async def get_automation_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    obj = get_defaults(db, user_id=current_user.id)
    return InvoiceAutomationRead(
        automationType=obj.automationType,
        automationDays=obj.automationDays
    )


@router.put("/automation", response_model=InvoiceAutomationRead)
async def set_automation_settings(
    payload: InvoiceAutomationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    obj = upsert_defaults(db, payload.model_dump(exclude_none=True), user_id=current_user.id, updated_by=current_user.id)
    return InvoiceAutomationRead(
        automationType=obj.automationType,
        automationDays=obj.automationDays
    )


