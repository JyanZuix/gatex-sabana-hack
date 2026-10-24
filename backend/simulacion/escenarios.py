"""Escenarios "¿y si…?" (sección 6.3): cambian supuestos, nunca el historial."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from .montecarlo import EntradaSimulacion


@dataclass(frozen=True)
class Escenario:
    plazo_h: Optional[float] = None

    def __post_init__(self):
        if self.plazo_h is not None and self.plazo_h < 0:
            raise ValueError("plazo_h no puede ser negativo")


def aplicar_escenario(entrada: EntradaSimulacion, escenario: Escenario) -> EntradaSimulacion:
    """Devuelve una entrada nueva con los supuestos cambiados. La original no se modifica."""
    cambios = {k: v for k, v in vars(escenario).items() if v is not None}
    return replace(entrada, **cambios)
