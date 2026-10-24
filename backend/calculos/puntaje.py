"""Puntaje ponderado S y orden de los candidatos (docs/calculos_simulacion.md, sección 6.4).

S = 100 · (w_p·M + w_t·P_a + w_d·D/100 + w_c·C/100)
M = profit / mejor profit entre los candidatos: el que más deja aporta todo su peso y los demás
en proporción. Es relativo a propósito: con un margen fijo de referencia, un presupuesto holgado
hacía que todos llegaran al tope y el precio dejara de contar. SIN_MARGEN ya descartó a quien
da pérdida, así que M está entre 0 y 1. Los pesos están en `parametros.yaml` (sección `puntaje`).
Desempate determinista: mayor probabilidad a tiempo, menor costo, luego `proveedor_id`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from backend.config import Config


@dataclass(frozen=True)
class EntradaPuntaje:
    proveedor_id: str
    costo_cop: int
    profit_cop: float             # presupuesto − costo (≥ 0 tras el filtro)
    prob_a_tiempo: float
    desempeno: float              # 0-100
    confianza: float              # 0-100


@dataclass(frozen=True)
class Puntaje:
    valor: float                  # 0-100
    profit: float                 # puntos que aporta cada factor; suman `valor`
    a_tiempo: float
    desempeno: float
    confianza: float


def calcular_puntaje(x: EntradaPuntaje, mejor_profit_cop: float, cfg: Config) -> Puntaje:
    p = cfg.puntaje
    M = min(max(x.profit_cop, 0.0) / mejor_profit_cop, 1.0) if mejor_profit_cop > 0 else 0.0
    aportes = (100 * p.peso_profit * M, 100 * p.peso_a_tiempo * x.prob_a_tiempo,
               p.peso_desempeno * x.desempeno, p.peso_confianza * x.confianza)
    return Puntaje(sum(aportes), *aportes)


def ordenar(entradas: Sequence[EntradaPuntaje], cfg: Config) -> list[tuple[EntradaPuntaje, Puntaje]]:
    """De mayor a menor puntaje, con desempate determinista."""
    mejor = max((x.profit_cop for x in entradas), default=0.0)
    con_puntaje = [(x, calcular_puntaje(x, mejor, cfg)) for x in entradas]
    return sorted(con_puntaje, key=lambda t: (-t[1].valor, -t[0].prob_a_tiempo, t[0].costo_cop, t[0].proveedor_id))
