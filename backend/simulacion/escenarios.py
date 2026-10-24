"""Escenarios "¿y si…?" (sección 6.3): cambian supuestos, nunca el historial."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from .montecarlo import EntradaSimulacion


@dataclass(frozen=True)
class Escenario:
    p_evento: Optional[float] = None
    demora_min_h: Optional[float] = None
    demora_max_h: Optional[float] = None
    plazo_h: Optional[float] = None
    penal_hora_cop: Optional[float] = None

    def __post_init__(self):
        if self.p_evento is not None and not 0 <= self.p_evento <= 1:
            raise ValueError("p_evento debe estar entre 0 y 1")
        for nombre in ("demora_min_h", "demora_max_h", "plazo_h", "penal_hora_cop"):
            valor = getattr(self, nombre)
            if valor is not None and valor < 0:
                raise ValueError(f"{nombre} no puede ser negativo")


def aplicar_escenario(entrada: EntradaSimulacion, escenario: Escenario) -> EntradaSimulacion:
    """Devuelve una entrada nueva con los supuestos cambiados. La original no se modifica."""
    cambios = {k: v for k, v in vars(escenario).items() if v is not None}
    nueva = replace(entrada, **cambios)
    if nueva.demora_min_h > nueva.demora_max_h:
        raise ValueError("demora_min_h no puede ser mayor que demora_max_h")
    return nueva
