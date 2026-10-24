"""Desempeño D (sección 2): D = 100 · [0.75 · P + 0.25 · (1 − Ret)]."""
from __future__ import annotations

from dataclasses import dataclass

from backend.config import Config

from .historial import Sumas
from .priors import Prior


@dataclass(frozen=True)
class Desempeno:
    valor: float
    puntualidad: float        # P
    magnitud_retraso: float   # Ret


def puntualidad(s: Sumas, prior: Prior, m: float) -> float:
    return (s.W_a + m * prior.P0) / (s.W + m)


def magnitud_retraso(s: Sumas, prior: Prior, m: float) -> float:
    return (s.W_r + m * prior.R0) / (s.W + m)


def calcular_desempeno(s: Sumas, prior: Prior, cfg: Config) -> Desempeno:
    m = cfg.prior.m
    P = puntualidad(s, prior, m)
    Ret = magnitud_retraso(s, prior, m)
    d = cfg.desempeno
    valor = 100 * (d.peso_puntualidad * P + d.peso_magnitud_retraso * (1 - Ret))
    return Desempeno(valor=valor, puntualidad=P, magnitud_retraso=Ret)
