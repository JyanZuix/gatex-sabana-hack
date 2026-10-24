"""API HTTP de la Sala de Simulación de Proveedores (FastAPI).

Arranque local:  uvicorn backend.api.app:app --reload
Documentación:   http://localhost:8000/docs
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Callable, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import Config, cargar_config
from backend.datos import Repositorio, crear_repositorio
from backend.dominio import Solicitud
from backend.filtro import RutaNoEncontrada

from . import esquemas as e
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
    registro = registro or Registro()
    servicio = ServicioEvaluacion(repo, cfg)

    app = FastAPI(
        title="Sala de Simulación de Proveedores · COSCO SHIPPING",
        description="Filtra proveedores de transporte terrestre con todas sus razones de descarte, simula a los "
                    "candidatos y registra la decisión del funcionario. La API no elige: el funcionario decide.",
        version="1.0.0",
    )
    origenes = [o.strip() for o in os.environ.get("CORS_ORIGENES", "*").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origenes, allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        errores = _errores_en_espanol(exc.errors())
        return JSONResponse(status_code=422, content={"detalle": "Datos de entrada no válidos", "errores": errores})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        detalle = GENERICOS.get(exc.detail, exc.detail) if isinstance(exc.detail, str) else exc.detail
        contenido = detalle if isinstance(detalle, dict) else {"detalle": detalle}
        return JSONResponse(status_code=exc.status_code, content=contenido)

    # ------------------------------------------------------------------
    @app.get("/salud", tags=["Sistema"], summary="Estado del servicio")
    def salud():
        return {"estado": "ok", "repositorio": type(repo).__name__.removeprefix("Repositorio").lower()}

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
              summary="¿Y si…? Vuelve a evaluar con otro plazo o penalidad; la solicitud original no cambia")
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
        r = _registrada(entrada.solicitud_id)
        evaluacion = r.evaluacion
        if entrada.escenario_id is not None:
            if entrada.escenario_id not in r.escenarios:
                raise HTTPException(status_code=404, detail=f"No existe el escenario {entrada.escenario_id}")
            evaluacion = r.escenarios[entrada.escenario_id][1]
        elegibles = {c.proveedor_id: c.nombre for c in evaluacion.candidatos}
        casi = {c.proveedor_id: c.nombre for c in evaluacion.casi_elegibles}
        if entrada.proveedor_id not in elegibles and entrada.proveedor_id not in casi:
            raise _error_422(f"El proveedor {entrada.proveedor_id} no es candidato ni casi elegible en esta evaluación",
                             "proveedor_id")
        decision = e.Decision(
            decision_id=registro.nuevo_decision_id(), solicitud_id=entrada.solicitud_id,
            escenario_id=entrada.escenario_id, proveedor_id=entrada.proveedor_id,
            nombre=elegibles.get(entrada.proveedor_id) or casi[entrada.proveedor_id],
            flexibilizado=entrada.proveedor_id not in elegibles, justificacion=entrada.justificacion,
            fecha_hora=datetime.now(timezone.utc), snapshot=evaluacion.model_copy(deep=True),
        )
        registro.guardar_decision(decision)
        return decision

    @app.get("/decisiones/{decision_id}", response_model=e.Decision, tags=["Decisiones"],
             summary="Decisión registrada con su snapshot")
    def ver_decision(decision_id: str) -> e.Decision:
        d = registro.decision(decision_id)
        if d is None:
            raise HTTPException(status_code=404, detail=f"No existe la decisión {decision_id}")
        return d

    @app.get("/proveedores/{proveedor_id}", response_model=e.FichaProveedor, tags=["Proveedores"],
             summary="Ficha: historial, tendencia de D, fortalezas y debilidades")
    def ficha(proveedor_id: str) -> e.FichaProveedor:
        f = servicio.ficha(proveedor_id, hoy())
        if f is None:
            raise HTTPException(status_code=404, detail=f"No existe el proveedor {proveedor_id}")
        return f

    return app


app = crear_app()
