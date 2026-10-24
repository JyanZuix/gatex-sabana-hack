"""Notas de la demo: siempre una opción viable con condición e historial de proveedores mes a mes."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.api.app import crear_app
from backend.api.registro import Registro
from backend.dominio import Proveedor
from backend.filtro.filtro import evaluar_contextos

from .test_fase1_filtro import _con_presupuesto, _ctx


# --- Siempre al menos una opción viable con condición -----------------------

def test_sin_nadie_con_una_sola_falla_igual_hay_opcion(cfg):
    # Los dos fallan dos condiciones: antes no había casi elegibles; ahora se muestran los dos
    p2 = Proveedor(proveedor_id="P2", nombre="P2", poliza_vigente_hasta=date(2027, 1, 1))
    s = _con_presupuesto(5_000_000)  # SIN_MARGEN para ambos
    r = evaluar_contextos([_ctx(cfg, solicitud=s, cobertura=False),
                           _ctx(cfg, solicitud=s, proveedor=p2, cobertura=False)])
    assert r.sin_candidatos and len(r.casi_elegibles) == 2
    for c in r.casi_elegibles:
        assert [x.codigo for x, _ in c.condiciones] == ["SIN_COBERTURA", "SIN_MARGEN"]
        assert c.razon.codigo == "SIN_COBERTURA" and c.flexibilizar == c.condiciones[0][1]


def test_se_muestran_solo_los_que_fallan_menos(cfg):
    p2 = Proveedor(proveedor_id="P2", nombre="P2", poliza_vigente_hasta=date(2027, 1, 1))
    s = _con_presupuesto(5_000_000)
    r = evaluar_contextos([_ctx(cfg, solicitud=s), _ctx(cfg, solicitud=s, proveedor=p2, cobertura=False)])
    assert [c.proveedor.proveedor_id for c in r.casi_elegibles] == ["P1"]  # P2 falla dos


@pytest.fixture
def cliente(repo, cfg):
    return TestClient(crear_app(repo=repo, cfg=cfg, registro=Registro(), hoy=lambda: date(2026, 10, 24)))


def _solicitud(**cambios):
    datos = dict(cliente_id="CLI-0001", origen_id="BUN", destino_id="BOG", fecha_servicio="2026-10-28",
                 plazo_h=40, n_contenedores=4, peso_kg=10_000, presupuesto_cop=15_000_000)
    datos.update(cambios)
    return datos


def test_api_siempre_marca_una_opcion_viable(cliente):
    j = cliente.post("/solicitudes/evaluar", json=_solicitud(presupuesto_cop=1_000)).json()
    assert j["sin_candidatos"] and j["casi_elegibles"]
    assert [c["puesto"] for c in j["casi_elegibles"]] == list(range(1, len(j["casi_elegibles"]) + 1))
    assert [c["recomendada"] for c in j["casi_elegibles"]] == [True] + [False] * (len(j["casi_elegibles"]) - 1)
    costos = [c["vehiculos"]["cantidad"] for c in j["casi_elegibles"] if c["vehiculos"]]
    assert costos  # traen el vehículo que tendrían
    for c in j["casi_elegibles"]:
        assert c["condiciones"][0]["razon"] == c["razon"] and c["condiciones"][0]["flexibilizar"] == c["flexibilizar"]
    # Se puede elegir: queda como decisión flexibilizada
    d = cliente.post("/decisiones", json={"solicitud_id": j["solicitud_id"], "justificacion": "Se amplía el presupuesto",
                                          "proveedor_id": j["casi_elegibles"][0]["proveedor_id"]})
    assert d.status_code == 201 and d.json()["flexibilizado"] is True


# --- Historial mes a mes ------------------------------------------------------

def test_historial_de_todos_los_proveedores(cliente, repo):
    j = cliente.get("/historial/proveedores").json()
    assert {p["proveedor_id"] for p in j["proveedores"]} == {p.proveedor_id for p in repo.proveedores()}
    assert j["meses"] == sorted(j["meses"]) and j["generado"] == "2026-10-24"
    con_datos = [p for p in j["proveedores"] if p["servicios"]]
    assert [p["desempeno"]["valor"] for p in con_datos] == sorted((p["desempeno"]["valor"] for p in con_datos),
                                                                  reverse=True)
    for p in con_datos:
        assert sum(t["servicios"] for t in p["tendencia"]) == p["servicios"]
        for t in p["tendencia"]:
            assert 0 <= t["a_tiempo_pct"] <= 100 and t["nivel"] in {"alto", "medio", "bajo"}
            assert t["mes"] in j["meses"]


def test_nivel_mensual_usa_los_umbrales(cfg):
    from backend.api.textos import nivel_puntualidad
    assert [nivel_puntualidad(x, cfg) for x in (85, 84.9, 70, 69.9)] == ["alto", "medio", "medio", "bajo"]


def test_informe_html_del_historial(cliente, cfg):
    r = cliente.get("/historial/proveedores/informe")
    assert r.status_code == 200 and r.headers["content-disposition"].startswith("attachment")
    assert cliente.get("/historial/proveedores/informe?descargar=false").headers["content-disposition"].startswith("inline")
    html = r.text
    j = cliente.get("/historial/proveedores").json()
    assert "Historial de proveedores, mes a mes" in html
    for p in j["proveedores"]:
        assert p["nombre"].split(" (")[0] in html
    # Solo los últimos `meses_informe` meses en la tabla mensual
    assert html.count("<th class='c'>") == min(len(j["meses"]), cfg.ficha.meses_informe)
