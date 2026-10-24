"""Comunicación del backend con la base: caché, cierre de viajes (servicio), actualización del modelo e informe.

Las pruebas usan una base de mentira en memoria con la forma de las tablas reales. La última prueba se conecta
a Supabase solo con `PRUEBAS_BD=1` y deshace todo con ROLLBACK (no deja datos).
"""
import os
from copy import deepcopy
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.api.app import crear_app
from backend.api.registro import Registro
from backend.datos import (AlmacenSolicitudes, CierreInvalido, CierreViaje, ErrorDatosNoDisponibles,
                           ServicioRegistrado, SolicitudNoEncontrada, SolicitudYaDecidida, ViajeYaCerrado)
from backend.datos.almacen import parametros_insert, resultado_del_viaje
from backend.datos.postgres import RepositorioPostgres

from .test_fase5_postgres import TABLAS

HOY = date(2026, 10, 24)


# --- Base de mentira: el almacén escribe en las mismas tablas que lee el repositorio ----------

class AlmacenTablas(AlmacenSolicitudes):
    """Imita a AlmacenPostgres sobre un diccionario de tablas (lo que lee RepositorioPostgres)."""

    def __init__(self, tablas):
        self.t = tablas

    def reservar_numero(self):
        return max(f["solicitud_id"] for f in self.t["solicitud"]) + 1

    def registrar(self, s):
        if any(f["solicitud_id"] == s.numero for f in self.t["solicitud"]):
            raise SolicitudYaDecidida("ya existe")
        self.t["solicitud"].append({**parametros_insert(s), "prioridad": "balanceado"})

    def cerrar_viaje(self, c: CierreViaje):
        so = next((f for f in self.t["solicitud"] if f["solicitud_id"] == c.numero_solicitud), None)
        if so is None:
            raise SolicitudNoEncontrada("no existe")
        if any(f["solicitud_id"] == c.numero_solicitud for f in self.t["servicio"]):
            raise ViajeYaCerrado("ya cerrado")
        r = resultado_del_viaje(so["fecha_recogida"], so["fecha_entrega_limite"], c)
        sid = max(f["servicio_id"] for f in self.t["servicio"]) + 1
        self.t["servicio"].append({
            "servicio_id": sid, "solicitud_id": c.numero_solicitud, "proveedor_id": c.proveedor_numero,
            "precio_cop": c.precio_cop, "fecha_servicio": r["fecha_servicio"], "fecha_entrega_real": c.fecha_entrega_real,
            "transito_real_h": r["transito_real_h"], "a_tiempo": r["a_tiempo"], "incidente": c.incidente,
            "calificacion": c.calificacion})
        return ServicioRegistrado(servicio_id=sid, numero_solicitud=c.numero_solicitud,
                                  proveedor_numero=c.proveedor_numero, precio_cop=c.precio_cop,
                                  fecha_entrega_real=c.fecha_entrega_real, incidente=c.incidente,
                                  calificacion=c.calificacion, **r)


@pytest.fixture
def base(cfg):
    tablas = deepcopy(TABLAS)
    repo = RepositorioPostgres("postgresql://prueba", cfg=cfg, leer_tablas=lambda: tablas)
    almacen = AlmacenTablas(tablas)
    api = TestClient(crear_app(repo=repo, cfg=cfg, registro=Registro(almacen), hoy=lambda: HOY))
    return api, tablas, repo


def _evaluar(api, **kw):
    datos = dict(cliente_id="CLI-016", origen_id="Buenaventura", destino_id="Bogotá", fecha_servicio="2026-10-28",
                 plazo_h=40, n_contenedores=1, peso_kg=20_000, tipo_vehiculo_id="tractomula", presupuesto_cop=10_000_000)
    datos.update(kw)
    r = api.post("/solicitudes/evaluar", json=datos)
    assert r.status_code == 200, r.text
    return r.json()


def _decidir(api, ev, justificacion="Mejor relación costo y tiempo"):
    r = api.post("/decisiones", json={"solicitud_id": ev["solicitud_id"],
                                      "proveedor_id": ev["candidatos"][0]["proveedor_id"],
                                      "justificacion": justificacion})
    assert r.status_code == 201, r.text
    return r.json()


# --- Caché del repositorio PostgreSQL --------------------------------------

class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_cache_se_refresca_al_vencer(cfg):
    lecturas = []
    tablas = deepcopy(TABLAS)

    def leer():
        lecturas.append(1)
        return tablas
    repo = RepositorioPostgres("postgresql://x", cfg=cfg, leer_tablas=leer)
    repo._reloj = reloj = Reloj()
    repo.proveedores(); repo.clientes()
    assert len(lecturas) == 1                                    # dentro del plazo: no relee
    reloj.t += cfg.datos.refresco_cache_s
    repo.proveedores()
    assert len(lecturas) == 2                                    # vencido: relee
    repo.recargar(); repo.proveedores()
    assert len(lecturas) == 3                                    # tras escribir: relee


def test_si_falla_el_refresco_se_usan_los_datos_anteriores(cfg):
    estado = {"caida": False}

    def leer():
        if estado["caida"]:
            raise ErrorDatosNoDisponibles("No se pudo leer la base de datos (OperationalError).")
        return deepcopy(TABLAS)
    repo = RepositorioPostgres("postgresql://x", cfg=cfg, leer_tablas=leer)
    repo._reloj = reloj = Reloj()
    assert len(repo.proveedores()) == 3
    estado["caida"] = True
    reloj.t += cfg.datos.refresco_cache_s
    assert len(repo.proveedores()) == 3 and "datos leídos antes" in repo.aviso_datos
    estado["caida"] = False
    repo.recargar(); repo.proveedores()
    assert repo.aviso_datos is None


def test_primera_lectura_fallida_sube_el_error(cfg):
    def leer():
        raise ErrorDatosNoDisponibles("caída")
    with pytest.raises(ErrorDatosNoDisponibles):
        RepositorioPostgres("postgresql://x", cfg=cfg, leer_tablas=leer).proveedores()


# --- Cálculo del resultado del viaje ------------------------------------------

def _cierre(entrega):
    return CierreViaje(numero_solicitud=1, proveedor_numero=1, fecha_entrega_real=entrega, precio_cop=1,
                       incidente="ninguno", calificacion=3)


def test_resultado_del_viaje_a_tiempo_y_tarde():
    recogida, limite = datetime(2026, 10, 28), datetime(2026, 10, 29, 16)          # plazo 40 h
    a = resultado_del_viaje(recogida, limite, _cierre(datetime(2026, 10, 29, 10)))
    assert (a["transito_real_h"], a["a_tiempo"], a["fecha_servicio"], a["plazo_h"]) == (34, True, date(2026, 10, 28), 40)
    b = resultado_del_viaje(recogida, limite, _cierre(datetime(2026, 10, 29, 16, 30)))
    assert (b["transito_real_h"], b["a_tiempo"]) == (41, False)                    # 40,5 h redondea a 41
    assert resultado_del_viaje(recogida, limite, _cierre(datetime(2026, 10, 29, 16)))["a_tiempo"] is True


def test_entrega_antes_de_la_recogida_es_invalida():
    with pytest.raises(CierreInvalido, match="posterior"):
        resultado_del_viaje(datetime(2026, 10, 28), datetime(2026, 10, 29), _cierre(datetime(2026, 10, 27, 23)))


# --- Ciclo completo: evaluar → decidir → cerrar → el modelo cambia -----------------

def test_ciclo_completo_actualiza_el_modelo(base):
    api, tablas, repo = base
    ev = _evaluar(api)
    elegido = ev["candidatos"][0]
    _decidir(api, ev)
    numero = int(ev["solicitud_id"][4:])
    assert any(f["solicitud_id"] == numero for f in tablas["solicitud"])        # la solicitud quedó en la base

    antes_ficha = api.get(f"/proveedores/{elegido['proveedor_id']}").json()
    r = api.post(f"/solicitudes/{ev['solicitud_id']}/cierre", json={"fecha_entrega_real": "2026-10-29T10:00:00"})
    assert r.status_code == 201, r.text
    s = r.json()
    assert (s["proveedor_id"], s["precio_cop"]) == (elegido["proveedor_id"], elegido["costo_cop"])  # de la decisión
    assert (s["transito_real_h"], s["plazo_h"], s["a_tiempo"]) == (34, 40, True)
    assert (s["calificacion"], s["calificacion_por_defecto"], s["incidente"]) == (3, True, "ninguno")
    assert s["servicios_despues"] == s["servicios_antes"] + 1
    assert s["desempeno_despues"] != s["desempeno_antes"]                       # el modelo usa el viaje nuevo
    assert any("valor neutro 3" in a for a in s["avisos"])
    # La ficha y las evaluaciones siguientes ya ven el servicio nuevo, sin reiniciar el servidor
    assert any(x.servicio_id == f"SRV-{s['servicio_id']:04d}" for x in repo.servicios_historicos())
    ev2 = _evaluar(api, fecha_servicio="2026-11-02")
    c2 = next(c for c in ev2["candidatos"] if c["proveedor_id"] == elegido["proveedor_id"])
    assert c2["desempeno"] != elegido["desempeno"]
    assert antes_ficha["servicios"] <= s["servicios_antes"]


def test_cerrar_dos_veces_da_409_y_entrega_imposible_422(base):
    api, *_ = base
    ev = _evaluar(api)
    _decidir(api, ev)
    url = f"/solicitudes/{ev['solicitud_id']}/cierre"
    assert api.post(url, json={"fecha_entrega_real": "2026-10-27T10:00:00"}).status_code == 422   # antes de recoger
    assert api.post(url, json={"fecha_entrega_real": "2026-10-29T18:00:00", "calificacion": 5}).status_code == 201
    assert api.post(url, json={"fecha_entrega_real": "2026-10-29T18:00:00"}).status_code == 409


def test_cierre_de_solicitud_sin_decision_exige_proveedor_y_precio(base):
    api, tablas, _ = base
    tablas["solicitud"].append({**tablas["solicitud"][0], "solicitud_id": 900})   # pendiente cargada por BD
    url = "/solicitudes/REQ-0900/cierre"
    r = api.post(url, json={"fecha_entrega_real": "2026-05-03T12:00:00"})
    assert r.status_code == 422 and r.json()["errores"][0]["campo"] == "proveedor_id"
    r = api.post(url, json={"fecha_entrega_real": "2026-05-03T12:00:00", "proveedor_id": "PROV-01"})
    assert r.status_code == 422 and r.json()["errores"][0]["campo"] == "precio_cop"
    r = api.post(url, json={"fecha_entrega_real": "2026-05-03T12:00:00", "proveedor_id": "PROV-01",
                            "precio_cop": 4_500_000, "incidente": "retraso", "calificacion": 2})
    assert r.status_code == 201 and (r.json()["incidente"], r.json()["calificacion"]) == ("retraso", 2)
    assert api.post("/solicitudes/REQ-0999/cierre", json={"fecha_entrega_real": "2026-05-03T12:00:00",
                                                          "proveedor_id": "PROV-01", "precio_cop": 1}).status_code == 404


def test_cierre_con_otro_proveedor_avisa(base):
    api, *_ = base
    ev = _evaluar(api)
    _decidir(api, ev)
    r = api.post(f"/solicitudes/{ev['solicitud_id']}/cierre",
                 json={"fecha_entrega_real": "2026-10-29T10:00:00", "proveedor_id": "PROV-07", "precio_cop": 5_000_000})
    assert r.status_code == 201 and any("distinto del elegido" in a for a in r.json()["avisos"])


def test_fecha_con_zona_horaria_se_pasa_a_hora_colombia(base):
    api, tablas, _ = base
    ev = _evaluar(api)
    _decidir(api, ev)
    r = api.post(f"/solicitudes/{ev['solicitud_id']}/cierre", json={"fecha_entrega_real": "2026-10-29T15:00:00Z"})
    assert r.json()["fecha_entrega_real"] == "2026-10-29T10:00:00"            # 15:00 UTC = 10:00 Colombia


# --- Informe descargable ---------------------------------------------------------

def test_informe_de_la_decision(base):
    api, *_ = base
    ev = _evaluar(api)
    d = _decidir(api, ev, justificacion="Conviene <script>alert(1)</script> por puntualidad")
    r = api.get(f"/decisiones/{d['decision_id']}/informe")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert r.headers["content-disposition"] == f'attachment; filename="informe_{d["decision_id"]}_{ev["solicitud_id"]}.html"'
    html = r.text
    assert d["nombre"] in html and "Elegido por el funcionario" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html and "<script>alert" not in html     # texto escapado
    for c in ev["cancelados"]:
        assert c["nombre"] in html and all(z["codigo"] in html for z in c["razones"])
    assert "Plásticos Bogotá" in html and "<svg" in html
    assert "asignó" not in html.lower()                                          # el sistema no decide
    assert api.get(f"/decisiones/{d['decision_id']}/informe?descargar=false").headers["content-disposition"].startswith("inline")
    assert api.get("/decisiones/DEC-9999/informe").status_code == 404


# --- Integración con Supabase (opcional, sin dejar datos) -------------------------------

@pytest.mark.skipif(os.environ.get("PRUEBAS_BD") != "1", reason="Solo con PRUEBAS_BD=1 y DATABASE_URL en .env")
def test_ciclo_contra_supabase_con_rollback(cfg):
    """Inserta solicitud y servicio en una transacción, comprueba que el modelo los lee y deshace todo."""
    import psycopg
    from psycopg.rows import dict_row

    from backend.datos import AlmacenPostgres
    from backend.datos.almacen import solicitud_decidida
    from backend.datos.fabrica import _entorno
    from backend.datos.postgres import TABLAS as NOMBRES, TABLAS_OPCIONALES
    from backend.dominio import Solicitud

    dsn = _entorno(None)["DATABASE_URL"]
    almacen = AlmacenPostgres(dsn)
    with psycopg.connect(dsn) as con:
        try:
            antes = con.execute("SELECT count(*) FROM transporte.servicio").fetchone()[0]
            n = con.execute("SELECT nextval(pg_get_serial_sequence('transporte.solicitud','solicitud_id'))").fetchone()[0]
            s = Solicitud(solicitud_id=f"REQ-{n:04d}", cliente_id="CLI-016", origen_id="Buenaventura",
                          destino_id="Bogotá", fecha_servicio=date(2026, 10, 20), plazo_h=33, n_contenedores=2,
                          peso_kg=15_000, presupuesto_cop=20_000_000)
            almacen.insertar(con, solicitud_decidida(s, "RUTA-02", "Plásticos Bogotá", "tractomula"))
            servicio = almacen.cerrar(con, CierreViaje(numero_solicitud=n, proveedor_numero=1,
                                                       fecha_entrega_real=datetime(2026, 10, 21, 6), precio_cop=9_000_000,
                                                       incidente="ninguno", calificacion=3))
            assert (servicio.transito_real_h, servicio.a_tiempo) == (30, True)
            cur = con.cursor(row_factory=dict_row)
            tablas = {t: cur.execute(f"SELECT * FROM transporte.{t}").fetchall() for t in NOMBRES + TABLAS_OPCIONALES}
            repo = RepositorioPostgres(dsn, cfg=cfg, leer_tablas=lambda: tablas)
            assert any(x.servicio_id == f"SRV-{servicio.servicio_id:04d}" and x.a_tiempo
                       for x in repo.servicios_historicos())
            assert len(tablas["servicio"]) == antes + 1
        finally:
            con.rollback()
        assert con.execute("SELECT count(*) FROM transporte.servicio").fetchone()[0] == antes
