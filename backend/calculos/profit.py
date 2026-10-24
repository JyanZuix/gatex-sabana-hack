"""Profit para COSCO (README 3.4).

Profit   = Presupuesto_disponible − Costo_proveedor − Costo_esperado_retraso
Margen % = Profit / Presupuesto_disponible
Un profit negativo se informa tal cual: significa que la opción supera el presupuesto.
"""
from __future__ import annotations

from typing import Optional


def calcular_profit(presupuesto_cop: float, costo_proveedor_cop: float, costo_esperado_retraso_cop: float) -> float:
    return presupuesto_cop - costo_proveedor_cop - costo_esperado_retraso_cop


def margen_pct(profit_cop: float, presupuesto_cop: float) -> Optional[float]:
    """Margen en porcentaje, o `None` si el presupuesto es 0 (no hay base para el margen)."""
    if presupuesto_cop <= 0:
        return None
    return 100 * profit_cop / presupuesto_cop
