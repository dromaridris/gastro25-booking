"""Endoscopy consumables inventory — Sprint 7C."""

from __future__ import annotations

from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.dept_ops.constants import ALL_CONSUMABLE_CATEGORIES, STOCK_ADJUSTMENT, STOCK_RECEIPT, STOCK_USAGE
from app.modules.dept_ops.models import ConsumableItem, ConsumableStockMovement, ProcedureConsumablePlan


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_consumables(acting_user) -> list[ConsumableItem]:
    _require(acting_user, "dept_ops:view")
    return ConsumableItem.query.filter_by(is_archived=False).order_by(ConsumableItem.name.asc()).all()


def low_stock_items(acting_user) -> list[ConsumableItem]:
    _require(acting_user, "dept_ops:view")
    return [
        c for c in list_consumables(acting_user) if c.current_stock <= c.minimum_stock
    ]


def create_consumable(
    acting_user,
    *,
    name: str,
    category: str,
    current_stock: int = 0,
    minimum_stock: int = 0,
    unit: str = "each",
) -> ConsumableItem:
    _require(acting_user, "dept_ops:consumable_manage")
    if category not in ALL_CONSUMABLE_CATEGORIES:
        raise ValidationError(f"Invalid consumable category '{category}'.")
    name_clean = name.strip()
    if ConsumableItem.query.filter_by(name=name_clean).first():
        raise ValidationError(f"Consumable '{name_clean}' already exists.")
    item = ConsumableItem(
        name=name_clean,
        category=category,
        current_stock=current_stock,
        minimum_stock=minimum_stock,
        unit=unit,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(item)
    db.session.commit()
    return item


def record_stock_movement(
    acting_user,
    consumable: ConsumableItem,
    movement_type: str,
    quantity: int,
    *,
    procedure_id: int | None = None,
    notes: str | None = None,
) -> ConsumableStockMovement:
    _require(acting_user, "dept_ops:consumable_manage")
    if movement_type not in {STOCK_USAGE, STOCK_RECEIPT, STOCK_ADJUSTMENT}:
        raise ValidationError("Invalid movement type.")
    if quantity <= 0:
        raise ValidationError("Quantity must be positive.")
    if movement_type == STOCK_USAGE:
        if consumable.current_stock < quantity:
            raise ValidationError("Insufficient stock.")
        consumable.current_stock -= quantity
    elif movement_type == STOCK_RECEIPT:
        consumable.current_stock += quantity
    else:
        consumable.current_stock = quantity
    movement = ConsumableStockMovement(
        consumable_id=consumable.id,
        movement_type=movement_type,
        quantity=quantity,
        procedure_id=procedure_id,
        notes=notes,
        recorded_by_id=acting_user.id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(movement)
    audit_engine.log(
        "dept_ops.consumable_movement",
        user=acting_user,
        target_type="consumable_item",
        target_id=consumable.id,
        details={"type": movement_type, "quantity": quantity, "stock": consumable.current_stock},
    )
    db.session.commit()
    return movement


def plan_procedure_consumable(
    acting_user, procedure_id: int, consumable_id: int, quantity: int = 1
) -> ProcedureConsumablePlan:
    _require(acting_user, "dept_ops:consumable_manage")
    if quantity <= 0:
        raise ValidationError("Quantity must be positive.")
    existing = ProcedureConsumablePlan.query.filter_by(
        procedure_id=procedure_id, consumable_id=consumable_id, is_archived=False
    ).first()
    if existing:
        existing.quantity = quantity
        db.session.commit()
        return existing
    plan = ProcedureConsumablePlan(
        procedure_id=procedure_id,
        consumable_id=consumable_id,
        quantity=quantity,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def list_procedure_plans(acting_user, procedure_id: int) -> list[ProcedureConsumablePlan]:
    _require(acting_user, "dept_ops:view")
    return ProcedureConsumablePlan.query.filter_by(
        procedure_id=procedure_id, is_archived=False
    ).all()


def deduct_planned_consumables(acting_user, procedure_id: int) -> int:
    """Auto-deduct consumables when procedure completes — no manual permission required."""
    plans = ProcedureConsumablePlan.query.filter_by(
        procedure_id=procedure_id, is_deducted=False, is_archived=False
    ).all()
    count = 0
    for plan in plans:
        consumable = ConsumableItem.query.get(plan.consumable_id)
        if consumable is None or consumable.current_stock < plan.quantity:
            continue
        consumable.current_stock -= plan.quantity
        movement = ConsumableStockMovement(
            consumable_id=consumable.id,
            movement_type=STOCK_USAGE,
            quantity=plan.quantity,
            procedure_id=procedure_id,
            notes="Auto-deducted on procedure completion",
            recorded_by_id=getattr(acting_user, "id", None),
            department_id=getattr(acting_user, "department_id", 1) or 1,
            created_by_id=getattr(acting_user, "id", None),
        )
        db.session.add(movement)
        plan.is_deducted = True
        count += 1
    if count:
        audit_engine.log(
            "dept_ops.consumable_auto_deduct",
            user=acting_user,
            target_type="procedure",
            target_id=procedure_id,
            details={"deducted_count": count},
        )
        db.session.commit()
    return count
