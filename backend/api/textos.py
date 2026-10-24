"""Textos en lenguaje llano para las tarjetas, la ficha y el informe.

Se generan en el backend (regla "nada de cálculos en el cliente"): la web, las gafas y el
informe muestran exactamente las mismas frases. Cada frase sale de un dato de la evaluación.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Literal, Optional

from backend.calculos.confianza import Confianza
from backend.calculos.costos import OpcionVehiculo
from backend.calculos.desempeno import Desempeno
from backend.calculos.historial import construir_historial
from backend.config import Config
from backend.dominio import Capacidad, ServicioHistorico
from backend.simulacion.explicacion import describir_consistencia

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
NOMBRE_CARGA = {"general": "general", "refrigerado": "refrigerada", "sobredimensionado": "sobredimensionada",
                "peligrosa": "peligrosa"}


def _pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def _horas(h: float) -> str:
    texto = f"{h:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{texto} h"


def _fecha(f: date) -> str:
    return f"{f.day:02d}-{MESES[f.month - 1]}"


def _servicios(n: int) -> str:
    return "1 servicio" if n == 1 else f"{n} servicios"


# --- Tarjeta del candidato --------------------------------------------------

def resumen_tiempo(p50: float, p90: float, plazo_h: float, prob_a_tiempo: float) -> str:
    return (f"Normalmente llega en {_horas(p50)}; en un día malo, hasta {_horas(p90)}. "
            f"Plazo: {_horas(plazo_h)} → llega a tiempo en el {_pct(prob_a_tiempo)} de los casos simulados.")


def texto_capacidad(opcion: OpcionVehiculo, capacidad: Optional[Capacidad], fecha: date) -> str:
    vehiculos = "1 vehículo" if opcion.viajes == 1 else f"{opcion.viajes} vehículos"
    texto = (f"Necesita {vehiculos} ({opcion.nombre}) y tiene {opcion.unidades_disponibles} "
             f"libre{'s' if opcion.unidades_disponibles != 1 else ''} esta semana")
    if capacidad is None:
        return texto + f" · sin dato de cuántos servicios acepta el {_fecha(fecha)} (no se descartó por eso)"
    n = capacidad.servicios_disponibles
    return texto + f" · acepta {_servicios(n)} más el {_fecha(fecha)}"


def texto_desempeno(d: Desempeno) -> str:
    return (f"{d.valor:.0f}/100: entrega a tiempo el {_pct(d.puntualidad)} de sus servicios y su retraso medio "
            f"es del {_pct(d.magnitud_retraso)} sobre el tiempo pactado (lo reciente pesa más; con pocos datos "
            f"se acerca al promedio del mercado).")


def _consistencia(valor: float, cfg: Config) -> str:
    return "sus " + describir_consistencia(valor, cfg).replace("tiempos ", "tiempos son ", 1)


def texto_confianza(c: Confianza, n_servicios: int, n_cliente: Optional[int], cfg: Config) -> str:
    """`n_cliente` es None cuando no hay un cliente de referencia (ficha del proveedor)."""
    base = f"{c.nivel} ({c.valor:.0f}/100): se basa en {_servicios(n_servicios)}"
    if n_cliente is None:
        return f"{base}; {_consistencia(c.consistencia, cfg)}."
    if n_cliente == 0:
        return f"{base}; {_consistencia(c.consistencia, cfg)}; nunca ha trabajado con este cliente."
    return (f"{base} ({n_cliente} con este cliente); {_consistencia(c.consistencia, cfg)}; "
            f"con este cliente cumple cerca del {_pct(c.cumplimiento_cliente)}.")


# --- Fortalezas y debilidades ----------------------------------------------

@dataclass(frozen=True)
class Segmento:
    """Puntualidad del proveedor en una ruta, un vehículo o un tipo de carga frente a su promedio."""
    clase: Literal["ruta", "vehiculo", "carga"]
    clave: str
    texto: str
    diferencia: float          # puntualidad del segmento − su promedio


def fortalezas_y_debilidades(propios: list[ServicioHistorico], hoy: date, cfg: Config,
                             rutas: dict[str, str], tipos: dict[str, str]) -> tuple[list[Segmento], list[Segmento]]:
    """Segmentos con ≥ `ficha.min_servicios_segmento` servicios que se apartan ≥ `ficha.umbral_diferencia`.

    `rutas` y `tipos` traducen identificadores a nombres. Cada frase cita el porcentaje del segmento,
    el promedio del proveedor y cuántos servicios lo respaldan.
    """
    h = construir_historial(propios, hoy, cfg.recencia.vida_media_dias)
    if not h.n:
        return [], []
    punt = float(h.a.mean())
    grupos: list[tuple[str, str, str, Iterable[ServicioHistorico]]] = []
    grupos += [("ruta", r, f"la ruta {rutas.get(r, r)}", [x for x in propios if x.ruta_id == r])
               for r in sorted({x.ruta_id for x in propios})]
    grupos += [("vehiculo", t, f"vehículo {tipos.get(t, t)}", [x for x in propios if x.tipo_vehiculo_id == t])
               for t in sorted({x.tipo_vehiculo_id for x in propios})]
    grupos += [("carga", k, f"carga {NOMBRE_CARGA[k]}", [x for x in propios if x.tipo_carga == k])
               for k in sorted({x.tipo_carga for x in propios if x.tipo_carga is not None})]
    u = cfg.ficha.umbral_diferencia
    fortalezas, debilidades = [], []
    for clase, clave, nombre, servicios in grupos:
        hs = construir_historial(list(servicios), hoy, cfg.recencia.vida_media_dias)
        if hs.n < cfg.ficha.min_servicios_segmento:
            continue
        p_seg = float(hs.a.mean())
        texto = f"Puntualidad de {_pct(p_seg)} en {nombre} (su promedio: {_pct(punt)}; {hs.n} servicios)"
        if p_seg >= punt + u:
            fortalezas.append(Segmento(clase, clave, texto, p_seg - punt))
        elif p_seg <= punt - u:
            debilidades.append(Segmento(clase, clave, texto, p_seg - punt))
    return fortalezas, debilidades


def para_tarjeta(segmentos: list[Segmento], relevantes: set[tuple[str, str]], n: int) -> list[str]:
    """Los `n` más útiles para esta solicitud: primero los de su ruta, vehículo o carga; luego los más marcados."""
    orden = sorted(segmentos, key=lambda s: ((s.clase, s.clave) not in relevantes, -abs(s.diferencia), s.texto))
    return [s.texto for s in orden[:n]]
