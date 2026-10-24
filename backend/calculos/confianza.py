"""Confianza C (sección 3): C = 100 · Q · F."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from backend.config import Config

from .historial import Sumas
from .priors import Prior

NivelConfianza = Literal["Alta", "Media", "Baja"]


@dataclass(frozen=True)
class Confianza:
    valor: float
    nivel: NivelConfianza
    consistencia: float          # S_desv
    incidentes: float            # S_inc
    cumplimiento_cliente: float  # S_cump
    evidencia: float             # F
    calidad: float               # Q
    sigma_ajustada: float        # σ_aj
    indice_incidentes: float     # I
    n_efectivo: float            # n_ef
    E: float


def nivel_confianza(valor: float, cfg: Config) -> NivelConfianza:
    n = cfg.confianza.niveles
    if valor >= n.alta:
        return "Alta"
    if valor >= n.media:
        return "Media"
    return "Baja"


def calcular_confianza(s: Sumas, prior: Prior, P: float, cfg: Config) -> Confianza:
    """`P` es la puntualidad ajustada del proveedor (sección 2.1)."""
    m = cfg.prior.m
    c = cfg.confianza

    # 3.1 Consistencia de tiempos
    sigma_aj = math.sqrt((s.W * s.sigma_obs ** 2 + m * prior.sigma0 ** 2) / (s.W + m))
    S_desv = 1 - min(sigma_aj / c.sigma_max, 1.0)

    # 3.2 Incidentes
    I = (s.W_inc + m * prior.I0) / (s.W + m)
    S_inc = 1 - I

    # 3.3 Cumplimiento con este cliente, suavizado hacia P
    S_cump = (s.W_ca + m * P) / (s.W_c + m)

    # 3.4 Calidad del historial
    Q = c.peso_consistencia * S_desv + c.peso_incidentes * S_inc + c.peso_cumplimiento_cliente * S_cump

    # 3.5 Factor de evidencia
    n_ef = s.W + c.alfa_cliente * s.W_c
    E = n_ef / (n_ef + c.k_evidencia)
    F = c.piso_evidencia + (1 - c.piso_evidencia) * E

    valor = 100 * Q * F
    return Confianza(
        valor=valor, nivel=nivel_confianza(valor, cfg),
        consistencia=S_desv, incidentes=S_inc, cumplimiento_cliente=S_cump, evidencia=F,
        calidad=Q, sigma_ajustada=sigma_aj, indice_incidentes=I, n_efectivo=n_ef, E=E,
    )
