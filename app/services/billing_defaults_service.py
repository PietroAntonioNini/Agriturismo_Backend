from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.models.models import BillingDefaults


SINGLE_ID = 1


def get_defaults(db: Session) -> BillingDefaults:
    """Recupera l'unica riga di default di fatturazione. Se non esiste, la crea con i valori di default."""
    obj = db.query(BillingDefaults).limit(1).one_or_none()
    if obj:
        return obj

    # Crea riga iniziale
    obj = BillingDefaults(id=SINGLE_ID)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def upsert_defaults(db: Session, payload: Dict[str, Any], updated_by: Optional[int] = None) -> BillingDefaults:
    """Aggiorna o crea i default di fatturazione.

    payload accetta chiavi: 'tari', 'meterFee', 'unitCosts': { 'electricity', 'water', 'gas' }
    """
    obj = get_defaults(db)

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

    obj.updatedBy = updated_by
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


