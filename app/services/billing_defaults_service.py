from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.models.models import BillingDefaults


def get_defaults(db: Session, user_id: int) -> BillingDefaults:
    """Recupera la riga di default di fatturazione per l'utente. Se non esiste, la crea con i valori di default."""
    obj = db.query(BillingDefaults).filter(BillingDefaults.userId == user_id).first()
    if obj:
        return obj

    # Crea riga iniziale per l'utente
    obj = BillingDefaults(
        userId=user_id,
        tari=15.00,
        meterFee=3.00,
        unitCostElectricity=0.75,
        unitCostWater=3.40,
        unitCostGas=4.45
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def upsert_defaults(db: Session, payload: Dict[str, Any], user_id: int, updated_by: Optional[int] = None) -> BillingDefaults:
    """Aggiorna o crea i default di fatturazione per l'utente.

    payload accetta chiavi: 'tari', 'meterFee', 'unitCosts': { 'electricity', 'water', 'gas' }
    """
    obj = get_defaults(db, user_id)

    # Aggiorna valori se presenti
    if payload.get("tari") is not None:
        obj.tari = payload["tari"]
    if payload.get("meterFee") is not None:
        obj.meterFee = payload["meterFee"]

    unit = payload.get("unitCosts") or {}
    if isinstance(unit, dict):
        if unit.get("electricity") is not None:
            obj.unitCostElectricity = unit["electricity"]
        if unit.get("water") is not None:
            obj.unitCostWater = unit["water"]
        if unit.get("gas") is not None:
            obj.unitCostGas = unit["gas"]

    obj.updatedBy = updated_by or user_id
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


