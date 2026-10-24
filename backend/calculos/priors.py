"""Valores de referencia del mercado (sección 1.3).

Se busca el segmento más específico con datos suficientes:
ruta → corredor → nacional → valores por defecto de la configuración.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from backend.config import Config

from .historial import Historial

Nivel = Literal["ruta", "corredor", "nacional", "por_defecto"]


@dataclass(frozen=True)
class Prior:
    P0: float
    R0: float
    sigma0: float
    nivel: Nivel
    n_servicios: int


def prior_por_defecto(cfg: Config) -> Prior:
    d = cfg.prior.por_defecto
    return Prior(P0=d.P0, R0=d.R0, sigma0=d.sigma0, nivel="por_defecto", n_servicios=0)


def prior_de_historial(h: Historial, nivel: Nivel) -> Prior:
    s = h.sumas()
    return Prior(P0=s.W_a / s.W, R0=s.W_r / s.W, sigma0=s.sigma_obs, nivel=nivel, n_servicios=h.n)


def calcular_prior(mercado: Historial, ruta_id: str, rutas_corredor: set[str], cfg: Config) -> Prior:
    """`mercado` es el historial de todos los proveedores; `rutas_corredor` las rutas del mismo corredor."""
    minimo = cfg.prior.min_servicios_segmento
    segmentos: list[tuple[Nivel, np.ndarray]] = [
        ("ruta", mercado.ruta_id == ruta_id),
        ("corredor", np.isin(mercado.ruta_id, list(rutas_corredor))),
        ("nacional", np.ones(mercado.n, dtype=bool)),
    ]
    for nivel, mascara in segmentos:
        if int(mascara.sum()) >= minimo:
            sub = Historial(*(x[mascara] for x in (mercado.w, mercado.delta, mercado.r, mercado.a,
                                                    mercado.c, mercado.ruta_id)))
            if sub.w.sum() > 0:
                return prior_de_historial(sub, nivel)
    return prior_por_defecto(cfg)
