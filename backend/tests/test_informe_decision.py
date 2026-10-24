"""Informe de la decisión: 8 secciones en orden, con los datos reales de una solicitud de prueba
(datos sintéticos), en HTML y en JSON; y snapshot completo al decidir."""
from html import escape

import pytest
from fastapi.testclient import TestClient

from backend.api.app import crear_app
from backend.api.informe import NOTA, SELLO, SIN_INCIDENTES, TITULOS
from backend.api.registro import Registro

MOTIVO = "Llega a tiempo con más probabilidad y el cliente lo conoce"


@pytest.fixture
def api(repo, cfg):
    return TestClient(crear_app(repo=repo, cfg=cfg, registro=Registro()))


def _evaluar(api, **cambios):
    datos = dict(cliente_id="CLI-0001", origen_id="BUN", destino_id="BOG", fecha_servicio="2026-10-28",
                 plazo_h=40, n_contenedores=4, peso_kg=10_000, presupuesto_cop=15_000_000, penal_hora_cop=20_000)
    datos.update(cambios)
    r = api.post("/solicitudes/evaluar", json=datos)
    assert r.status_code == 200
    return r.json()


def _decidir(api, ev, pid):
    r = api.post("/decisiones", json={"solicitud_id": ev["solicitud_id"], "proveedor_id": pid, "justificacion": MOTIVO})
    assert r.status_code == 201
    return r.json()


def _cop(x):
    return f"{'−' if x < 0 else ''}${abs(x):,.0f}".replace(",", ".")


def test_snapshot_completo_de_lo_que_vio_el_funcionario(api):
    ev = _evaluar(api)
    d = _decidir(api, ev, ev["candidatos"][-1]["proveedor_id"])
    s = d["snapshot"]
    assert s == ev                                        # idéntico a lo que se mostró, sin recalcular
    assert len(s["candidatos"]) == len(ev["candidatos"]) and all("tiempo_h" in c and "confianza" in c
                                                                 for c in s["candidatos"])
    assert s["cancelados"] and all(c["razones"] for c in s["cancelados"])
    assert s["parametros_escenario"] == {"plazo_h": 40.0, "penal_hora_cop": 20_000.0, "semilla": 42,
                                         "n_simulaciones": 2000}
    assert d["justificacion"] == MOTIVO and d["fecha_hora"]


def test_informe_tiene_las_8_secciones_en_orden_con_datos_reales(api):
    ev = _evaluar(api)
    elegido = ev["candidatos"][-1]
    d = _decidir(api, ev, elegido["proveedor_id"])
    html = api.get(f"/decisiones/{d['decision_id']}/informe?descargar=false").text

    posiciones = [html.index(escape(t)) for t in TITULOS]
    assert posiciones == sorted(posiciones), "las secciones deben ir en el orden pedido"
    for n in range(1, 9):
        assert f"id='seccion-{n}'" in html or f'id="seccion-{n}"' in html

    # 1. Encabezado
    assert ev["solicitud_id"] in html and d["decision_id"] in html and "hora Colombia" in html
    # 2. La solicitud
    assert f"{ev['ruta']['origen']} → {ev['ruta']['destino']}" in html and "km" in html
    assert "4 contenedor(es) de 20&#x27; × 10.000 kg" in html and "40,0 h" in html
    # 3. Decisión final
    assert escape(elegido["nombre"]) in html and escape(MOTIVO) in html
    # 4. Resultados de la opción elegida, con desglose de D y C
    for valor in (_cop(elegido["costo_cop"]), _cop(15_000_000), _cop(elegido["profit"]["esperado_cop"]),
                  _cop(elegido["profit"]["p10_cop"])):
        assert valor in html
    assert "Puntualidad (pesa 75 %)" in html and "Consistencia de tiempos" in html and "Evidencia histórica" in html
    assert escape(SIN_INCIDENTES) in html and escape(elegido["explicacion"]) in html
    # 5. Comparación: todos los candidatos y la fila elegida resaltada
    assert all(escape(c["nombre"]) in html for c in ev["candidatos"])
    assert html.count("class='fila-elegida'") == 1 and SELLO in html
    # 6. Descartados con TODAS sus razones (código, mensaje, requerido frente a disponible)
    for c in ev["cancelados"]:
        for z in c["razones"]:
            assert escape(z["codigo"]) in html and escape(z["mensaje"]) in html
    assert html.count("requerido:") == sum(len(c["razones"]) for c in ev["cancelados"])
    # 7. Parámetros: N, semilla, escenario y penalidad
    assert "2.000" in html and ">42<" in html and "Original (sin cambios de supuestos)" in html
    assert _cop(20_000) in html
    # 8. Nota al pie
    assert escape(NOTA) in html
    assert "Descargar PDF" in html and "asignó" not in html.lower()


def test_informe_json_trae_el_mismo_contenido_para_las_gafas(api):
    ev = _evaluar(api)
    elegido = ev["candidatos"][0]
    d = _decidir(api, ev, elegido["proveedor_id"])
    r = api.get(f"/decisiones/{d['decision_id']}/informe?formato=json")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    j = r.json()
    assert [s["titulo"] for s in j["secciones"]] == list(TITULOS) and [s["numero"] for s in j["secciones"]] == list(range(1, 9))
    tabla = next(b for b in j["secciones"][4]["bloques"] if b["tipo"] == "tabla")
    assert len(tabla["filas"]) == len(ev["candidatos"]) and tabla["filas"][tabla["resaltada"]][0] == elegido["nombre"]
    razones = [z for b in j["secciones"][5]["bloques"] if b["tipo"] == "razones" for z in b["razones"]]
    assert razones and len(razones) == sum(len(c["razones"]) for c in ev["cancelados"])
    cita = next(b for b in j["secciones"][2]["bloques"] if b["tipo"] == "cita")
    assert cita["texto"] == MOTIVO
    assert j["secciones"][7]["bloques"][0]["texto"] == NOTA
    # Mismo contenido que el HTML: cada valor del JSON aparece en el documento imprimible.
    html = api.get(f"/decisiones/{d['decision_id']}/informe").text
    for s in j["secciones"]:
        for b in s["bloques"]:
            for p in b["pares"]:
                assert escape(p["valor"]) in html, p


def test_informe_de_un_casi_elegible_lo_marca_como_flexibilizado(api):
    ev = _evaluar(api, plazo_h=1)
    assert ev["sin_candidatos"] and ev["casi_elegibles"]
    d = _decidir(api, ev, ev["casi_elegibles"][0]["proveedor_id"])
    html = api.get(f"/decisiones/{d['decision_id']}/informe").text
    assert "decidió flexibilizar" in html and "No hay resultados simulados" in html
    assert "No hubo candidatos" in html and "Casi elegibles (fallan una sola regla)" in html
