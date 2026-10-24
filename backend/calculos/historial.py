"""Historial ponderado de un proveedor y sus sumas (secciones 1 y 1.2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Iterable, Optional

import numpy as np

from backend.dominio import ServicioHistorico

from .recencia import peso_recencia


@dataclass(frozen=True)
class Sumas:
    """Sumas ponderadas que reutilizan Desempeño y Confianza."""
    W: float
    W_a: float
    W_r: float
    W_c: float
    W_ca: float
    sigma_obs: float  # desviación estándar ponderada de Δ


def _solo_lectura(a) -> np.ndarray:
    a = np.asarray(a)
    a.setflags(write=False)
    return a


@dataclass(frozen=True)
class Historial:
    """Servicios ya transformados: Δ_i, r_i, a_i, c_i y w_i (arreglos de solo lectura)."""
    w: np.ndarray
    delta: np.ndarray
    r: np.ndarray
    a: np.ndarray
    c: np.ndarray
    ruta_id: np.ndarray
    omitidos: tuple[str, ...] = field(default=())  # servicios sin datos suficientes, con el motivo

    @property
    def n(self) -> int:
        return int(self.w.size)

    def filtrar_ruta(self, ruta_id: str) -> "Historial":
        m = self.ruta_id == ruta_id
        return Historial(*(_solo_lectura(x[m]) for x in (self.w, self.delta, self.r, self.a, self.c, self.ruta_id)))

    def sumas(self) -> Sumas:
        W = float(self.w.sum())
        if W > 0:
            media = float((self.w * self.delta).sum() / W)
            var = float((self.w * (self.delta - media) ** 2).sum() / W)
        else:
            var = 0.0
        return Sumas(
            W=W,
            W_a=float((self.w * self.a).sum()),
            W_r=float((self.w * self.r).sum()),
            W_c=float((self.w * self.c).sum()),
            W_ca=float((self.w * self.c * self.a).sum()),
            sigma_obs=float(np.sqrt(var)),
        )


def construir_historial(
    servicios: Iterable[ServicioHistorico],
    fecha_calculo: date,
    vida_media_dias: float,
    cliente_id: Optional[str] = None,
    tiempo_prometido_respaldo: Optional[Callable[[ServicioHistorico], Optional[float]]] = None,
) -> Historial:
    """Transforma servicios en el historial ponderado.

    - Si falta `tiempo_prometido_h`, se usa `tiempo_prometido_respaldo` (el de la tarifa).
    - Si falta `a_tiempo`, se calcula como `tiempo_real_h ≤ plazo_acordado_h`.
    - Un servicio sin datos para Δ o a_i no se inventa: se omite y se informa en `omitidos`.
    """
    filas, omitidos = [], []
    for sv in servicios:
        prometido = sv.tiempo_prometido_h
        if prometido is None and tiempo_prometido_respaldo is not None:
            prometido = tiempo_prometido_respaldo(sv)
        if prometido is None:
            omitidos.append(f"{sv.servicio_id}: sin tiempo prometido")
            continue
        a = sv.a_tiempo
        if a is None:
            if sv.plazo_acordado_h is None:
                omitidos.append(f"{sv.servicio_id}: sin a_tiempo ni plazo acordado")
                continue
            a = sv.tiempo_real_h <= sv.plazo_acordado_h
        delta = (sv.tiempo_real_h - prometido) / prometido
        filas.append((
            (fecha_calculo - sv.fecha_entrega).days,
            delta,
            min(max(delta, 0.0), 1.0),
            1.0 if a else 0.0,
            1.0 if cliente_id is not None and sv.cliente_id == cliente_id else 0.0,
            sv.ruta_id,
        ))
    if filas:
        t, delta, r, a, c, ruta = (np.array(col) for col in zip(*filas))
        w = peso_recencia(t, vida_media_dias)
        w = np.atleast_1d(w)
    else:
        w = delta = r = a = c = np.zeros(0)
        ruta = np.array([], dtype=str)
    return Historial(
        w=_solo_lectura(w.astype(float)), delta=_solo_lectura(delta.astype(float)),
        r=_solo_lectura(r.astype(float)), a=_solo_lectura(a.astype(float)),
        c=_solo_lectura(c.astype(float)),
        ruta_id=_solo_lectura(ruta.astype(str)), omitidos=tuple(omitidos),
    )
