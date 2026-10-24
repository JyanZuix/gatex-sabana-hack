"""Profit para COSCO (README 3.4).

Profit   = Presupuesto_disponible − Costo_proveedor
Margen % = Profit / Presupuesto_disponible
El costo por retraso se eliminó (docs/decisiones.md, 2026-10-24).
"""
from __future__ import annotations

from typing import Optional


def calcular_profit(presupuesto_cop: float, costo_proveedor_cop: float) -> float:
    return presupuesto_cop - costo_proveedor_cop


def margen_pct(profit_cop: float, presupuesto_cop: float) -> Optional[float]:
    """Margen en porcentaje, o `None` si el presupuesto es 0 (no hay base para el margen)."""
    if presupuesto_cop <= 0:
        return None
    return 100 * profit_cop / presupuesto_cop
