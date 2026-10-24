"""Número de vehículos y costo de una opción (sección 5.3).

viajes_v = max(ceil(n_teu / cap_teu_v), ceil(toneladas / cap_toneladas_v))
costo_v  = viajes_v · precio_viaje(p, ruta, v)
Se elige el tipo de vehículo más económico que sirve.
TODO: combinaciones mixtas de vehículos (fuera del alcance de la v1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional

from backend.dominio import Solicitud, Tarifa, TipoVehiculo


@dataclass(frozen=True)
class OpcionVehiculo:
    tipo_vehiculo_id: str
    nombre: str
    viajes: int
    unidades_disponibles: int
    precio_viaje: int
    tiempo_prometido_h: float

    @property
    def costo(self) -> int:
        return self.viajes * self.precio_viaje

    @property
    def suficiente(self) -> bool:
        return self.viajes <= self.unidades_disponibles


def viajes_necesarios(n_teu: int, toneladas: float, tipo: TipoVehiculo) -> Optional[int]:
    """Viajes (vehículos) que exige la carga, o `None` si el tipo no puede llevarla."""
    if n_teu > 0 and tipo.cap_teu <= 0:
        return None
    if toneladas > 0 and tipo.cap_toneladas <= 0:
        return None
    por_teu = math.ceil(n_teu / tipo.cap_teu) if n_teu > 0 else 0
    por_peso = math.ceil(toneladas / tipo.cap_toneladas) if toneladas > 0 else 0
    return max(por_teu, por_peso, 1)


def tipos_validos(solicitud: Solicitud, tipos: Iterable[TipoVehiculo]) -> list[TipoVehiculo]:
    """Tipos que cumplen el requisito de la carga.

    - Si la solicitud exige un tipo de vehículo, solo ese.
    - Si no, el tipo debe corresponder a la carga especial (o ser de carga general).
      Si el catálogo no tiene vehículos para esa carga especial (p. ej. peligrosa va en
      tractomula), sirven los de carga general; la aptitud la exige `CARGA_NO_SOPORTADA`.
    - En ambos casos debe poder llevar la carga (capacidad en TEU y en toneladas).
    """
    tipos = list(tipos)
    carga = solicitud.tipo_carga
    if carga is not None and not any(t.carga_especial == carga for t in tipos):
        carga = None
    validos = []
    for t in tipos:
        if solicitud.tipo_vehiculo_id is not None:
            if t.tipo_vehiculo_id != solicitud.tipo_vehiculo_id:
                continue
        elif t.carga_especial != carga:
            continue
        if viajes_necesarios(solicitud.n_teu, solicitud.toneladas, t) is not None:
            validos.append(t)
    return validos


def opciones_vehiculo(
    solicitud: Solicitud,
    validos: Iterable[TipoVehiculo],
    tarifas_proveedor: Iterable[Tarifa],
    unidades: dict[str, int],
) -> list[OpcionVehiculo]:
    """Una opción por cada tipo válido para el que el proveedor tiene tarifa vigente."""
    por_tipo = {t.tipo_vehiculo_id: t for t in tarifas_proveedor}
    opciones = []
    for tipo in validos:
        tarifa = por_tipo.get(tipo.tipo_vehiculo_id)
        if tarifa is None:
            continue
        opciones.append(OpcionVehiculo(
            tipo_vehiculo_id=tipo.tipo_vehiculo_id, nombre=tipo.nombre,
            viajes=viajes_necesarios(solicitud.n_teu, solicitud.toneladas, tipo),
            unidades_disponibles=unidades.get(tipo.tipo_vehiculo_id, 0),
            precio_viaje=tarifa.precio_viaje, tiempo_prometido_h=tarifa.tiempo_prometido_h,
        ))
    return opciones


def opcion_mas_economica(opciones: Iterable[OpcionVehiculo]) -> Optional[OpcionVehiculo]:
    """La más barata; en empate, la de menor tiempo prometido y luego por id (determinista)."""
    return min(opciones, key=lambda o: (o.costo, o.tiempo_prometido_h, o.tipo_vehiculo_id), default=None)
