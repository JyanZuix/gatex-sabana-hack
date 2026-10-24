"""Fase 1: filtro Candidatos → Cancelados con todas las razones."""
from datetime import date

import pytest

from backend.calculos.costos import opciones_vehiculo, tipos_validos
from backend.dominio import Capacidad, Proveedor, Ruta, Solicitud, Tarifa, TipoVehiculo
from backend.filtro import REGLAS, ContextoProveedor, Razon, RutaNoEncontrada, filtrar
from backend.filtro.filtro import evaluar_contextos

FECHA = date(2026, 10, 28)
RUTA = Ruta(ruta_id="R-BUN-BOG", origen_id="BUN", destino_id="BOG", distancia_km=515, corredor="Buenaventura–Bogotá")
PLAT = TipoVehiculo(tipo_vehiculo_id="PLAT", nombre="Tractocamión 40'", cap_teu=2, cap_kg=34_000)
CAMA = TipoVehiculo(tipo_vehiculo_id="CAMA", nombre="Cama baja", cap_teu=2, cap_kg=45_000, carga_especial="sobredimensionado")


def _ctx(cfg, *, proveedor=None, solicitud=None, tipos=(PLAT,), unidades=None, tarifas=None,
         cobertura=True, capacidad=5):
    solicitud = solicitud or Solicitud(cliente_id="C", origen_id="BUN", destino_id="BOG", fecha_servicio=FECHA,
                                       plazo_h=40, n_contenedores=4, peso_kg=10_000, presupuesto_cop=20_000_000)
    proveedor = proveedor or Proveedor(proveedor_id="P1", nombre="Prov 1", poliza_vigente_hasta=date(2027, 1, 1))
    unidades = {"PLAT": 3} if unidades is None else unidades
    if tarifas is None:
        tarifas = [Tarifa(tarifa_id="T1", proveedor_id=proveedor.proveedor_id, ruta_id=RUTA.ruta_id,
                          tipo_vehiculo_id="PLAT", precio_viaje=4_000_000, tiempo_prometido_h=26,
                          vigente_desde=date(2025, 1, 1))]
    validos = tuple(tipos_validos(solicitud, tipos))
    return ContextoProveedor(
        solicitud=solicitud, proveedor=proveedor, ruta=RUTA, nombres_origen_destino=("Buenaventura", "Bogotá"),
        tipos_validos=validos, unidades=unidades, opciones=tuple(opciones_vehiculo(solicitud, validos, tarifas, unidades)),
        tiene_cobertura=cobertura,
        capacidad=None if capacidad is None else Capacidad(proveedor_id=proveedor.proveedor_id, fecha=FECHA,
                                                          servicios_disponibles=capacidad),
        cfg=cfg,
    )


def _codigos(resultado):
    return {c.proveedor.proveedor_id: [r.codigo for r in c.razones] for c in resultado.cancelados}


def _razones(ctx):
    return evaluar_contextos([ctx]).cancelados[0].razones


def test_proveedor_que_cumple_queda_en_candidatos(cfg):
    r = evaluar_contextos([_ctx(cfg)])
    assert len(r.candidatos) == 1 and not r.cancelados
    c = r.candidatos[0]
    assert (c.opcion.viajes, c.opcion.reparto, c.opcion.costo) == (2, (2, 2), 8_000_000)


def test_regla_nueva_se_registra_sin_tocar_nada_mas(cfg):
    def regla_de_prueba(ctx):
        return [Razon("REGLA_PRUEBA", "Regla de prueba", requerido=1, disponible=0)]
    r = evaluar_contextos([_ctx(cfg)], reglas=REGLAS + [regla_de_prueba])
    assert _codigos(r) == {"P1": ["REGLA_PRUEBA"]}


def test_sin_cobertura(cfg):
    (razon,) = _razones(_ctx(cfg, cobertura=False))
    assert razon.codigo == "SIN_COBERTURA" and "Buenaventura → Bogotá" in razon.mensaje


def test_sin_tarifa(cfg):
    (razon,) = _razones(_ctx(cfg, tarifas=[]))
    assert razon.codigo == "SIN_TARIFA"


def test_sin_tarifa_por_vigencia_vencida(cfg, repo):
    # PROV-06 tenía tarifa BOG→BUN hasta 2026-06-30
    s = Solicitud(cliente_id="CLI-0001", origen_id="BOG", destino_id="BUN", fecha_servicio=FECHA,
                  plazo_h=40, n_contenedores=2, peso_kg=10_000, presupuesto_cop=10_000_000)
    assert "SIN_TARIFA" in _codigos(filtrar(s, repo, cfg))["PROV-06"]


def test_sin_tarifa_para_los_vehiculos_que_tiene(cfg):
    sencillo = TipoVehiculo(tipo_vehiculo_id="SENC", nombre="Sencillo", cap_teu=1, cap_kg=17_000)
    # Tiene sencillos pero solo hay tarifa de plataforma, que no tiene
    ctx = _ctx(cfg, tipos=(PLAT, sencillo), unidades={"SENC": 4})
    assert [r.codigo for r in _razones(ctx)] == ["SIN_TARIFA"]


def test_vehiculo_no_disponible(cfg):
    s = Solicitud(cliente_id="C", origen_id="BUN", destino_id="BOG", fecha_servicio=FECHA, plazo_h=40,
                  n_contenedores=1, peso_kg=40_000, tipo_carga="sobredimensionado", presupuesto_cop=1)
    p = Proveedor(proveedor_id="P1", nombre="P", cargas_especiales=("sobredimensionado",))
    razones = _razones(_ctx(cfg, solicitud=s, proveedor=p, tipos=(PLAT, CAMA), tarifas=[]))
    codigos = [r.codigo for r in razones]
    assert "VEHICULO_NO_DISPONIBLE" in codigos
    r = next(r for r in razones if r.codigo == "VEHICULO_NO_DISPONIBLE")
    assert "Cama baja" in r.mensaje and "sobredimensionado" in r.mensaje


def test_carga_no_soportada(cfg):
    s = Solicitud(cliente_id="C", origen_id="BUN", destino_id="BOG", fecha_servicio=FECHA, plazo_h=40,
                  n_contenedores=2, peso_kg=10_000, tipo_carga="peligrosa", tipo_vehiculo_id="PLAT", presupuesto_cop=20_000_000)
    razones = _razones(_ctx(cfg, solicitud=s))
    assert [r.codigo for r in razones] == ["CARGA_NO_SOPORTADA"]
    assert razones[0].mensaje == "No transporta carga peligrosa"


def _con_presupuesto(presupuesto):
    return Solicitud(cliente_id="C", origen_id="BUN", destino_id="BOG", fecha_servicio=FECHA, plazo_h=40,
                     n_contenedores=4, peso_kg=10_000, presupuesto_cop=presupuesto)


@pytest.mark.parametrize("presupuesto", [8_000_000, 20_000_000])
def test_sin_margen_no_descarta_si_alcanza_el_presupuesto(cfg, presupuesto):
    # La opción cuesta 2 viajes × 4 000 000 = 8 000 000: igual o menor al presupuesto no da pérdida
    r = evaluar_contextos([_ctx(cfg, solicitud=_con_presupuesto(presupuesto))])
    assert len(r.candidatos) == 1


def test_sin_margen_descarta_a_quien_da_perdida(cfg):
    (razon,) = _razones(_ctx(cfg, solicitud=_con_presupuesto(7_999_999)))
    assert razon.codigo == "SIN_MARGEN"
    assert (razon.requerido, razon.disponible) == (7_999_999, 8_000_000)
    assert razon.mensaje == "Costo $8.000.000 supera el presupuesto de $7.999.999"


def test_sin_margen_usa_la_opcion_mas_barata_que_cumple(cfg):
    # Una opción más barata pero lenta (60 h > plazo 40 h) no cuenta: el candidato pagaría la rápida
    tarifas = [Tarifa(tarifa_id=t, proveedor_id="P1", ruta_id=RUTA.ruta_id, tipo_vehiculo_id=v, precio_viaje=p,
                      tiempo_prometido_h=h, vigente_desde=date(2025, 1, 1))
               for t, v, p, h in [("T1", "PLAT", 4_000_000, 26), ("T2", "CAMA", 1_000_000, 60)]]
    ctx = _ctx(cfg, solicitud=_con_presupuesto(6_000_000), tipos=(PLAT, CAMA), unidades={"PLAT": 3, "CAMA": 3},
               tarifas=tarifas)
    assert [r.codigo for r in _razones(ctx)] == ["SIN_MARGEN"]


def test_si_todos_dan_perdida_son_casi_elegibles_con_presupuesto_a_flexibilizar(cfg):
    p2 = Proveedor(proveedor_id="P2", nombre="P2", poliza_vigente_hasta=date(2027, 1, 1))
    s = _con_presupuesto(5_000_000)
    r = evaluar_contextos([_ctx(cfg, solicitud=s), _ctx(cfg, solicitud=s, proveedor=p2)])
    assert r.sin_candidatos
    assert {c.proveedor.proveedor_id: c.flexibilizar for c in r.casi_elegibles} == {
        "P1": "Aumentar el presupuesto a $8.000.000", "P2": "Aumentar el presupuesto a $8.000.000"}


def test_presupuesto_debe_ser_positivo():
    with pytest.raises(ValueError):
        _con_presupuesto(0)


def test_vehiculos_insuficientes(cfg):
    (razon,) = _razones(_ctx(cfg, unidades={"PLAT": 1}))
    assert razon.codigo == "VEHICULOS_INSUFICIENTES"
    assert (razon.requerido, razon.disponible) == (2, 1)


def test_vehiculos_insuficientes_igual_con_tandas_desactivadas(cfg):
    assert cfg.vehiculos.permitir_tandas is False
    assert _razones(_ctx(cfg, unidades={"PLAT": 1}))[0].codigo == "VEHICULOS_INSUFICIENTES"


def test_sin_capacidad(cfg):
    (razon,) = _razones(_ctx(cfg, capacidad=0))
    assert razon.codigo == "SIN_CAPACIDAD"
    assert razon.mensaje == "Capacidad agotada para el 28-oct"
    assert (razon.requerido, razon.disponible) == (1, 0)


def test_sin_dato_de_capacidad_no_descarta_pero_avisa(cfg):
    r = evaluar_contextos([_ctx(cfg, capacidad=None)])
    assert r.candidatos and r.candidatos[0].avisos


def test_plazo_incumplible_52_vs_40(cfg):
    tarifa = Tarifa(tarifa_id="T1", proveedor_id="P1", ruta_id=RUTA.ruta_id, tipo_vehiculo_id="PLAT",
                    precio_viaje=4_000_000, tiempo_prometido_h=52, vigente_desde=date(2025, 1, 1))
    (razon,) = _razones(_ctx(cfg, tarifas=[tarifa]))
    assert razon.codigo == "PLAZO_INCUMPLIBLE"
    assert (razon.requerido, razon.disponible) == (40, 52)
    assert razon.mensaje == "Tránsito pactado 52 h; plazo disponible 40 h"


def test_proveedor_inactivo_y_poliza_vencida(cfg):
    p = Proveedor(proveedor_id="P1", nombre="P", estado="suspendido", poliza_vigente_hasta=date(2026, 10, 15))
    razones = _razones(_ctx(cfg, proveedor=p))
    assert [r.codigo for r in razones] == ["PROVEEDOR_INACTIVO", "PROVEEDOR_INACTIVO"]
    assert razones[1].mensaje == "Póliza vencida desde el 15-oct"


def test_se_evaluan_todas_las_reglas(cfg):
    p = Proveedor(proveedor_id="P1", nombre="P", estado="inactivo")
    tarifa = Tarifa(tarifa_id="T1", proveedor_id="P1", ruta_id=RUTA.ruta_id, tipo_vehiculo_id="PLAT",
                    precio_viaje=4_000_000, tiempo_prometido_h=52, vigente_desde=date(2025, 1, 1))
    razones = _razones(_ctx(cfg, proveedor=p, tarifas=[tarifa], unidades={"PLAT": 1}, cobertura=False))
    assert {r.codigo for r in razones} == {"SIN_COBERTURA", "VEHICULOS_INSUFICIENTES", "PLAZO_INCUMPLIBLE",
                                           "PROVEEDOR_INACTIVO"}


def test_orden_de_entrada_no_altera_resultado(cfg):
    ctxs = [_ctx(cfg, proveedor=Proveedor(proveedor_id=f"P{i}", nombre=f"P{i}"), unidades={"PLAT": i})
            for i in range(1, 5)]
    a, b = evaluar_contextos(ctxs), evaluar_contextos(list(reversed(ctxs)))
    assert a == b
    assert [c.proveedor.proveedor_id for c in a.candidatos] == ["P2", "P3", "P4"]


def test_elige_vehiculo_que_cumple_plazo_aunque_no_sea_el_mas_barato(cfg):
    sencillo = TipoVehiculo(tipo_vehiculo_id="SENC", nombre="Sencillo", cap_teu=1, cap_kg=17_000)
    tarifas = [
        Tarifa(tarifa_id="T1", proveedor_id="P1", ruta_id=RUTA.ruta_id, tipo_vehiculo_id="PLAT",
               precio_viaje=4_000_000, tiempo_prometido_h=30, vigente_desde=date(2025, 1, 1)),
        Tarifa(tarifa_id="T2", proveedor_id="P1", ruta_id=RUTA.ruta_id, tipo_vehiculo_id="SENC",
               precio_viaje=1_000_000, tiempo_prometido_h=45, vigente_desde=date(2025, 1, 1)),
    ]
    r = evaluar_contextos([_ctx(cfg, tipos=(PLAT, sencillo), unidades={"PLAT": 3, "SENC": 5}, tarifas=tarifas)])
    assert r.candidatos[0].opcion.tipo_vehiculo_id == "PLAT"


def test_cero_candidatos_muestra_casi_elegibles(cfg):
    p1 = Proveedor(proveedor_id="P1", nombre="P1")
    p2 = Proveedor(proveedor_id="P2", nombre="P2")
    p3 = Proveedor(proveedor_id="P3", nombre="P3", estado="inactivo")
    lento = lambda pid: [Tarifa(tarifa_id=f"T{pid}", proveedor_id=pid, ruta_id=RUTA.ruta_id, tipo_vehiculo_id="PLAT",
                                precio_viaje=4_000_000, tiempo_prometido_h=52, vigente_desde=date(2025, 1, 1))]
    r = evaluar_contextos([
        _ctx(cfg, proveedor=p1, tarifas=lento("P1")),               # solo plazo
        _ctx(cfg, proveedor=p2, unidades={"PLAT": 1}),              # solo vehículos
        _ctx(cfg, proveedor=p3, cobertura=False),                   # dos razones: no es casi elegible
    ])
    assert r.sin_candidatos
    casi = {c.proveedor.proveedor_id: c for c in r.casi_elegibles}
    assert set(casi) == {"P1", "P2"}
    assert casi["P1"].flexibilizar == "Ampliar el plazo a 52 h"
    assert "tandas" in casi["P2"].flexibilizar


def test_con_candidatos_no_hay_casi_elegibles(cfg):
    r = evaluar_contextos([_ctx(cfg), _ctx(cfg, proveedor=Proveedor(proveedor_id="P2", nombre="P2"), unidades={"PLAT": 1})])
    assert not r.sin_candidatos and r.casi_elegibles == ()


def test_ruta_inexistente(cfg, repo):
    s = Solicitud(cliente_id="C", origen_id="BUN", destino_id="MED", fecha_servicio=FECHA, plazo_h=40,
                  n_contenedores=1, peso_kg=10_000, presupuesto_cop=1)
    with pytest.raises(RutaNoEncontrada):
        filtrar(s, repo, cfg)


def test_filtro_con_datos_sinteticos(cfg, repo, solicitud_base):
    r = filtrar(solicitud_base, repo, cfg)
    codigos = _codigos(r)
    assert codigos["PROV-07"] == ["VEHICULOS_INSUFICIENTES", "PLAZO_INCUMPLIBLE"]
    assert codigos["PROV-05"] == ["SIN_CAPACIDAD"]
    assert codigos["PROV-08"] == ["PROVEEDOR_INACTIVO"]
    assert "SIN_COBERTURA" in codigos["PROV-04"]
    assert {c.proveedor.proveedor_id for c in r.candidatos} == {"PROV-01", "PROV-02", "PROV-03", "PROV-06", "PROV-09"}
    assert len(r.candidatos) + len(r.cancelados) == len(repo.proveedores())
