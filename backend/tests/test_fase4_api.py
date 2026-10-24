"""Fase 4: API HTTP con los datos sintéticos (contrato de README, sección 5)."""
import pytest
from fastapi.testclient import TestClient

from backend.api.app import crear_app
from backend.api.registro import Registro
from backend.datos import AlmacenEnMemoria, ErrorDatosNoDisponibles


@pytest.fixture
def cliente(repo, cfg):
    return TestClient(crear_app(repo=repo, cfg=cfg, registro=Registro()))


def _solicitud(**cambios):
    datos = dict(cliente_id="CLI-0001", origen_id="BUN", destino_id="BOG", fecha_servicio="2026-10-28",
                 plazo_h=40, n_contenedores=4, peso_kg=10_000, presupuesto_cop=15_000_000)
    datos.update(cambios)
    return {k: v for k, v in datos.items() if v is not None}


def test_salud(cliente):
    assert cliente.get("/salud").json() == {"estado": "ok", "repositorio": "simulado"}


def test_evaluar_devuelve_candidatos_y_cancelados(cliente):
    r = cliente.post("/solicitudes/evaluar", json=_solicitud())
    assert r.status_code == 200
    j = r.json()
    assert j["solicitud_id"] == "REQ-0001" and not j["sin_candidatos"]
    assert j["candidatos"] and j["cancelados"]
    assert all(c["razones"] for c in j["cancelados"])
    c = j["candidatos"][0]
    assert "prob_incidente" not in c
    assert set(c["confianza"]["desglose"]) == {"consistencia", "cumplimiento_cliente", "evidencia"}


def test_candidatos_ordenados_por_puntaje_con_top_4(cliente, cfg):
    j = cliente.post("/solicitudes/evaluar", json=_solicitud()).json()
    cands = j["candidatos"]
    assert len(cands) > cfg.puntaje.top_n  # los datos sintéticos dejan 5 candidatos
    assert [c["puesto"] for c in cands] == list(range(1, len(cands) + 1))
    valores = [c["puntaje"]["valor"] for c in cands]
    assert valores == sorted(valores, reverse=True)
    assert [c["top"] for c in cands] == [p <= cfg.puntaje.top_n for p in range(1, len(cands) + 1)]
    for c in cands:
        assert c["puntaje"]["valor"] == pytest.approx(sum(c["puntaje"]["desglose"].values()), abs=0.25)
    assert j["parametros_escenario"]["pesos_puntaje"] == {"profit": 0.4, "a_tiempo": 0.3, "desempeno": 0.15,
                                                          "confianza": 0.15, "top_n": 4}


def test_ningun_candidato_da_perdida(cliente):
    # Presupuesto justo: algunos proveedores quedan por encima y se descartan con SIN_MARGEN
    j = cliente.post("/solicitudes/evaluar", json=_solicitud(presupuesto_cop=9_000_000)).json()
    assert all(c["profit"]["cop"] >= 0 and c["costo_cop"] <= 9_000_000 for c in j["candidatos"])
    sin_margen = [c for c in j["cancelados"] if any(r["codigo"] == "SIN_MARGEN" for r in c["razones"])]
    assert sin_margen
    assert all(r["requerido"] == 9_000_000 and r["disponible"] > 9_000_000
               for c in sin_margen for r in c["razones"] if r["codigo"] == "SIN_MARGEN")


def test_si_todos_dan_perdida_aparecen_casi_elegibles(cliente):
    j = cliente.post("/solicitudes/evaluar", json=_solicitud(presupuesto_cop=1_000)).json()
    assert j["sin_candidatos"] and not j["candidatos"]
    flexibilizar = [c["flexibilizar"] for c in j["casi_elegibles"] if c["razon"]["codigo"] == "SIN_MARGEN"]
    assert flexibilizar and all(f.startswith("Aumentar el presupuesto a $") for f in flexibilizar)


def test_presupuesto_cero_es_invalido(cliente):
    assert cliente.post("/solicitudes/evaluar", json=_solicitud(presupuesto_cop=0)).status_code == 422


def test_vehiculos_incluyen_contenedores_por_vehiculo(cliente):
    j = cliente.post("/solicitudes/evaluar", json=_solicitud(n_contenedores=3)).json()
    for c in j["candidatos"]:
        v = c["vehiculos"]
        assert sum(v["contenedores_por_vehiculo"]) == 3 and len(v["contenedores_por_vehiculo"]) == v["cantidad"]
    plataforma = next(c for c in j["candidatos"] if c["vehiculos"]["tipo"] == "Tractocamión plataforma 40'")
    assert plataforma["vehiculos"]["contenedores_por_vehiculo"] == [2, 1]


def test_contenedor_que_no_cabe_en_el_vehiculo_exigido_da_422(cliente):
    r = cliente.post("/solicitudes/evaluar", json=_solicitud(peso_kg=20_000, tipo_vehiculo_id="TV-SENC20"))
    assert r.status_code == 422 and r.json()["errores"][0]["campo"] == "tipo_vehiculo_id"
    assert "20.000 kg" in r.json()["detalle"]


def test_contenedor_que_no_cabe_en_ningun_vehiculo_da_422(cliente):
    r = cliente.post("/solicitudes/evaluar", json=_solicitud(peso_kg=60_000))
    assert r.status_code == 422 and r.json()["errores"][0]["campo"] == "peso_kg"
    assert "máximo 45.000 kg" in r.json()["detalle"]


def test_consecutivos_distintos(cliente):
    a = cliente.post("/solicitudes/evaluar", json=_solicitud()).json()["solicitud_id"]
    b = cliente.post("/solicitudes/evaluar", json=_solicitud()).json()["solicitud_id"]
    assert (a, b) == ("REQ-0001", "REQ-0002")


@pytest.mark.parametrize("cambios,campo", [
    (dict(n_contenedores=0), "n_contenedores"),
    (dict(n_contenedores=None), "n_contenedores"),
    (dict(peso_kg=0), "peso_kg"),
    (dict(peso_kg=None), "peso_kg"),
    (dict(n_teu=2), "n_teu"),            # campos de la versión anterior: ya no existen
    (dict(toneladas=20), "toneladas"),
])
def test_solicitud_invalida_da_422_en_espanol(cliente, cambios, campo):
    r = cliente.post("/solicitudes/evaluar", json=_solicitud(**cambios))
    assert r.status_code == 422
    errores = r.json()["errores"]
    assert any(e["campo"] == campo for e in errores)
    assert all(e["mensaje"] and "Field" not in e["mensaje"] for e in errores)


def test_cliente_inexistente_da_422(cliente):
    r = cliente.post("/solicitudes/evaluar", json=_solicitud(cliente_id="CLI-9999"))
    assert r.status_code == 422 and "CLI-9999" in r.json()["detalle"]


def test_tipo_de_vehiculo_inexistente_da_422(cliente):
    r = cliente.post("/solicitudes/evaluar", json=_solicitud(tipo_vehiculo_id="TV-NAVE"))
    assert r.status_code == 422 and "TV-NAVE" in r.json()["detalle"]


def test_tipo_de_vehiculo_indicado_es_obligatorio(cliente):
    """Con `tipo_vehiculo_id` solo se consideran tarifas y flota de ese tipo."""
    libre = cliente.post("/solicitudes/evaluar", json=_solicitud()).json()
    exigido = cliente.post("/solicitudes/evaluar", json=_solicitud(tipo_vehiculo_id="TV-SENC20")).json()
    assert {c["vehiculos"]["tipo"] for c in libre["candidatos"]} == {"Tractocamión plataforma 40'"}
    assert {c["vehiculos"]["tipo"] for c in exigido["candidatos"]} <= {"Camión sencillo 20'"}
    assert len(exigido["candidatos"]) + len(exigido["cancelados"]) == len(libre["candidatos"]) + len(libre["cancelados"])


def test_escenario_no_cambia_la_solicitud_original(cliente):
    original = cliente.post("/solicitudes/evaluar", json=_solicitud()).json()
    sid = original["solicitud_id"]
    esc = cliente.post(f"/solicitudes/{sid}/escenario", json={"plazo_h": 20})
    assert esc.status_code == 200 and esc.json()["escenario_id"] == f"{sid}-E1"
    assert esc.json()["parametros_escenario"]["plazo_h"] == 20
    assert cliente.get(f"/solicitudes/{sid}").json() == original


def test_escenario_solo_acepta_plazo(cliente):
    sid = cliente.post("/solicitudes/evaluar", json=_solicitud()).json()["solicitud_id"]
    for cuerpo in ({"p_evento": 1.0}, {"plazo_h": 20, "penal_hora_cop": 50_000}, {}):
        assert cliente.post(f"/solicitudes/{sid}/escenario", json=cuerpo).status_code == 422


def test_decision_exige_justificacion_y_guarda_snapshot(cliente):
    ev = cliente.post("/solicitudes/evaluar", json=_solicitud()).json()
    pid = ev["candidatos"][0]["proveedor_id"]
    sin = cliente.post("/decisiones", json={"solicitud_id": ev["solicitud_id"], "proveedor_id": pid,
                                            "justificacion": "   "})
    assert sin.status_code == 422
    con = cliente.post("/decisiones", json={"solicitud_id": ev["solicitud_id"], "proveedor_id": pid,
                                            "justificacion": "Mejor puntualidad con este cliente"})
    assert con.status_code == 201
    d = cliente.get(f"/decisiones/{con.json()['decision_id']}").json()
    assert d["snapshot"] == ev and d["flexibilizado"] is False


def test_ficha_de_proveedor(cliente):
    assert cliente.get("/proveedores/PROV-03").status_code == 200
    assert cliente.get("/proveedores/PROV-99").status_code == 404


def test_catalogos_dan_los_ids_que_acepta_la_api(cliente, repo):
    j = cliente.get("/catalogos").json()
    assert {c["cliente_id"] for c in j["clientes"]} == {c.cliente_id for c in repo.clientes()}
    assert {"BUN", "BOG"} <= {u["ubicacion_id"] for u in j["ubicaciones"]}
    assert {t["tipo_vehiculo_id"] for t in j["tipos_vehiculo"]} == {t.tipo_vehiculo_id for t in repo.tipos_vehiculo()}
    assert [t["tipo_carga"] for t in j["tipos_carga"]] == [None, "refrigerado", "sobredimensionado", "peligrosa"]
    # Una solicitud armada solo con valores del catálogo se acepta
    r = j["rutas"][0]
    body = _solicitud(cliente_id=j["clientes"][0]["cliente_id"], origen_id=r["origen_id"], destino_id=r["destino_id"])
    assert cliente.post("/solicitudes/evaluar", json=body).status_code == 200


def test_ejemplos_guardados_cumplen_el_contrato():
    """Los JSON de backend/api/ejemplos/ los usan frontend y gafas: deben validar contra los esquemas."""
    import json
    from pathlib import Path

    from backend.api import esquemas as e
    d = Path(__file__).resolve().parents[1] / "api" / "ejemplos"
    leer = lambda n: json.loads((d / n).read_text(encoding="utf-8"))
    e.SolicitudEntrada.model_validate(leer("solicitud_entrada.json"))
    e.EscenarioEntrada.model_validate(leer("escenario_entrada.json"))
    e.DecisionEntrada.model_validate(leer("decision_entrada.json"))
    ev = e.Evaluacion.model_validate(leer("evaluacion_respuesta.json"))
    e.Evaluacion.model_validate(leer("escenario_respuesta.json"))
    e.Catalogos.model_validate(leer("catalogos_respuesta.json"))
    e.FichaProveedor.model_validate(leer("ficha_proveedor_respuesta.json"))
    e.CierreEntrada.model_validate(leer("cierre_entrada.json"))
    e.ServicioSalida.model_validate(leer("cierre_respuesta.json"))
    assert (d / "informe_decision_ejemplo.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    assert ev.candidatos and ev.cancelados
    assert all(sum(c.vehiculos.contenedores_por_vehiculo) == 3 for c in ev.candidatos)
    assert set(leer("error_422_respuesta.json")) == {"detalle", "errores"}



# --- Persistencia de la decisión (decisión del 2026-10-24: "solicitud al decidir") ----------

@pytest.fixture
def almacen():
    return AlmacenEnMemoria(ultimo=495)


@pytest.fixture
def api(repo, cfg, almacen):
    return TestClient(crear_app(repo=repo, cfg=cfg, registro=Registro(almacen)))


def _decidir(api, ev, pid=None, **kw):
    pid = pid or ev["candidatos"][0]["proveedor_id"]
    return api.post("/decisiones", json={"solicitud_id": ev["solicitud_id"], "proveedor_id": pid,
                                         "justificacion": "Prueba", **kw})


def test_numero_de_solicitud_sale_del_almacen(api):
    assert api.post("/solicitudes/evaluar", json=_solicitud()).json()["solicitud_id"] == "REQ-0496"
    assert api.post("/solicitudes/evaluar", json=_solicitud()).json()["solicitud_id"] == "REQ-0497"


def test_evaluar_no_guarda_nada_hasta_decidir(api, almacen):
    api.post("/solicitudes/evaluar", json=_solicitud())
    assert almacen.registradas == {}


def test_decidir_guarda_la_solicitud_con_el_vehiculo_elegido(api, almacen):
    ev = api.post("/solicitudes/evaluar", json=_solicitud(n_contenedores=3, peso_kg=12_000)).json()
    c = ev["candidatos"][0]
    d = _decidir(api, ev)
    assert d.status_code == 201 and d.json()["tipo_vehiculo_id"] == c["vehiculos"]["tipo_vehiculo_id"]
    (fila,) = almacen.registradas.values()
    assert (fila.numero, fila.cliente_id, fila.ruta_id) == (496, "CLI-0001", "R-BUN-BOG")
    assert fila.tipo_vehiculo_id == c["vehiculos"]["tipo_vehiculo_id"]
    assert fila.peso_total_kg == 36_000                                  # 3 contenedores × 12 000 kg
    assert (fila.fecha_entrega_limite - fila.fecha_recogida).total_seconds() == 40 * 3600


def test_una_sola_decision_por_solicitud(api, almacen):
    ev = api.post("/solicitudes/evaluar", json=_solicitud()).json()
    assert _decidir(api, ev).status_code == 201
    otra = _decidir(api, ev, pid=ev["candidatos"][1]["proveedor_id"])
    assert otra.status_code == 409 and "DEC-0001" in otra.json()["detalle"]
    assert len(almacen.registradas) == 1


def test_decidir_sobre_un_escenario_guarda_su_plazo(api, almacen):
    ev = api.post("/solicitudes/evaluar", json=_solicitud()).json()
    esc = api.post(f"/solicitudes/{ev['solicitud_id']}/escenario", json={"plazo_h": 45}).json()
    d = _decidir(api, esc, escenario_id=esc["escenario_id"])
    assert d.status_code == 201 and d.json()["snapshot"] == esc
    (fila,) = almacen.registradas.values()
    assert (fila.fecha_entrega_limite - fila.fecha_recogida).total_seconds() == 45 * 3600


def test_casi_elegible_trae_vehiculo_y_se_puede_elegir(api, almacen):
    ev = api.post("/solicitudes/evaluar", json=_solicitud(plazo_h=1)).json()
    assert ev["sin_candidatos"] and ev["casi_elegibles"]
    casi = ev["casi_elegibles"][0]
    assert casi["razon"]["codigo"] == "PLAZO_INCUMPLIBLE" and casi["vehiculos"]["cantidad"] >= 1
    d = _decidir(api, ev, pid=casi["proveedor_id"])
    assert d.status_code == 201 and d.json()["flexibilizado"] is True
    assert next(iter(almacen.registradas.values())).tipo_vehiculo_id == casi["vehiculos"]["tipo_vehiculo_id"]


class _AlmacenCaido(AlmacenEnMemoria):
    def __init__(self):
        super().__init__()
        self.caido = True

    def registrar(self, s):
        if self.caido:
            raise ErrorDatosNoDisponibles("No se pudo guardar la solicitud en la base (OperationalError)")
        super().registrar(s)


def test_base_caida_al_decidir_no_registra_nada(repo, cfg):
    almacen = _AlmacenCaido()
    api = TestClient(crear_app(repo=repo, cfg=cfg, registro=Registro(almacen)))
    ev = api.post("/solicitudes/evaluar", json=_solicitud()).json()
    r = _decidir(api, ev)
    assert r.status_code == 503 and "base" in r.json()["detalle"]
    almacen.caido = False                                                 # se puede reintentar
    assert _decidir(api, ev).status_code == 201
