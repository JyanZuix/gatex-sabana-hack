"""Escenarios "¿y si…?" (sección 6.3): cambian supuestos, nunca el historial."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from .montecarlo import EntradaSimulacion


@dataclass(frozen=True)
class Escenario:
    plazo_h: Optional[float] = None
    penal_hora_cop: Optional[float] = None

    def __post_init__(self):
        for nombre in ("plazo_h", "penal_hora_cop"):
            valor = getattr(self, nombre)
            if valor is not None and valor < 0:
                raise ValueError(f"{nombre} no puede ser negativo")


def aplicar_escenario(entrada: EntradaSimulacion, escenario: Escenario) -> EntradaSimulacion:
    """Devuelve una entrada nueva con los supuestos cambiados. La original no se modifica."""
    cambios = {k: v for k, v in vars(escenario).items() if v is not None}
    return replace(entrada, **cambios)
