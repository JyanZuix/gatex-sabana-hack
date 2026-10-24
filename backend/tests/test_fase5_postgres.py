"""Adaptador PostgreSQL: conversión de las tablas del esquema `transporte` a modelos de dominio.

Usa filas hechas a mano con la forma de las tablas reales (no se conecta a la base).
"""
from copy import deepcopy
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api.app import crear_app
from backend.api.registro import Registro
from backend.datos.postgres import ErrorMapeo, RepositorioPostgres
from backend.dominio import Solicitud
from backend.filtro import filtrar

TABLAS = {
    "tipo_vehiculo": [
        {"tipo_vehiculo": "turbo", "nombre": "Turbo", "cap_teu": 0, "cap_kg": 4500, "carga_especial": None},
        {"tipo_vehiculo": "tractomula", "nombre": "Tractomula", "cap_teu": 2, "cap_kg": 34000, "carga_especial": None},
        {"tipo_vehiculo": "refrigerado", "nombre": "Refrigerado", "cap_teu": 2, "cap_kg": 28000,
         "carga_especial": "refrigerado"},
        {"tipo_vehiculo": "cama_baja", "nombre": "Cama baja", "cap_teu": 2, "cap_kg": 45000,
         "carga_especial": "sobredimensionado"},
    ],
    "cliente": [
        {"cliente_id": 1, "nombre": "Agroquímicos Andinos", "activo": True, "fecha_alta": date(2024, 1, 1)},
        {"cliente_id": 16, "nombre": "Plásticos Bogotá", "activo": True, "fecha_alta": date(2024, 1, 1)},
    ],
    "proveedor": [
        {"proveedor_id": 1, "nombre": "Transportes Andinos del Sur", "ciudad_base": "Cali", "activo": True,
         "apto_carga_peligrosa": False, "apto_refrigerada": False, "fecha_vinculacion": date(2019, 3, 1)},
        {"proveedor_id": 7, "nombre": "Transpesados de Colombia", "ciudad_base": "Medellín", "activo": True,
         "apto_carga_peligrosa": False, "apto_refrigerada": False, "fecha_vinculacion": date(2017, 2, 1)},
        {"proveedor_id": 12, "nombre": "Carga Nacional TLC", "ciudad_base": "Barranquilla", "activo": False,
         "apto_carga_peligrosa": False, "apto_refrigerada": False, "fecha_vinculacion": date(2019, 1, 1)},
    ],
    "flota": [
        {"flota_id": 1, "proveedor_id": 1, "tipo_vehiculo": "turbo", "cantidad": 8, "disponibles_semana": 4},
        {"flota_id": 3, "proveedor_id": 1, "tipo_vehiculo": "tractomula", "cantidad": 25, "disponibles_semana": 9},
        {"flota_id": 20, "proveedor_id": 7, "tipo_vehiculo": "cama_baja", "cantidad": 3, "disponibles_semana": 2},
        {"flota_id": 30, "proveedor_id": 12, "tipo_vehiculo": "tractomula", "cantidad": 10, "disponibles_semana": 5},
    ],
    "capacidad_actual": [
        {"proveedor_id": 1, "fecha": date(2026, 10, 28), "servicios_disponibles": 5},
        {"proveedor_id": 7, "fecha": date(2026, 10, 28), "servicios_disponibles": 2},
    ],
    "ruta": [
        {"ruta_id": 2, "origen": "Buenaventura", "destino": "Bogotá", "distancia_km": 515},
        {"ruta_id": 9, "origen": "Bogotá", "destino": "Buenaventura", "distancia_km": 515},
    ],
    "tarifa": [
        {"tarifa_id": 1, "proveedor_id": 1, "ruta_id": 2, "tipo_vehiculo": "turbo", "precio_cop": 1_900_000,
         "transito_estimado_h": 22},
        {"tarifa_id": 3, "proveedor_id": 1, "ruta_id": 2, "tipo_vehiculo": "tractomula", "precio_cop": 4_500_000,
         "transito_estimado_h": 30},
        {"tarifa_id": 50, "proveedor_id": 7, "ruta_id": 2, "tipo_vehiculo": "cama_baja", "precio_cop": 9_000_000,
         "transito_estimado_h": 36},
        {"tarifa_id": 60, "proveedor_id": 12, "ruta_id": 2, "tipo_vehiculo": "tractomula", "precio_cop": 3_800_000,
         "transito_estimado_h": 28},
    ],
    "solicitud": [
        {"solicitud_id": 1, "cliente_id": 16, "cliente": "Plásticos Bogotá", "ruta_id": 2, "tipo_vehiculo": "tractomula",
         "tipo_carga": "general", "peso_kg": 25000, "fecha_recogida": datetime(2026, 5, 2, 13),
         "fecha_entrega_limite": datetime(2026, 5, 3, 21)},
        {"solicitud_id": 2, "cliente_id": 1, "cliente": "Agroquímicos Andinos", "ruta_id": 2, "tipo_vehiculo": "tractomula",
         "tipo_carga": "general", "peso_kg": 23000, "fecha_recogida": datetime(2026, 4, 4, 14),
         "fecha_entrega_limite": datetime(2026, 4, 6, 16)},
    ],
    "servicio": [
        {"servicio_id": 1, "solicitud_id": 1, "proveedor_id": 1, "precio_cop": 4_500_000, "fecha_servicio": date(2026, 5, 2),
         "fecha_entrega_real": datetime(2026, 5, 3, 19), "transito_real_h": 30, "a_tiempo": True,
         "incidente": "ninguno", "calificacion": 4},
        {"servicio_id": 2, "solicitud_id": 2, "proveedor_id": 1, "precio_cop": 4_500_000, "fecha_servicio": date(2026, 4, 4),
         "fecha_entrega_real": datetime(2026, 4, 7, 5), "transito_real_h": 63, "a_tiempo": False,
         "incidente": "robo", "calificacion": 2},
    ],
}


def _repo(tablas=None, cfg=None):
    tablas = deepcopy(TABLAS) if tablas is None else tablas
    return RepositorioPostgres("postgresql://prueba", cfg=cfg, leer_tablas=lambda: tablas)


def test_catalogo_de_vehiculos_sale_de_la_tabla(cfg):
    tipos = {t.tipo_vehiculo_id: t for t in _repo(cfg=cfg).tipos_vehiculo()}
    assert set(tipos) == {"turbo", "tractomula", "refrigerado", "cama_baja"}
    assert (tipos["tractomula"].cap_teu, tipos["tractomula"].cap_kg) == (2, 34000)
    assert tipos["cama_baja"].carga_especial == "sobredimensionado"


def test_clientes_con_identificador_propio(cfg):
    repo = _repo(cfg=cfg)
    assert [(c.cliente_id, c.nombre) for c in repo.clientes()] == [("CLI-001", "Agroquímicos Andinos"),
                                                                  ("CLI-016", "Plásticos Bogotá")]
    assert {s.servicio_id: s.cliente_id for s in repo.servicios_historicos()} == {"SRV-0001": "CLI-016",
                                                                                 "SRV-0002": "CLI-001"}


def test_compatibilidad_sin_tabla_cliente(cfg):
    tablas = deepcopy(TABLAS)
    del tablas["cliente"]
    for f in tablas["solicitud"]:
        del f["cliente_id"]
    repo = _repo(tablas, cfg)
    assert {c.cliente_id for c in repo.clientes()} == {"Plásticos Bogotá", "Agroquímicos Andinos"}
    assert {s.cliente_id for s in repo.servicios_historicos()} == {"Plásticos Bogotá", "Agroquímicos Andinos"}


def test_historial_sin_incidentes_ni_calificacion(cfg):
    s = {x.servicio_id: x for x in _repo(cfg=cfg).servicios_historicos()}["SRV-0001"]
    assert (s.tiempo_prometido_h, s.tiempo_real_h, s.plazo_acordado_h, s.a_tiempo) == (30, 30, 32, True)
    assert not hasattr(s, "incidente") and not hasattr(s, "calificacion")


def test_proveedores_ids_estado_y_cargas(cfg):
    p = {x.proveedor_id: x for x in _repo(cfg=cfg).proveedores()}
    assert p["PROV-12"].estado == "inactivo"
    assert "sobredimensionado" in p["PROV-07"].cargas_especiales      # tiene cama baja


def test_falta_tabla_tipo_vehiculo(cfg):
    tablas = deepcopy(TABLAS)
    del tablas["tipo_vehiculo"]
    with pytest.raises(ErrorMapeo, match="tipo_vehiculo"):
        _repo(tablas, cfg).proveedores()


def test_tipo_de_vehiculo_sin_fila_en_el_catalogo(cfg):
    tablas = deepcopy(TABLAS)
    tablas["tipo_vehiculo"] = [t for t in tablas["tipo_vehiculo"] if t["tipo_vehiculo"] != "turbo"]
    with pytest.raises(ErrorMapeo, match="turbo"):
        _repo(tablas, cfg).proveedores()


def test_carga_especial_desconocida(cfg):
    tablas = deepcopy(TABLAS)
    tablas["tipo_vehiculo"][2]["carga_especial"] = "congelada"
    with pytest.raises(ErrorMapeo, match="congelada"):
        _repo(tablas, cfg).tipos_vehiculo()


def test_solicitud_con_cliente_que_no_existe(cfg):
    tablas = deepcopy(TABLAS)
    tablas["solicitud"][0]["cliente_id"] = 99
    with pytest.raises(ErrorMapeo, match="99"):
        _repo(tablas, cfg).clientes()


def test_filtro_con_datos_de_la_base(cfg):
    """3 contenedores de 20 000 kg: la tractomula lleva 1 por peso → 3 vehículos; el turbo no es opción."""
    s = Solicitud(cliente_id="CLI-016", origen_id="Buenaventura", destino_id="Bogotá", fecha_servicio=date(2026, 10, 28),
                  plazo_h=40, n_contenedores=3, peso_kg=20_000, presupuesto_cop=20_000_000)
    r = filtrar(s, _repo(cfg=cfg), cfg)
    (c,) = r.candidatos
    assert c.proveedor.proveedor_id == "PROV-01"
    assert (c.opcion.tipo_vehiculo_id, c.opcion.viajes, c.opcion.reparto, c.opcion.costo) == \
        ("tractomula", 3, (1, 1, 1), 13_500_000)
    cancelados = {x.proveedor.proveedor_id: [z.codigo for z in x.razones] for x in r.cancelados}
    assert "PROVEEDOR_INACTIVO" in cancelados["PROV-12"]
    assert "VEHICULO_NO_DISPONIBLE" in cancelados["PROV-07"]   # solo tiene cama baja; la carga es general


def test_api_con_datos_de_la_base(cfg):
    api = TestClient(crear_app(repo=_repo(cfg=cfg), cfg=cfg, registro=Registro()))
    r = api.post("/solicitudes/evaluar", json=dict(
        cliente_id="CLI-016", origen_id="Buenaventura", destino_id="Bogotá", fecha_servicio="2026-10-28",
        plazo_h=40, n_contenedores=3, peso_kg=20_000, tipo_vehiculo_id="tractomula", presupuesto_cop=20_000_000))
    assert r.status_code == 200
    (c,) = r.json()["candidatos"]
    assert c["vehiculos"] == {"tipo_vehiculo_id": "tractomula", "tipo": "Tractomula", "cantidad": 3,
                              "contenedores_por_vehiculo": [1, 1, 1]}
    turbo = api.post("/solicitudes/evaluar", json=dict(
        cliente_id="CLI-016", origen_id="Buenaventura", destino_id="Bogotá", fecha_servicio="2026-10-28",
        plazo_h=40, n_contenedores=1, peso_kg=2_000, tipo_vehiculo_id="turbo", presupuesto_cop=1))
    assert turbo.status_code == 422 and "obsoleto" in turbo.json()["detalle"]


def test_base_caida_responde_503_en_espanol(cfg):
    from backend.datos import ErrorDatosNoDisponibles

    def caida():
        raise ErrorDatosNoDisponibles("No se pudo leer la base de datos (OperationalError).")
    api = TestClient(crear_app(repo=RepositorioPostgres("postgresql://x", cfg=cfg, leer_tablas=caida), cfg=cfg,
                               registro=Registro()))
    assert api.get("/salud").status_code == 200          # la API sigue viva
    r = api.get("/catalogos")
    assert r.status_code == 503 and "base de datos" in r.json()["detalle"]


def test_error_de_psycopg_se_traduce_sin_exponer_la_cadena(cfg):
    from backend.datos import ErrorDatosNoDisponibles
    repo = RepositorioPostgres("postgresql://usuario:secreto@127.0.0.1:1/x?connect_timeout=1", cfg=cfg)
    with pytest.raises(ErrorDatosNoDisponibles) as e:
        repo.proveedores()
    assert "secreto" not in str(e.value)


def test_catalogo_no_ofrece_vehiculos_sin_contenedores(cfg):
    """Solo se transportan contenedores: turbo y sencillo quedan obsoletos (decisión del 2026-10-24)."""
    api = TestClient(crear_app(repo=_repo(cfg=cfg), cfg=cfg, registro=Registro()))
    tipos = {t["tipo_vehiculo_id"] for t in api.get("/catalogos").json()["tipos_vehiculo"]}
    assert tipos == {"tractomula", "refrigerado", "cama_baja"}


def test_fila_para_transporte_solicitud():
    from backend.datos.almacen import parametros_insert, solicitud_decidida
    s = Solicitud(solicitud_id="REQ-0496", cliente_id="CLI-016", origen_id="Buenaventura", destino_id="Bogotá",
                  fecha_servicio=date(2026, 11, 3), plazo_h=33.5, n_contenedores=3, peso_kg=20_000,
                  tipo_carga="refrigerado", presupuesto_cop=1)
    p = parametros_insert(solicitud_decidida(s, "RUTA-02", "Plásticos Bogotá", "refrigerado"))
    assert p == {"solicitud_id": 496, "cliente_id": 16, "cliente": "Plásticos Bogotá", "ruta_id": 2,
                 "tipo_vehiculo": "refrigerado", "tipo_carga": "refrigerada", "peso_kg": 60_000,
                 "fecha_recogida": datetime(2026, 11, 3), "fecha_entrega_limite": datetime(2026, 11, 4, 9, 30)}
    general = parametros_insert(solicitud_decidida(s.model_copy(update={"tipo_carga": None}), "RUTA-02", "X", "tractomula"))
    assert general["tipo_carga"] == "general"


def test_fabrica_de_almacen():
    from backend.datos import AlmacenEnMemoria, AlmacenPostgres, crear_almacen
    assert isinstance(crear_almacen({"REPOSITORIO": "simulado"}), AlmacenEnMemoria)
    assert isinstance(crear_almacen({"REPOSITORIO": "postgres", "DATABASE_URL": "postgresql://x"}), AlmacenPostgres)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        crear_almacen({"REPOSITORIO": "postgres"})


def test_almacen_postgres_sin_base_responde_error_claro():
    from backend.datos import AlmacenPostgres, ErrorDatosNoDisponibles
    almacen = AlmacenPostgres("postgresql://usuario:secreto@127.0.0.1:1/x?connect_timeout=1")
    with pytest.raises(ErrorDatosNoDisponibles) as e:
        almacen.reservar_numero()
    assert "secreto" not in str(e.value)
