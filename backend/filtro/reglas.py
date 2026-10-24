"""Reglas de descarte.

Cada regla recibe el contexto de un proveedor y devuelve sus razones (lista
vacía si cumple). Para agregar una regla basta decorarla con `@regla`; la
simulación no se toca.
"""
from __future__ import annotations

from typing import Callable

from .modelos import ContextoProveedor, Razon

Regla = Callable[[ContextoProveedor], list[Razon]]
REGLAS: list[Regla] = []

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def regla(funcion: Regla) -> Regla:
    REGLAS.append(funcion)
    return funcion


def _fecha(f) -> str:
    return f"{f.day:02d}-{MESES[f.month - 1]}"


def _horas(h: float) -> str:
    return f"{h:g} h"


def _cop(x: float) -> str:
    return "$" + f"{x:,.0f}".replace(",", ".")


@regla
def sin_cobertura(ctx: ContextoProveedor) -> list[Razon]:
    if ctx.tiene_cobertura:
        return []
    origen, destino = ctx.nombres_origen_destino
    return [Razon("SIN_COBERTURA", f"No opera el trayecto {origen} → {destino}",
                  requerido=ctx.ruta.ruta_id, disponible=None)]


@regla
def sin_tarifa(ctx: ContextoProveedor) -> list[Razon]:
    if not ctx.opciones:
        return [Razon("SIN_TARIFA", "Sin tarifa vigente para esta ruta y un vehículo válido",
                      requerido=ctx.ruta.ruta_id, disponible=None)]
    con_unidades = [t.tipo_vehiculo_id for t in ctx.tipos_validos if ctx.unidades.get(t.tipo_vehiculo_id, 0) > 0]
    if con_unidades and not ctx.operables:
        return [Razon("SIN_TARIFA", "Sin tarifa vigente para los vehículos que tiene disponibles en esta ruta",
                      requerido=", ".join(con_unidades), disponible=None)]
    return []


@regla
def vehiculo_no_disponible(ctx: ContextoProveedor) -> list[Razon]:
    if any(ctx.unidades.get(t.tipo_vehiculo_id, 0) > 0 for t in ctx.tipos_validos):
        return []
    requeridos = ", ".join(t.nombre for t in ctx.tipos_validos) or "un vehículo compatible con la carga"
    tiene = ", ".join(sorted(k for k, v in ctx.unidades.items() if v > 0)) or None
    detalle = f" (requerida para {ctx.solicitud.tipo_carga})" if ctx.solicitud.tipo_carga else ""
    return [Razon("VEHICULO_NO_DISPONIBLE", f"No tiene {requeridos} disponible{detalle}",
                  requerido=requeridos, disponible=tiene)]


@regla
def vehiculos_insuficientes(ctx: ContextoProveedor) -> list[Razon]:
    if not ctx.operables or ctx.suficientes:
        return []
    # TODO: viajes en varias tandas (`vehiculos.permitir_tandas`). La v1 siempre descarta.
    o = min(ctx.operables, key=lambda o: (o.viajes - o.unidades_disponibles, o.costo))
    return [Razon("VEHICULOS_INSUFICIENTES",
                  f"Necesita {o.viajes} × {o.nombre}, solo tiene {o.unidades_disponibles} disponible(s)",
                  requerido=o.viajes, disponible=o.unidades_disponibles)]


@regla
def sin_capacidad(ctx: ContextoProveedor) -> list[Razon]:
    requeridos = ctx.cfg.filtro.servicios_requeridos
    if ctx.capacidad is None or ctx.capacidad.servicios_disponibles >= requeridos:
        return []
    return [Razon("SIN_CAPACIDAD", f"Capacidad agotada para el {_fecha(ctx.solicitud.fecha_servicio)}",
                  requerido=requeridos, disponible=ctx.capacidad.servicios_disponibles)]


@regla
def plazo_incumplible(ctx: ContextoProveedor) -> list[Razon]:
    # Se evalúa sobre las opciones más viables que haya: suficientes, luego operables, luego con tarifa.
    evaluadas = ctx.suficientes or ctx.operables or ctx.opciones
    if not evaluadas:
        return []
    mejor = min(o.tiempo_prometido_h for o in evaluadas)
    plazo = ctx.solicitud.plazo_h
    if mejor <= plazo:
        return []
    return [Razon("PLAZO_INCUMPLIBLE", f"Tránsito pactado {_horas(mejor)}; plazo disponible {_horas(plazo)}",
                  requerido=plazo, disponible=mejor)]


@regla
def sin_margen(ctx: ContextoProveedor) -> list[Razon]:
    """Descarta a quien da pérdida: su opción más barata cuesta más que el presupuesto.

    Se evalúa sobre las mismas opciones con las que se elige el vehículo del candidato
    (suficientes y dentro del plazo); si no hay, sobre las más viables que tenga.
    """
    plazo = ctx.solicitud.plazo_h
    en_plazo = [o for o in ctx.suficientes if o.tiempo_prometido_h <= plazo]
    evaluadas = en_plazo or ctx.suficientes or ctx.operables or ctx.opciones
    if not evaluadas:
        return []
    costo = min(o.costo for o in evaluadas)
    presupuesto = ctx.solicitud.presupuesto_cop
    if costo <= presupuesto:
        return []
    return [Razon("SIN_MARGEN", f"Costo {_cop(costo)} supera el presupuesto de {_cop(presupuesto)}",
                  requerido=presupuesto, disponible=costo)]


@regla
def carga_no_soportada(ctx: ContextoProveedor) -> list[Razon]:
    carga = ctx.solicitud.tipo_carga
    if carga is None or carga in ctx.proveedor.cargas_especiales:
        return []
    return [Razon("CARGA_NO_SOPORTADA", f"No transporta carga {carga}",
                  requerido=carga, disponible=", ".join(ctx.proveedor.cargas_especiales) or None)]


@regla
def proveedor_inactivo(ctx: ContextoProveedor) -> list[Razon]:
    p = ctx.proveedor
    razones = []
    if p.estado != "activo":
        razones.append(Razon("PROVEEDOR_INACTIVO", f"Proveedor {p.estado}", requerido="activo", disponible=p.estado))
    if p.poliza_vigente_hasta is not None and p.poliza_vigente_hasta < ctx.solicitud.fecha_servicio:
        razones.append(Razon("PROVEEDOR_INACTIVO", f"Póliza vencida desde el {_fecha(p.poliza_vigente_hasta)}",
                             requerido=ctx.solicitud.fecha_servicio.isoformat(),
                             disponible=p.poliza_vigente_hasta.isoformat()))
    return razones


FLEXIBILIZAR = {
    "SIN_COBERTURA": lambda r: "El proveedor tendría que operar esta ruta",
    "SIN_TARIFA": lambda r: "Habría que pactar una tarifa para esta ruta",
    "VEHICULO_NO_DISPONIBLE": lambda r: "Aceptar otro tipo de vehículo",
    "VEHICULOS_INSUFICIENTES": lambda r: f"Aceptar viajes en varias tandas o dividir la carga (tiene {r.disponible} de {r.requerido})",
    "SIN_CAPACIDAD": lambda r: "Cambiar la fecha del servicio",
    "PLAZO_INCUMPLIBLE": lambda r: f"Ampliar el plazo a {_horas(r.disponible)}",
    "SIN_MARGEN": lambda r: f"Aumentar el presupuesto a {_cop(r.disponible)}",
    "CARGA_NO_SOPORTADA": lambda r: "El proveedor no maneja este tipo de carga",
    "PROVEEDOR_INACTIVO": lambda r: "Habría que regularizar al proveedor",
}


def que_flexibilizar(razon: Razon) -> str:
    texto = FLEXIBILIZAR.get(razon.codigo)
    return texto(razon) if texto else f"Revisar la condición {razon.codigo}"
