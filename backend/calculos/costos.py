"""Número de vehículos, reparto de contenedores y costo de una opción (sección 5.3).

Toda carga va en contenedores de 20' (1 TEU cada uno); `peso_kg` es el peso de cada contenedor.

por_vehiculo = min(cap_teu, floor(cap_kg / peso_kg))
vehiculos    = ceil(n_contenedores / por_vehiculo)
costo        = vehiculos · precio_viaje(p, ruta, v)

Si por_vehiculo = 0 (un contenedor excede el peso del vehículo, o el vehículo no lleva
contenedores) ese tipo no es opción. Se elige el tipo más económico que sirve.
Reparto: se llena un vehículo antes de pasar al siguiente (3 contenedores, 2 por vehículo → [2, 1]).
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
    viajes: int                              # vehículos (un viaje por vehículo)
    reparto: tuple[int, ...]                 # contenedores en cada vehículo
    unidades_disponibles: int
    precio_viaje: int
    tiempo_prometido_h: float

    @property
    def costo(self) -> int:
        return self.viajes * self.precio_viaje

    @property
    def suficiente(self) -> bool:
        return self.viajes <= self.unidades_disponibles


def contenedores_por_vehiculo(peso_kg: float, tipo: TipoVehiculo) -> int:
    """Contenedores que caben en un vehículo: los limita el número de puestos (TEU) y el peso."""
    return min(tipo.cap_teu, math.floor(tipo.cap_kg / peso_kg))


def vehiculos_necesarios(n_contenedores: int, peso_kg: float, tipo: TipoVehiculo) -> Optional[int]:
    """Vehículos que exige la carga, o `None` si el tipo no puede llevar ni un contenedor."""
    por_vehiculo = contenedores_por_vehiculo(peso_kg, tipo)
    if por_vehiculo == 0:
        return None
    return math.ceil(n_contenedores / por_vehiculo)


def reparto_contenedores(n_contenedores: int, por_vehiculo: int) -> tuple[int, ...]:
    """Llena cada vehículo antes de pasar al siguiente: (7, 2) → (2, 2, 2, 1)."""
    llenos, resto = divmod(n_contenedores, por_vehiculo)
    return (por_vehiculo,) * llenos + ((resto,) if resto else ())


def tipos_validos(solicitud: Solicitud, tipos: Iterable[TipoVehiculo]) -> list[TipoVehiculo]:
    """Tipos que cumplen el requisito de la carga.

    - Si la solicitud exige un tipo de vehículo, solo ese (es obligatorio).
    - Si no, el tipo debe corresponder a la carga especial (o ser de carga general).
      Si el catálogo no tiene vehículos para esa carga especial (p. ej. peligrosa va en
      tractomula), sirven los de carga general; la aptitud la exige `CARGA_NO_SOPORTADA`.
    - En ambos casos debe poder llevar al menos un contenedor (por_vehiculo ≥ 1).
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
        if vehiculos_necesarios(solicitud.n_contenedores, solicitud.peso_kg, t) is not None:
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
        por_vehiculo = contenedores_por_vehiculo(solicitud.peso_kg, tipo)
        reparto = reparto_contenedores(solicitud.n_contenedores, por_vehiculo)
        opciones.append(OpcionVehiculo(
            tipo_vehiculo_id=tipo.tipo_vehiculo_id, nombre=tipo.nombre, viajes=len(reparto), reparto=reparto,
            unidades_disponibles=unidades.get(tipo.tipo_vehiculo_id, 0),
            precio_viaje=tarifa.precio_viaje, tiempo_prometido_h=tarifa.tiempo_prometido_h,
        ))
    return opciones


def opcion_mas_economica(opciones: Iterable[OpcionVehiculo]) -> Optional[OpcionVehiculo]:
    """La más barata; en empate, la de menor tiempo prometido y luego por id (determinista)."""
    return min(opciones, key=lambda o: (o.costo, o.tiempo_prometido_h, o.tipo_vehiculo_id), default=None)
