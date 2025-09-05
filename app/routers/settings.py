from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import BillingDefaultsRead, BillingDefaultsUpdate
from app.services.billing_defaults_service import get_defaults, upsert_defaults
from app.core.auth import get_current_active_user
from app.models.models import User


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
    user: User = Depends(get_current_active_user),
):
    obj = get_defaults(db)
    return to_read_schema(obj)


@router.put("/billing-defaults", response_model=BillingDefaultsRead, status_code=status.HTTP_200_OK)
async def set_billing_defaults(
    payload: BillingDefaultsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    # Solo admin/manager possono aggiornare
    if user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Not allowed")

    obj = upsert_defaults(db, payload.model_dump(exclude_none=True), updated_by=user.id)
    return to_read_schema(obj)


