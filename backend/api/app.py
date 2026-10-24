"""API HTTP de la Sala de Simulación de Proveedores (FastAPI).

Arranque local:  uvicorn backend.api.app:app --reload
Documentación:   http://localhost:8000/docs
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.calculos.costos import contenedores_por_vehiculo
from backend.config import Config, cargar_config
from backend.datos import (CierreInvalido, CierreViaje, ErrorDatosNoDisponibles, Repositorio, SolicitudNoEncontrada,
                           SolicitudYaDecidida, ViajeYaCerrado, crear_almacen, crear_repositorio)
from backend.datos.almacen import numero_solicitud, solicitud_decidida
from backend.dominio import CARGAS_ESPECIALES, Solicitud
from backend.filtro import RutaNoEncontrada

from . import esquemas as e
from .catalogos import construir_catalogos
from .cors import envolver_cors
from .informe import construir_informe, nombre_archivo
from .registro import Registro
from .servicio import ServicioEvaluacion

MENSAJES = {
    "missing": lambda c: "Falta este campo",
    "extra_forbidden": lambda c: "Campo no permitido",
    "greater_than": lambda c: f"Debe ser mayor que {c['gt']:g}",
    "greater_than_equal": lambda c: f"Debe ser mayor o igual que {c['ge']:g}",
    "less_than_equal": lambda c: f"Debe ser menor o igual que {c['le']:g}",
    "string_too_short": lambda c: "No puede estar vacío",
    "literal_error": lambda c: f"Valor no válido; use {c['expected']}",
    "int_parsing": lambda c: "Debe ser un número entero",
    "int_from_float": lambda c: "Debe ser un número entero",
    "float_parsing": lambda c: "Debe ser un número",
    "date_from_datetime_parsing": lambda c: "Fecha no válida (use AAAA-MM-DD)",
    "date_parsing": lambda c: "Fecha no válida (use AAAA-MM-DD)",
    "string_type": lambda c: "Debe ser un texto",
    "json_invalid": lambda c: "El cuerpo no es un JSON válido",
}

NOMBRES_CARGA = {"refrigerado": "Refrigerada", "sobredimensionado": "Sobredimensionada", "peligrosa": "Peligrosa"}

GENERICOS = {"Not Found": "Recurso no encontrado", "Method Not Allowed": "Método no permitido"}


def _errores_en_espanol(errores) -> list[dict]:
    salida = []
    for err in errores:
        loc = [str(x) for x in err.get("loc", ()) if x != "body"]
        traducir = MENSAJES.get(err.get("type"))
        mensaje = traducir(err.get("ctx") or {}) if traducir else str(err.get("msg", "")).removeprefix("Value error, ")
        salida.append({"campo": ".".join(loc) or None, "mensaje": mensaje})
    return salida


def _error_422(mensaje: str, campo: Optional[str] = None) -> HTTPException:
    return HTTPException(status_code=422, detail={"detalle": mensaje, "errores": [{"campo": campo, "mensaje": mensaje}]})


def crear_app(repo: Optional[Repositorio] = None, cfg: Optional[Config] = None,
              registro: Optional[Registro] = None, hoy: Callable[[], date] = date.today) -> FastAPI:
    repo = repo or crear_repositorio()
    cfg = cfg or cargar_config()
    registro = registro or Registro(crear_almacen())
    servicio = ServicioEvaluacion(repo, cfg)

    app = FastAPI(
        title="Sala de Simulación de Proveedores · COSCO SHIPPING",
        description="Filtra proveedores de transporte terrestre con todas sus razones de descarte, simula a los "
                    "candidatos y registra la decisión del funcionario. La API no elige: el funcionario decide.",
        version="1.0.0",
    )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        errores = _errores_en_espanol(exc.errors())
        return JSONResponse(status_code=422, content={"detalle": "Datos de entrada no válidos", "errores": errores})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        detalle = GENERICOS.get(exc.detail, exc.detail) if isinstance(exc.detail, str) else exc.detail
        contenido = detalle if isinstance(detalle, dict) else {"detalle": detalle}
        return JSONResponse(status_code=exc.status_code, content=contenido)

    @app.exception_handler(SolicitudYaDecidida)
    async def _ya_decidida(_: Request, exc: SolicitudYaDecidida):
        return JSONResponse(status_code=409, content={"detalle": str(exc)})

    @app.exception_handler(ViajeYaCerrado)
    async def _ya_cerrado(_: Request, exc: ViajeYaCerrado):
        return JSONResponse(status_code=409, content={"detalle": str(exc)})

    @app.exception_handler(SolicitudNoEncontrada)
    async def _no_encontrada(_: Request, exc: SolicitudNoEncontrada):
        return JSONResponse(status_code=404, content={"detalle": str(exc)})

    @app.exception_handler(CierreInvalido)
    async def _cierre_invalido(_: Request, exc: CierreInvalido):
        return JSONResponse(status_code=422, content={"detalle": str(exc), "errores": [{"campo": None, "mensaje": str(exc)}]})

    @app.exception_handler(ErrorDatosNoDisponibles)
    async def _sin_datos(_: Request, exc: ErrorDatosNoDisponibles):
        return JSONResponse(status_code=503, content={"detalle": str(exc)})

    # ------------------------------------------------------------------
    @app.get("/salud", tags=["Sistema"], summary="Estado del servicio")
    def salud():
        return {"estado": "ok", "repositorio": type(repo).__name__.removeprefix("Repositorio").lower()}

    @app.get("/catalogos", response_model=e.Catalogos, tags=["Catálogos"],
             summary="Clientes, ubicaciones, rutas, tipos de vehículo y de carga con los IDs que acepta la API. "
                     "Solo se listan vehículos que llevan contenedores (turbo y sencillo quedan obsoletos)")
    def catalogos() -> e.Catalogos:
        return e.Catalogos(
            clientes=[e.ClienteCatalogo(cliente_id=c.cliente_id, nombre=c.nombre) for c in repo.clientes()],
            ubicaciones=[e.UbicacionCatalogo(ubicacion_id=u.ubicacion_id, nombre=u.nombre, tipo=u.tipo)
                         for u in repo.ubicaciones()],
            rutas=[e.RutaCatalogo(ruta_id=r.ruta_id, origen_id=r.origen_id, destino_id=r.destino_id,
                                  distancia_km=r.distancia_km) for r in repo.rutas()],
            tipos_vehiculo=[e.TipoVehiculoCatalogo(tipo_vehiculo_id=t.tipo_vehiculo_id, nombre=t.nombre,
                                                   cap_teu=t.cap_teu, cap_kg=t.cap_kg, carga_especial=t.carga_especial)
                            for t in repo.tipos_vehiculo() if t.cap_teu > 0],
            tipos_carga=[e.TipoCargaCatalogo(tipo_carga=None, nombre="General")]
                        + [e.TipoCargaCatalogo(tipo_carga=c, nombre=NOMBRES_CARGA[c]) for c in CARGAS_ESPECIALES],
        )

    @app.get("/catalogos/formulario", response_model=e.CatalogosSalida, tags=["Catálogos"], summary="Catálogos y destinos según cobertura, sin evaluar una solicitud")
    def catalogos_formulario(origen_id: Optional[str] = None, fecha_servicio: Optional[date] = None):
        return construir_catalogos(repo, origen_id, fecha_servicio)

    def _evaluar(s: Solicitud, escenario_id: Optional[str] = None) -> e.Evaluacion:
        try:
            return servicio.evaluar(s, escenario_id)
        except RutaNoEncontrada:
            raise _error_422(f"No existe la ruta {s.origen_id} → {s.destino_id}", "destino_id") from None

    @app.post("/solicitudes/evaluar", response_model=e.Evaluacion, tags=["Solicitudes"],
              summary="Evalúa una solicitud: candidatos simulados, cancelados con sus razones y casi elegibles")
    def evaluar(entrada: e.SolicitudEntrada) -> e.Evaluacion:
        if entrada.cliente_id not in {c.cliente_id for c in repo.clientes()}:
            raise _error_422(f"El cliente '{entrada.cliente_id}' no existe en el catálogo", "cliente_id")
        _validar_vehiculo(entrada)
        try:
            Solicitud(**entrada.model_dump())  # valida reglas de dominio antes de gastar un consecutivo
        except ValidationError as ex:
            raise RequestValidationError(ex.errors()) from None
        if repo.ruta(entrada.origen_id, entrada.destino_id) is None:
            raise _error_422(f"No existe la ruta {entrada.origen_id} → {entrada.destino_id}", "destino_id")
        s = Solicitud(**entrada.model_dump(), solicitud_id=registro.nuevo_solicitud_id())
        evaluacion = _evaluar(s)
        registro.guardar_solicitud(s, evaluacion)
        return evaluacion

    def _validar_vehiculo(entrada: e.SolicitudEntrada) -> None:
        """El tipo exigido debe existir y algún vehículo debe poder llevar un contenedor de ese peso."""
        catalogo = {t.tipo_vehiculo_id: t for t in repo.tipos_vehiculo()}
        kg = f"{entrada.peso_kg:,.0f}".replace(",", ".")
        if entrada.tipo_vehiculo_id is not None:
            t = catalogo.get(entrada.tipo_vehiculo_id)
            if t is None:
                raise _error_422(f"El tipo de vehículo '{entrada.tipo_vehiculo_id}' no existe en el catálogo; "
                                 f"use uno de {sorted(catalogo)}", "tipo_vehiculo_id")
            if t.cap_teu == 0:
                raise _error_422(f"{t.nombre} no lleva contenedores y el sistema solo transporta contenedores "
                                 "(vehículo obsoleto)", "tipo_vehiculo_id")
            if contenedores_por_vehiculo(entrada.peso_kg, t) == 0:
                raise _error_422(f"{t.nombre} no puede llevar un contenedor de {kg} kg: soporta "
                                 f"{t.cap_kg:,.0f} kg".replace(",", "."), "tipo_vehiculo_id")
        elif not any(contenedores_por_vehiculo(entrada.peso_kg, t) > 0 for t in catalogo.values()):
            maximo = max((t.cap_kg for t in catalogo.values() if t.cap_teu > 0), default=0)
            raise _error_422(f"Ningún vehículo del catálogo puede llevar un contenedor de {kg} kg "
                             f"(máximo {maximo:,.0f} kg)".replace(",", "."), "peso_kg")

    def _registrada(solicitud_id: str):
        r = registro.solicitud(solicitud_id)
        if r is None:
            raise HTTPException(status_code=404, detail=f"No existe la solicitud {solicitud_id}")
        return r

    @app.get("/solicitudes/{solicitud_id}", response_model=e.Evaluacion, tags=["Solicitudes"],
             summary="Evaluación original de una solicitud")
    def ver_solicitud(solicitud_id: str) -> e.Evaluacion:
        return _registrada(solicitud_id).evaluacion

    @app.post("/solicitudes/{solicitud_id}/escenario", response_model=e.Evaluacion, tags=["Solicitudes"],
              summary="¿Y si…? Vuelve a evaluar con otro plazo; la solicitud original no cambia")
    def escenario(solicitud_id: str, entrada: e.EscenarioEntrada) -> e.Evaluacion:
        r = _registrada(solicitud_id)
        cambios = entrada.model_dump(exclude_none=True)
        s = r.solicitud.model_copy(update=cambios)
        escenario_id = registro.nuevo_escenario_id(solicitud_id)
        evaluacion = _evaluar(s, escenario_id)
        registro.guardar_escenario(solicitud_id, escenario_id, s, evaluacion)
        return evaluacion

    @app.post("/decisiones", response_model=e.Decision, status_code=201, tags=["Decisiones"],
              summary="Registra la elección del funcionario con su justificación y un snapshot de lo que vio")
    def decidir(entrada: e.DecisionEntrada) -> e.Decision:
        """Guarda la solicitud en `transporte.solicitud` (pendiente de servicio) y la decisión en el registro.

        Con PostgreSQL, si la base no responde se devuelve 503 y no queda nada registrado.
        """
        r = _registrada(entrada.solicitud_id)
        solicitud, evaluacion = r.solicitud, r.evaluacion
        if entrada.escenario_id is not None:
            if entrada.escenario_id not in r.escenarios:
                raise HTTPException(status_code=404, detail=f"No existe el escenario {entrada.escenario_id}")
            solicitud, evaluacion = r.escenarios[entrada.escenario_id]
        previa = registro.decision_de(entrada.solicitud_id)
        if previa is not None:
            raise SolicitudYaDecidida(f"La solicitud {entrada.solicitud_id} ya tiene la decisión {previa.decision_id}")
        elegibles = {c.proveedor_id: c for c in evaluacion.candidatos}
        casi = {c.proveedor_id: c for c in evaluacion.casi_elegibles}
        elegido = elegibles.get(entrada.proveedor_id) or casi.get(entrada.proveedor_id)
        if elegido is None:
            raise _error_422(f"El proveedor {entrada.proveedor_id} no es candidato ni casi elegible en esta evaluación",
                             "proveedor_id")
        tipo = elegido.vehiculos.tipo_vehiculo_id if elegido.vehiculos is not None else solicitud.tipo_vehiculo_id
        if tipo is None:
            raise _error_422(f"{elegido.nombre} no tiene tarifa para ningún vehículo válido en esta ruta: indique "
                             "tipo_vehiculo_id en la solicitud para poder registrarla", "proveedor_id")
        nombre_cliente = next(c.nombre for c in repo.clientes() if c.cliente_id == solicitud.cliente_id)
        fila = solicitud_decidida(solicitud, evaluacion.ruta.ruta_id, nombre_cliente, tipo)
        return registro.registrar_decision(lambda decision_id: e.Decision(
            decision_id=decision_id, solicitud_id=entrada.solicitud_id, escenario_id=entrada.escenario_id,
            proveedor_id=entrada.proveedor_id, nombre=elegido.nombre, tipo_vehiculo_id=tipo,
            flexibilizado=entrada.proveedor_id not in elegibles, justificacion=entrada.justificacion,
            fecha_hora=datetime.now(timezone.utc), snapshot=evaluacion.model_copy(deep=True),
        ), fila)

    @app.get("/decisiones/{decision_id}", response_model=e.Decision, tags=["Decisiones"],
             summary="Decisión registrada con su snapshot")
    def ver_decision(decision_id: str) -> e.Decision:
        d = registro.decision(decision_id)
        if d is None:
            raise HTTPException(status_code=404, detail=f"No existe la decisión {decision_id}")
        return d

    @app.get("/decisiones/{decision_id}/informe", response_class=HTMLResponse, tags=["Decisiones"],
             summary="Informe descargable (HTML imprimible o guardable como PDF) con todo lo que vio el funcionario")
    def informe(decision_id: str, descargar: bool = True) -> HTMLResponse:
        d = registro.decision(decision_id)
        if d is None:
            raise HTTPException(status_code=404, detail=f"No existe la decisión {decision_id} (las decisiones "
                                                        "viven en memoria hasta que se reinicia el servidor)")
        r = registro.solicitud(d.solicitud_id)
        solicitud = r.escenarios[d.escenario_id][0] if d.escenario_id else r.solicitud
        cliente = next((c.nombre for c in repo.clientes() if c.cliente_id == solicitud.cliente_id), solicitud.cliente_id)
        modo = "attachment" if descargar else "inline"
        return HTMLResponse(construir_informe(d, solicitud, cliente),
                            headers={"Content-Disposition": f'{modo}; filename="{nombre_archivo(d)}"'})

    @app.post("/solicitudes/{solicitud_id}/cierre", response_model=e.ServicioSalida, status_code=201,
              tags=["Solicitudes"],
              summary="Registra el resultado real del viaje en transporte.servicio y actualiza el modelo")
    def cerrar_viaje(solicitud_id: str, entrada: e.CierreEntrada) -> e.ServicioSalida:
        """El viaje debe estar guardado en la base (se guarda al decidir; también sirve una solicitud pendiente
        cargada por el equipo de BD). Desde la respuesta, D y C del proveedor ya incluyen este viaje."""
        try:
            numero = numero_solicitud(solicitud_id)
        except ValueError as ex:
            raise _error_422(str(ex), None) from None
        decision = registro.decision_de(solicitud_id)
        avisos = []
        proveedor_id = entrada.proveedor_id or (decision.proveedor_id if decision else None)
        if proveedor_id is None:
            raise _error_422("Indique proveedor_id: no hay una decisión registrada en memoria para esta solicitud",
                             "proveedor_id")
        proveedor = next((p for p in repo.proveedores() if p.proveedor_id == proveedor_id), None)
        if proveedor is None:
            raise _error_422(f"El proveedor {proveedor_id} no existe en el catálogo", "proveedor_id")
        if decision is not None and decision.proveedor_id != proveedor_id:
            avisos.append(f"El viaje lo hizo {proveedor.nombre}, distinto del elegido en {decision.decision_id} "
                          f"({decision.nombre})")
        precio = entrada.precio_cop
        if precio is None and decision is not None and decision.proveedor_id == proveedor_id:
            elegido = next((c for c in decision.snapshot.candidatos if c.proveedor_id == proveedor_id), None)
            precio = elegido.costo_cop if elegido else None
        if precio is None:
            raise _error_422("Indique precio_cop: no se conoce el costo pactado de este viaje", "precio_cop")
        entrega = entrada.fecha_entrega_real
        if entrega.tzinfo is not None:
            entrega = entrega.astimezone(timezone(timedelta(hours=cfg.cierre.utc_offset_horas))).replace(tzinfo=None)
        calificacion = entrada.calificacion if entrada.calificacion is not None else cfg.cierre.calificacion_por_defecto
        if entrada.calificacion is None:
            avisos.append(f"Sin calificación: se guardó el valor neutro {calificacion} (el modelo no la usa)")

        corte = max(hoy(), entrega.date()) + timedelta(days=1)   # incluye viajes entregados hoy
        antes = servicio.ficha(proveedor_id, corte)
        s = registro.almacen.cerrar_viaje(CierreViaje(
            numero_solicitud=numero, proveedor_numero=int(proveedor_id.rsplit("-", 1)[-1]),
            fecha_entrega_real=entrega, precio_cop=precio,
            incidente=entrada.incidente or cfg.cierre.incidente_por_defecto, calificacion=calificacion))
        repo.recargar()                                          # el modelo ve el viaje nuevo desde ya
        despues = servicio.ficha(proveedor_id, corte)
        aviso_datos = getattr(repo, "aviso_datos", None)
        if aviso_datos:
            avisos.append(aviso_datos)
        return e.ServicioSalida(
            servicio_id=s.servicio_id, solicitud_id=solicitud_id, proveedor_id=proveedor_id, nombre=proveedor.nombre,
            precio_cop=s.precio_cop, fecha_servicio=s.fecha_servicio, fecha_entrega_real=s.fecha_entrega_real,
            transito_real_h=s.transito_real_h, plazo_h=round(s.plazo_h, 2), a_tiempo=s.a_tiempo,
            incidente=s.incidente, calificacion=s.calificacion, calificacion_por_defecto=entrada.calificacion is None,
            desempeno_antes=antes.desempeno.valor, desempeno_despues=despues.desempeno.valor,
            servicios_antes=antes.servicios, servicios_despues=despues.servicios, avisos=avisos)

    @app.get("/proveedores/{proveedor_id}", response_model=e.FichaProveedor, tags=["Proveedores"],
             summary="Ficha: historial, tendencia de D, fortalezas y debilidades")
    def ficha(proveedor_id: str) -> e.FichaProveedor:
        f = servicio.ficha(proveedor_id, hoy())
        if f is None:
            raise HTTPException(status_code=404, detail=f"No existe el proveedor {proveedor_id}")
        return f

    return app


# CORS por fuera de FastAPI: también cubre los errores 500 del servidor.
app = envolver_cors(crear_app())


