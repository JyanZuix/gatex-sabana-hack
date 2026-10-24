"""Genera los datos SINTÉTICOS de prueba (no son datos de COSCO).

Uso, desde la raíz del repositorio:
    .venv/bin/python -m backend.datos_sinteticos.generar

Es determinista (semilla fija): volver a ejecutarlo produce los mismos archivos.
Cada archivo lleva `"sintetico": true` para que nunca se confundan con datos reales.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

CARPETA = Path(__file__).resolve().parent
SEMILLA = 2026
FECHA_REFERENCIA = date(2026, 10, 23)
NOTA = "Datos sintéticos generados para pruebas y demo. No representan proveedores ni clientes reales."

UBICACIONES = [
    {"ubicacion_id": "BUN", "nombre": "Puerto de Buenaventura", "tipo": "puerto", "lat": 3.8801, "lon": -77.0312},
    {"ubicacion_id": "BOG", "nombre": "Bogotá", "tipo": "ciudad", "lat": 4.7110, "lon": -74.0721},
    {"ubicacion_id": "CTG", "nombre": "Puerto de Cartagena", "tipo": "puerto", "lat": 10.3910, "lon": -75.4794},
    {"ubicacion_id": "MED", "nombre": "Medellín", "tipo": "ciudad", "lat": 6.2442, "lon": -75.5812},
]

# ruta_id: (origen, destino, km, corredor, horas base)
RUTAS = {
    "R-BUN-BOG": ("BUN", "BOG", 515, "Buenaventura–Bogotá", 26.0),
    "R-BOG-BUN": ("BOG", "BUN", 515, "Buenaventura–Bogotá", 25.0),
    "R-CTG-MED": ("CTG", "MED", 640, "Cartagena–Medellín", 30.0),
    "R-MED-CTG": ("MED", "CTG", 640, "Cartagena–Medellín", 29.0),
}

TIPOS = [
    {"tipo_vehiculo_id": "TV-PLAT40", "nombre": "Tractocamión plataforma 40'", "cap_teu": 2, "cap_toneladas": 34, "cap_m3": 67, "carga_especial": None},
    {"tipo_vehiculo_id": "TV-SENC20", "nombre": "Camión sencillo 20'", "cap_teu": 1, "cap_toneladas": 17, "cap_m3": 33, "carga_especial": None},
    {"tipo_vehiculo_id": "TV-REFRI40", "nombre": "Tractocamión refrigerado 40'", "cap_teu": 2, "cap_toneladas": 30, "cap_m3": 60, "carga_especial": "refrigerado"},
    {"tipo_vehiculo_id": "TV-CAMABAJA", "nombre": "Cama baja", "cap_teu": 0, "cap_toneladas": 45, "cap_m3": None, "carga_especial": "sobredimensionado"},
]
PRECIO_BASE = {"TV-PLAT40": 4_800_000, "TV-SENC20": 3_200_000, "TV-REFRI40": 6_200_000, "TV-CAMABAJA": 8_500_000}
FACTOR_RUTA = {"R-BUN-BOG": 1.0, "R-BOG-BUN": 0.92, "R-CTG-MED": 1.15, "R-MED-CTG": 1.08}

CLIENTES = [
    {"cliente_id": "CLI-0001", "nombre": "Cliente sintético Alimentos"},
    {"cliente_id": "CLI-0002", "nombre": "Cliente sintético Químicos"},
    {"cliente_id": "CLI-0003", "nombre": "Cliente sintético Retail"},
    {"cliente_id": "CLI-0004", "nombre": "Cliente sintético Maquinaria"},
]

# Perfil de cada proveedor sintético.
#   rutas, flota {tipo: unidades}, factor de precio, factor de tiempo prometido,
#   n servicios, media y desviación de Δ, prob. de incidente, cliente preferido.
PROVEEDORES = {
    "PROV-01": dict(nombre="Transportes Andinos (sintético)", rutas=["R-BUN-BOG", "R-BOG-BUN", "R-CTG-MED"],
                    flota={"TV-PLAT40": 4, "TV-SENC20": 3}, precio=1.05, prom=1.00,
                    n=70, mu=0.02, sd=0.12, inc=0.05, cliente="CLI-0001"),
    "PROV-02": dict(nombre="Logística del Pacífico (sintético)", rutas=["R-BUN-BOG", "R-BOG-BUN"],
                    flota={"TV-PLAT40": 6, "TV-SENC20": 2}, precio=0.92, prom=1.00,
                    n=60, mu=0.10, sd=0.20, inc=0.08, cliente="CLI-0003"),
    "PROV-03": dict(nombre="Carga Segura (sintético)", rutas=["R-BUN-BOG", "R-CTG-MED", "R-MED-CTG"],
                    flota={"TV-PLAT40": 3, "TV-REFRI40": 3}, precio=1.12, prom=1.05,
                    n=55, mu=-0.02, sd=0.07, inc=0.02, cliente="CLI-0001", cargas=["refrigerado", "peligrosa"]),
    "PROV-04": dict(nombre="TransCaribe (sintético)", rutas=["R-CTG-MED", "R-MED-CTG"],
                    flota={"TV-PLAT40": 3, "TV-CAMABAJA": 2}, precio=1.00, prom=1.00,
                    n=45, mu=0.04, sd=0.14, inc=0.06, cliente="CLI-0004", cargas=["sobredimensionado"]),
    "PROV-05": dict(nombre="Rápido Express (sintético)", rutas=["R-BUN-BOG", "R-BOG-BUN"],
                    flota={"TV-PLAT40": 2, "TV-SENC20": 4}, precio=1.08, prom=0.85,
                    n=40, mu=0.12, sd=0.25, inc=0.07, cliente="CLI-0002"),
    "PROV-06": dict(nombre="Montaña Cargo (sintético)", rutas=["R-BUN-BOG", "R-CTG-MED", "R-MED-CTG"],
                    flota={"TV-PLAT40": 5}, precio=0.88, prom=1.00,
                    n=50, mu=0.06, sd=0.18, inc=0.18, cliente="CLI-0003"),
    "PROV-07": dict(nombre="Carga Express (sintético)", rutas=["R-BUN-BOG"],
                    flota={"TV-PLAT40": 1}, precio=0.95, prom=2.00,
                    n=30, mu=0.03, sd=0.10, inc=0.04, cliente="CLI-0002"),
    "PROV-08": dict(nombre="Vías del Sur (sintético)", rutas=["R-BUN-BOG", "R-BOG-BUN"],
                    flota={"TV-PLAT40": 3}, precio=0.97, prom=1.00,
                    n=35, mu=0.05, sd=0.15, inc=0.05, cliente="CLI-0001",
                    poliza=date(2026, 10, 15)),
    "PROV-09": dict(nombre="Nuevo Horizonte (sintético)", rutas=["R-BUN-BOG", "R-BOG-BUN"],
                    flota={"TV-PLAT40": 2}, precio=0.96, prom=1.00,
                    n=3, mu=-0.03, sd=0.03, inc=0.0, cliente="CLI-0001", reciente=True),
    "PROV-10": dict(nombre="Transportes Llanos (sintético)", rutas=["R-BUN-BOG"],
                    flota={"TV-PLAT40": 3}, precio=0.94, prom=1.00,
                    n=25, mu=0.08, sd=0.16, inc=0.06, cliente="CLI-0003", estado="suspendido"),
}

TIPOS_INCIDENTE = [("Novedad documental", 0.3), ("Avería mecánica", 0.6), ("Daño mayor a la carga", 1.0)]


def _guardar(nombre: str, datos: list[dict]) -> None:
    contenido = {"sintetico": True, "nota": NOTA, "generado_para": FECHA_REFERENCIA.isoformat(), "datos": datos}
    with (CARPETA / f"{nombre}.json").open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=1, default=str)


def generar() -> None:
    rng = np.random.default_rng(SEMILLA)

    rutas = [{"ruta_id": r, "origen_id": o, "destino_id": d, "distancia_km": km, "corredor": c}
             for r, (o, d, km, c, _) in RUTAS.items()]
    proveedores, tarifas, flota, cobertura, capacidad = [], [], [], [], []
    servicios, incidentes = [], []
    tipos_por_id = {t["tipo_vehiculo_id"]: t for t in TIPOS}

    for pid, p in PROVEEDORES.items():
        proveedores.append({
            "proveedor_id": pid, "nombre": p["nombre"], "estado": p.get("estado", "activo"),
            "poliza_vigente_hasta": p.get("poliza", date(2027, 6, 30)),
            "cargas_especiales": p.get("cargas", []),
        })
        for tipo, unidades in p["flota"].items():
            flota.append({"proveedor_id": pid, "tipo_vehiculo_id": tipo,
                          "unidades_disponibles": unidades, "vigente_desde": date(2026, 10, 1)})
        for ruta in p["rutas"]:
            cobertura.append({"proveedor_id": pid, "ruta_id": ruta})
            horas = RUTAS[ruta][4] * p["prom"]
            for tipo in p["flota"]:
                precio = PRECIO_BASE[tipo] * FACTOR_RUTA[ruta] * p["precio"]
                tarifas.append({
                    "tarifa_id": f"TAR-{pid}-{ruta}-{tipo}", "proveedor_id": pid, "ruta_id": ruta,
                    "tipo_vehiculo_id": tipo, "precio_viaje": int(round(precio, -4)),
                    "tiempo_prometido_h": round(horas, 1), "vigente_desde": date(2025, 1, 1), "vigente_hasta": None,
                })
        for dia in range(15):
            fecha = FECHA_REFERENCIA + timedelta(days=dia)
            disponibles = int(rng.integers(1, 6))
            if pid == "PROV-05" and fecha == date(2026, 10, 28):
                disponibles = 0  # caso de demo: capacidad agotada
            capacidad.append({"proveedor_id": pid, "fecha": fecha, "servicios_disponibles": disponibles})

        # Historial de servicios
        dias_historia = 60 if p.get("reciente") else 3 * 365
        for k in range(p["n"]):
            ruta = p["rutas"][int(rng.integers(len(p["rutas"])))]
            tipo = list(p["flota"])[int(rng.integers(len(p["flota"])))]
            entrega = FECHA_REFERENCIA - timedelta(days=int(rng.integers(3, dias_historia)))
            prometido = round(RUTAS[ruta][4] * p["prom"], 1)
            delta = max(float(rng.normal(p["mu"], p["sd"])), -0.3)
            real = round(prometido * (1 + delta), 1)
            plazo = round(prometido * 1.10, 1)
            cliente = p["cliente"] if rng.random() < 0.5 else CLIENTES[int(rng.integers(len(CLIENTES)))]["cliente_id"]
            sid = f"SRV-{pid}-{k:03d}"
            servicios.append({
                "servicio_id": sid, "proveedor_id": pid, "cliente_id": cliente, "ruta_id": ruta,
                "tipo_vehiculo_id": tipo, "fecha_entrega": entrega, "tiempo_prometido_h": prometido,
                "tiempo_real_h": real, "plazo_acordado_h": plazo, "a_tiempo": real <= plazo,
            })
            if rng.random() < p["inc"]:
                nombre, sev = TIPOS_INCIDENTE[int(rng.choice(3, p=[0.6, 0.3, 0.1]))]
                incidentes.append({"servicio_id": sid, "tipo": nombre, "severidad": sev})

    # Tarifa vencida: sirve para probar SIN_TARIFA con vigencia
    tarifas.append({
        "tarifa_id": "TAR-PROV-06-R-BOG-BUN-TV-PLAT40-2025", "proveedor_id": "PROV-06", "ruta_id": "R-BOG-BUN",
        "tipo_vehiculo_id": "TV-PLAT40", "precio_viaje": 4_100_000, "tiempo_prometido_h": 25.0,
        "vigente_desde": date(2025, 1, 1), "vigente_hasta": date(2026, 6, 30),
    })
    cobertura.append({"proveedor_id": "PROV-06", "ruta_id": "R-BOG-BUN"})

    condiciones = [
        {"corredor": "Buenaventura–Bogotá", "fecha_hora": datetime(2026, 10, 20, 8, 0), "p_evento": 0.15,
         "demora_min_h": 4, "demora_max_h": 12, "descripcion": "Riesgo de bloqueo en el Alto de La Línea"},
        {"corredor": "Cartagena–Medellín", "fecha_hora": datetime(2026, 10, 20, 8, 0), "p_evento": 0.05,
         "demora_min_h": 2, "demora_max_h": 6, "descripcion": "Obras en la vía con paso restringido"},
    ]

    assert all(t in tipos_por_id for p in PROVEEDORES.values() for t in p["flota"])
    _guardar("ubicaciones", UBICACIONES)
    _guardar("rutas", rutas)
    _guardar("tipos_vehiculo", TIPOS)
    _guardar("clientes", CLIENTES)
    _guardar("proveedores", proveedores)
    _guardar("tarifas", tarifas)
    _guardar("vehiculos_proveedor", flota)
    _guardar("cobertura_proveedor", cobertura)
    _guardar("capacidad_actual", capacidad)
    _guardar("servicios_historicos", servicios)
    _guardar("incidentes", incidentes)
    _guardar("condiciones_via", condiciones)
    print(f"{len(proveedores)} proveedores, {len(tarifas)} tarifas, {len(servicios)} servicios, {len(incidentes)} incidentes")


if __name__ == "__main__":
    generar()
