from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import BillingDefaultsRead, BillingDefaultsUpdate
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
):
    obj = get_defaults(db)
    return to_read_schema(obj)


@router.put("/billing-defaults", response_model=BillingDefaultsRead, status_code=status.HTTP_200_OK)
async def set_billing_defaults(
    payload: BillingDefaultsUpdate,
    db: Session = Depends(get_db),
):
    obj = upsert_defaults(db, payload.model_dump(exclude_none=True), updated_by=None)
    return to_read_schema(obj)


