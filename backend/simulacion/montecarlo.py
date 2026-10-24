"""Monte Carlo por opción (sección 6.1).

Por iteración j:
  1. Δ_j: con prob. W/(W+m) del historial del proveedor (ponderado por w_i), si no del mercado.
  2. demora_j ~ Uniforme(d_min, d_max) con prob. p_evento del corredor.
  3. T_j = T_prom · (1 + Δ_j) + demora_j
  4. a_j = T_j ≤ plazo
  5. inc_j ~ Bernoulli(min(1, I / s̄)); si ocurre, la severidad sale de su historial.
  6. costo_j = Costo_opción + penal_hora · max(0, T_j − plazo)
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.calculos.historial import Historial
from backend.calculos.profit import margen_pct
from backend.config import Config
from backend.dominio import CondicionVia


@dataclass(frozen=True)
class EntradaSimulacion:
    clave: str                       # identifica la opción (proveedor) dentro de la semilla
    tiempo_prometido_h: float
    plazo_h: float
    costo_cop: int
    presupuesto_cop: float
    penal_hora_cop: float
    deltas_proveedor: np.ndarray
    pesos_proveedor: np.ndarray
    deltas_mercado: np.ndarray
    pesos_mercado: np.ndarray
    sigma0: float                    # respaldo si el mercado no tiene datos
    p_evento: float
    demora_min_h: float
    demora_max_h: float
    indice_incidentes: float         # I (sección 3.2), incluye servicios sin incidente
    severidades_proveedor: np.ndarray

    @property
    def W(self) -> float:
        return float(self.pesos_proveedor.sum())


@dataclass(frozen=True)
class ResultadoSimulacion:
    n: int
    semilla: int
    tiempo_p50_h: float
    tiempo_p90_h: float
    prob_a_tiempo: float
    prob_incidente: float
    severidad_media_incidente: float
    costo_cop: int
    costo_esperado_retraso_cop: float
    costo_esperado_cop: float
    costo_p90_cop: float
    profit_esperado_cop: float
    profit_p10_cop: float
    margen_pct: Optional[float]
    abanico_h: dict[float, float]    # percentil → horas, para el gráfico de abanico
    peso_historial_propio: float     # W/(W+m): cuánto se parece la simulación al proveedor
    avisos: tuple[str, ...] = ()


def preparar_entrada(
    clave: str,
    historial_proveedor: Historial,
    historial_mercado: Historial,
    ruta_id: str,
    indice_incidentes: float,
    sigma0: float,
    tiempo_prometido_h: float,
    plazo_h: float,
    costo_cop: int,
    presupuesto_cop: float,
    penal_hora_cop: float,
    condicion: Optional[CondicionVia],
    cfg: Config,
) -> EntradaSimulacion:
    """Arma la entrada desde los historiales: ruta del proveedor (o todo si W_ruta < mínimo) y mercado en la ruta."""
    propio = historial_proveedor.filtrar_ruta(ruta_id)
    if propio.w.sum() < cfg.simulacion.min_servicios_ruta:
        propio = historial_proveedor
    mercado = historial_mercado.filtrar_ruta(ruta_id)
    return EntradaSimulacion(
        clave=clave, tiempo_prometido_h=tiempo_prometido_h, plazo_h=plazo_h, costo_cop=costo_cop,
        presupuesto_cop=presupuesto_cop, penal_hora_cop=penal_hora_cop,
        deltas_proveedor=propio.delta, pesos_proveedor=propio.w,
        deltas_mercado=mercado.delta, pesos_mercado=mercado.w, sigma0=sigma0,
        p_evento=condicion.p_evento if condicion else 0.0,
        demora_min_h=condicion.demora_min_h if condicion else 0.0,
        demora_max_h=condicion.demora_max_h if condicion else 0.0,
        indice_incidentes=indice_incidentes,
        severidades_proveedor=historial_proveedor.severidades_incidentes,
    )


def generador(semilla: int, clave: str) -> np.random.Generator:
    """Un flujo aleatorio por (solicitud, opción): no depende del orden de los candidatos."""
    return np.random.default_rng(np.random.SeedSequence([semilla, zlib.crc32(clave.encode("utf-8"))]))


def _muestrear(rng: np.random.Generator, valores: np.ndarray, pesos: np.ndarray, n: int) -> np.ndarray:
    return valores[rng.choice(valores.size, size=n, p=pesos / pesos.sum())]


def simular(e: EntradaSimulacion, cfg: Config, semilla: Optional[int] = None) -> ResultadoSimulacion:
    s = cfg.simulacion
    n = s.n
    semilla = s.semilla if semilla is None else semilla
    rng = generador(semilla, e.clave)
    avisos = []

    # 1. Desviación de tiempo: mezcla proveedor / mercado
    W = e.W
    peso_propio = W / (W + cfg.prior.m)
    usa_propio = rng.random(n) < peso_propio
    if W > 0:
        d_propio = _muestrear(rng, e.deltas_proveedor, e.pesos_proveedor, n)
    else:
        d_propio = np.zeros(n)
    if e.pesos_mercado.sum() > 0:
        d_mercado = _muestrear(rng, e.deltas_mercado, e.pesos_mercado, n)
    else:
        # TODO: la especificación no define qué hacer si el mercado no tiene datos en la ruta.
        # Respaldo provisional: Δ ~ Normal(0, σ0). Confirmar con el equipo.
        d_mercado = rng.normal(0.0, e.sigma0, n)
        avisos.append("Sin historial del mercado en la ruta: se usó Δ ~ Normal(0, σ0)")
    delta = np.where(usa_propio, d_propio, d_mercado)

    # 2. Condiciones actuales de la vía
    hay_evento = rng.random(n) < e.p_evento
    demora = np.where(hay_evento, rng.uniform(e.demora_min_h, e.demora_max_h, n), 0.0)

    # 3-4. Tiempo y llegada a tiempo
    T = e.tiempo_prometido_h * (1 + delta) + demora
    a_tiempo = T <= e.plazo_h

    # 5. Incidentes
    sev = e.severidades_proveedor
    s_media = float(sev.mean()) if sev.size else s.severidad_media_sin_historial
    p_inc = min(1.0, e.indice_incidentes / s_media)
    inc = rng.random(n) < p_inc
    sev_j = rng.choice(sev, size=n) if sev.size else np.full(n, s_media)
    sev_media_inc = float(sev_j[inc].mean()) if inc.any() else 0.0

    # 6. Costo y profit
    retraso_h = np.maximum(0.0, T - e.plazo_h)
    penalidad = e.penal_hora_cop * retraso_h
    costo_j = e.costo_cop + penalidad
    profit_j = e.presupuesto_cop - costo_j
    profit_esperado = float(profit_j.mean())

    return ResultadoSimulacion(
        n=n, semilla=semilla,
        tiempo_p50_h=float(np.percentile(T, s.percentil_tipico)),
        tiempo_p90_h=float(np.percentile(T, s.percentil_mal_caso)),
        prob_a_tiempo=float(a_tiempo.mean()),
        prob_incidente=float(inc.mean()),
        severidad_media_incidente=sev_media_inc,
        costo_cop=e.costo_cop,
        costo_esperado_retraso_cop=float(penalidad.mean()),
        costo_esperado_cop=float(costo_j.mean()),
        costo_p90_cop=float(np.percentile(costo_j, s.percentil_mal_caso)),
        profit_esperado_cop=profit_esperado,
        profit_p10_cop=float(np.percentile(profit_j, s.percentil_profit_mal_caso)),
        margen_pct=margen_pct(profit_esperado, e.presupuesto_cop),
        abanico_h={p: float(np.percentile(T, p)) for p in s.percentiles_abanico},
        peso_historial_propio=peso_propio,
        avisos=tuple(avisos),
    )
