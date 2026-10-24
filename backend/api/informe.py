"""Informe de una decisión: HTML autocontenido e imprimible (o guardable como PDF) y la misma
información como JSON para las gafas.

Ambos formatos salen del mismo documento (`construir_documento`), así la web y las gafas muestran
lo mismo. Muestra lo que vio el funcionario (el snapshot), en 8 secciones: encabezado, solicitud,
decisión, resultados de la opción elegida, comparación, descartados, parámetros y nota al pie.
No ordena ni recomienda: el elegido se marca como decisión del funcionario (regla 1 del README).
No usa recursos externos para que funcione sin internet.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from typing import Optional

from backend.dominio import Solicitud

from . import esquemas as e

NOMBRES_CARGA = {None: "General", "refrigerado": "Refrigerada", "sobredimensionado": "Sobredimensionada",
                 "peligrosa": "Peligrosa"}
HORA_COLOMBIA = timezone(timedelta(hours=-5))

TITULO = "COSCO SHIPPING – Informe de decisión de proveedor"
TITULOS = (TITULO, "La solicitud", "Decisión final", "Resultados predichos para la opción elegida",
           "Comparación con los demás candidatos", "Proveedores descartados", "Parámetros de la simulación",
           "Nota")
NOTA = "Recomendaciones generadas por el sistema; la decisión fue tomada por el funcionario."
SIN_INCIDENTES = "No aplica: los incidentes están fuera del modelo (decisión del 2026-10-24)"
SELLO = "Elegido por el funcionario"


# --- Formatos --------------------------------------------------------------

def _t(x) -> str:
    return escape(str(x))


def _cop(x: Optional[float]) -> str:
    if x is None:
        return "—"
    signo = "−" if x < 0 else ""
    return f"{signo}${abs(x):,.0f}".replace(",", ".")


def _num(x: float, dec: int = 1) -> str:
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(x: float) -> str:
    return f"{_num(100 * x, 1)} %"


def _horas(x: float) -> str:
    return f"{_num(x, 1)} h"


def _margen(x: Optional[float]) -> str:
    return "—" if x is None else f"{_num(x)} %"


def _vehiculos(v: e.Vehiculos) -> str:
    reparto = " + ".join(str(n) for n in v.contenedores_por_vehiculo)
    return f"{v.cantidad} × {v.tipo} (contenedores por vehículo: {reparto})"


def _hora(x: datetime) -> str:
    return f"{x.astimezone(HORA_COLOMBIA):%Y-%m-%d %H:%M} (hora Colombia)"


# --- Bloques ---------------------------------------------------------------

def _datos(pares, titulo: Optional[str] = None) -> e.BloqueInforme:
    return e.BloqueInforme(tipo="datos", titulo=titulo, pares=[e.ParInforme(etiqueta=k, valor=v) for k, v in pares])


def _texto(texto: str, tipo: str = "texto", titulo: Optional[str] = None) -> e.BloqueInforme:
    return e.BloqueInforme(tipo=tipo, titulo=titulo, texto=texto)


def _lista(items, titulo: Optional[str] = None) -> e.BloqueInforme:
    return e.BloqueInforme(tipo="lista", titulo=titulo, items=list(items))


def _seccion(numero: int, bloques) -> e.SeccionInforme:
    return e.SeccionInforme(numero=numero, titulo=TITULOS[numero - 1], bloques=list(bloques))


# --- Secciones ---------------------------------------------------------------

def _encabezado(d: e.Decision) -> list:
    # Funcionario: la API no lo registra todavía, así que no se muestra (no se inventa).
    return [_datos([("ID de la solicitud", d.solicitud_id), ("ID de la decisión", d.decision_id),
                    ("Fecha y hora de la decisión", _hora(d.fecha_hora))])]


def _solicitud(s: Solicitud, ev: e.Evaluacion, cliente: str, vehiculo: Optional[str]) -> list:
    total = s.n_contenedores * s.peso_kg
    pares = [
        ("Origen → destino", f"{ev.ruta.origen} → {ev.ruta.destino}"),
        ("Distancia", f"{_num(ev.ruta.distancia_km, 0)} km"),
        ("Carga", f"{s.n_contenedores} contenedor(es) de 20' × {_num(s.peso_kg, 0)} kg "
                  f"({_num(total, 0)} kg en total) · {NOMBRES_CARGA.get(s.tipo_carga, s.tipo_carga)}"),
        ("Vehículo requerido", vehiculo or "Cualquiera que cumpla (sin tipo exigido)"),
        ("Plazo", _horas(s.plazo_h)),
        ("Cliente", f"{cliente} ({s.cliente_id})"),
        ("Fecha del servicio", s.fecha_servicio.isoformat()),
        ("Presupuesto disponible", _cop(s.presupuesto_cop)),
    ]
    if ev.escenario_id:
        pares.append(("Escenario", f"{ev.escenario_id} (supuestos cambiados por el funcionario)"))
    return [_datos(pares)]


def _decision(d: e.Decision, ev: e.Evaluacion) -> list:
    casi = next((x for x in ev.casi_elegibles if x.proveedor_id == d.proveedor_id), None)
    opciones = [x.vehiculos for x in [*ev.candidatos, *ev.casi_elegibles]
                if x.proveedor_id == d.proveedor_id and x.vehiculos is not None]
    vehiculo = next((v.tipo for v in opciones if v.tipo_vehiculo_id == d.tipo_vehiculo_id), d.tipo_vehiculo_id)
    bloques = [_datos([("Proveedor elegido", f"{d.nombre} ({d.proveedor_id})"),
                       ("Vehículo con el que se registró", vehiculo)]),
               _texto(d.justificacion, "cita", "Motivo escrito por el funcionario")]
    if d.flexibilizado and casi is not None:
        bloques.append(_texto(f"Proveedor casi elegible: el funcionario decidió flexibilizar. No cumplía: "
                              f"{casi.razon.mensaje}. Habría que: {casi.flexibilizar}.", "aviso"))
    return bloques


def _resultados(d: e.Decision, s: Solicitud, ev: e.Evaluacion) -> list:
    c = next((x for x in ev.candidatos if x.proveedor_id == d.proveedor_id), None)
    if c is None:
        casi = next((x for x in ev.casi_elegibles if x.proveedor_id == d.proveedor_id), None)
        bloques = [_texto("No hay resultados simulados: el proveedor era casi elegible y la simulación solo se "
                          "calcula para los candidatos que cumplen todos los requisitos.", "aviso")]
        if casi is not None and casi.vehiculos is not None:
            bloques.append(_datos([("Vehículos", _vehiculos(casi.vehiculos))]))
        return bloques
    t, dz, cf = c.tiempo_h, c.desempeno, c.confianza
    return [
        _datos([
            ("Vehículos", _vehiculos(c.vehiculos)),
            ("Costo del proveedor", _cop(c.costo_cop)),
            ("Ingreso (presupuesto disponible)", _cop(s.presupuesto_cop)),
            ("Profit esperado", _cop(c.profit.esperado_cop)),
            ("Profit en mal escenario (P10)", _cop(c.profit.p10_cop)),
            ("Margen", _margen(c.profit.margen_pct)),
            ("Tiempo típico (P50)", _horas(t.p50)),
            ("Tiempo en mal caso (P90)", _horas(t.p90)),
            ("Probabilidad de llegar a tiempo", _pct(t.prob_a_tiempo)),
            ("Probabilidad de incidente", SIN_INCIDENTES),
        ]),
        _datos([("Valor", f"{_num(dz.valor)} / 100"),
                ("Puntualidad (pesa 75 %)", _pct(dz.desglose.puntualidad)),
                ("Magnitud de retraso (pesa 25 %)", _pct(dz.desglose.magnitud_retraso))], "Desempeño (D)"),
        _datos([("Valor", f"{_num(cf.valor)} / 100 · nivel {cf.nivel}"),
                ("Consistencia de tiempos (2/3 de Q)", _pct(cf.desglose.consistencia)),
                ("Cumplimiento con este cliente (1/3 de Q)", _pct(cf.desglose.cumplimiento_cliente)),
                ("Evidencia histórica (F)", _pct(cf.desglose.evidencia))], "Confianza (C)"),
        _lista([*c.riesgos, *c.avisos] or ["Sin riesgos ni avisos señalados"], "Riesgos y avisos"),
        _texto(c.explicacion, titulo="Explicación"),
    ]


ENCABEZADOS_COMPARACION = ["Proveedor", "Vehículos", "Costo", "Profit esperado", "Profit P10", "Margen", "P50",
                           "P90", "A tiempo", "Desempeño", "Confianza"]


def _comparacion(d: e.Decision, ev: e.Evaluacion) -> list:
    if not ev.candidatos:
        return [_texto("No hubo candidatos que cumplieran todos los requisitos.")]
    cands = sorted(ev.candidatos, key=lambda x: x.proveedor_id)
    filas = [[c.nombre, f"{c.vehiculos.cantidad} × {c.vehiculos.tipo}", _cop(c.costo_cop),
              _cop(c.profit.esperado_cop), _cop(c.profit.p10_cop), _margen(c.profit.margen_pct),
              _horas(c.tiempo_h.p50), _horas(c.tiempo_h.p90), _pct(c.tiempo_h.prob_a_tiempo),
              _num(c.desempeno.valor), f"{_num(c.confianza.valor)} {c.confianza.nivel}"] for c in cands]
    elegida = next((i for i, c in enumerate(cands) if c.proveedor_id == d.proveedor_id), None)
    return [_texto("Ordenado por identificador del proveedor, no por preferencia: el sistema no impone un ganador."),
            e.BloqueInforme(tipo="tabla", encabezados=ENCABEZADOS_COMPARACION, filas=filas, resaltada=elegida)]


def _descartados(ev: e.Evaluacion) -> list:
    if not ev.cancelados:
        return [_texto("Ningún proveedor fue descartado.")]
    bloques = [e.BloqueInforme(tipo="razones", titulo=f"{x.nombre} ({x.proveedor_id})", razones=x.razones)
               for x in sorted(ev.cancelados, key=lambda c: c.proveedor_id)]
    if ev.casi_elegibles:
        bloques.append(e.BloqueInforme(
            tipo="tabla", titulo="Casi elegibles (fallan una sola regla)",
            encabezados=["Proveedor", "No cumple", "Qué habría que flexibilizar"],
            filas=[[x.nombre, x.razon.mensaje, x.flexibilizar] for x in ev.casi_elegibles]))
    return bloques


def _parametros(ev: e.Evaluacion) -> list:
    p = ev.parametros_escenario
    return [
        _datos([("Simulaciones (N)", _num(p.n_simulaciones, 0)), ("Semilla", str(p.semilla)),
                ("Escenario", ev.escenario_id or "Original (sin cambios de supuestos)"),
                ("Penalidad por hora de retraso", _cop(p.penal_hora_cop)), ("Plazo usado", _horas(p.plazo_h))]),
        _lista([
            "Vehículos: contenedores por vehículo = mín(puestos TEU, ⌊capacidad kg / peso del contenedor⌋); "
            "se usa el tipo más económico que cumple.",
            f"Tiempo: simulación Monte Carlo con {_num(p.n_simulaciones, 0)} iteraciones y semilla {p.semilla} "
            "(resultados reproducibles), a partir del historial del proveedor y del mercado en la ruta.",
            f"Profit: presupuesto − costo del proveedor − costo esperado de retraso (penalidad "
            f"{_cop(p.penal_hora_cop)} por hora sobre el plazo de {_horas(p.plazo_h)}).",
            "Desempeño: 100 · [0,75 · puntualidad + 0,25 · (1 − magnitud del retraso)], con recencia de 12 meses "
            "y suavizado hacia el mercado.",
            "Confianza: 100 · Q · F, con Q = 2/3 consistencia de tiempos + 1/3 cumplimiento con este cliente y "
            "F = evidencia histórica.",
        ], "Cómo se calcularon los valores"),
    ]


def construir_documento(d: e.Decision, solicitud: Solicitud, cliente: str, vehiculo: Optional[str] = None,
                        generado: Optional[datetime] = None) -> e.InformeDecision:
    """Las 8 secciones del informe como datos. `vehiculo` es el nombre del tipo exigido en la solicitud."""
    ev = d.snapshot
    generado = generado or datetime.now(timezone.utc)
    secciones = [
        _seccion(1, _encabezado(d)),
        _seccion(2, _solicitud(solicitud, ev, cliente, vehiculo)),
        _seccion(3, _decision(d, ev)),
        _seccion(4, _resultados(d, solicitud, ev)),
        _seccion(5, _comparacion(d, ev)),
        _seccion(6, _descartados(ev)),
        _seccion(7, _parametros(ev)),
        _seccion(8, [_texto(NOTA), _texto(f"Generado el {_hora(generado)}. Este informe reproduce exactamente lo "
                                          "que se mostró al decidir.")]),
    ]
    return e.InformeDecision(decision_id=d.decision_id, solicitud_id=d.solicitud_id, proveedor_id=d.proveedor_id,
                             fecha_hora=d.fecha_hora, generado=generado, secciones=secciones)


# --- HTML ------------------------------------------------------------------------

def _html_bloque(b: e.BloqueInforme) -> str:
    h3 = f"<h3>{_t(b.titulo)}</h3>" if b.titulo else ""
    if b.tipo == "datos":
        return h3 + "<dl class='datos'>" + "".join(f"<dt>{_t(p.etiqueta)}</dt><dd>{_t(p.valor)}</dd>"
                                                   for p in b.pares) + "</dl>"
    if b.tipo == "texto":
        return f"{h3}<p>{_t(b.texto)}</p>"
    if b.tipo == "cita":
        return f"{h3}<blockquote>{_t(b.texto)}</blockquote>"
    if b.tipo == "aviso":
        return f"{h3}<p class='aviso'>{_t(b.texto)}</p>"
    if b.tipo == "lista":
        return h3 + "<ul>" + "".join(f"<li>{_t(i)}</li>" for i in b.items) + "</ul>"
    if b.tipo == "razones":
        razones = "".join(
            f"<li><code>{_t(r.codigo)}</code> {_t(r.mensaje)}<span class='tenue'> · requerido: "
            f"{_t('—' if r.requerido is None else r.requerido)} · disponible: "
            f"{_t('—' if r.disponible is None else r.disponible)}</span></li>" for r in b.razones)
        return f"<div class='descartado'>{h3}<ul>{razones}</ul></div>"
    th = "".join(f"<th>{_t(x)}</th>" for x in b.encabezados)
    celda = "<td class='n'>{}</td>" if len(b.encabezados) > 3 else "<td>{}</td>"   # la comparación es numérica
    filas = []
    for i, fila in enumerate(b.filas):
        elegida = i == b.resaltada
        sello = f" <span class='sello'>{SELLO}</span>" if elegida else ""
        clase = " class='fila-elegida'" if elegida else ""
        celdas = f"<td>{_t(fila[0])}{sello}</td>" + "".join(celda.format(_t(v)) for v in fila[1:])
        filas.append(f"<tr{clase}>{celdas}</tr>")
    clase_tabla = " class='comparacion'" if len(b.encabezados) > 3 else ""
    return f"{h3}<div class='tabla'><table{clase_tabla}><thead><tr>{th}</tr></thead><tbody>{''.join(filas)}</tbody></table></div>"


def _grafico_tiempos(d: e.Decision, ev: e.Evaluacion) -> str:
    """Rango P10–P90 simulado de cada candidato, con P50 y el plazo marcados (SVG en línea)."""
    plazo = ev.parametros_escenario.plazo_h
    cands = sorted(ev.candidatos, key=lambda x: x.proveedor_id)
    extremos = [plazo] + [v for c in cands for v in c.tiempo_h.abanico.values()]
    lo, hi = 0.0, max(extremos) * 1.08
    ancho, izq, alto_fila = 720, 210, 26
    x = lambda h: izq + (ancho - izq - 20) * (h - lo) / (hi - lo)
    alto = 30 + alto_fila * len(cands) + 26
    partes = [f'<svg viewBox="0 0 {ancho} {alto}" role="img" aria-label="Tiempos de tránsito simulados">']
    for i, c in enumerate(cands):
        y = 24 + i * alto_fila
        a = c.tiempo_h.abanico
        bajo, alto_p = a.get("10", c.tiempo_h.p50), a.get("90", c.tiempo_h.p90)
        clase = "rango elegido" if c.proveedor_id == d.proveedor_id else "rango"
        partes.append(f'<text x="{izq - 8}" y="{y + 12}" text-anchor="end" class="etq">{_t(c.nombre[:28])}</text>')
        partes.append(f'<rect class="{clase}" x="{x(bajo):.1f}" y="{y + 3}" width="{max(2, x(alto_p) - x(bajo)):.1f}" '
                      f'height="12" rx="3"/>')
        partes.append(f'<line class="p50" x1="{x(c.tiempo_h.p50):.1f}" x2="{x(c.tiempo_h.p50):.1f}" '
                      f'y1="{y}" y2="{y + 18}"/>')
    y_fin = 24 + alto_fila * len(cands)
    partes.append(f'<line class="plazo" x1="{x(plazo):.1f}" x2="{x(plazo):.1f}" y1="14" y2="{y_fin}"/>')
    partes.append(f'<text x="{x(plazo):.1f}" y="11" text-anchor="middle" class="etq plazo-t">Plazo {_horas(plazo)}</text>')
    for h in range(0, int(hi) + 1, max(1, int(hi // 6) or 1)):
        partes.append(f'<text x="{x(h):.1f}" y="{y_fin + 18}" text-anchor="middle" class="eje">{h} h</text>')
    partes.append("</svg>")
    return ("<figure><figcaption>Tiempo de tránsito simulado: barra del percentil 10 al 90, raya en el P50 "
            "y línea roja en el plazo.</figcaption>" + "".join(partes) + "</figure>")


ESTILOS = """
:root{--tinta:#16243b;--tenue:#5b6b82;--linea:#d9e0ea;--acento:#175cde;--suave:#eef3fb;--aviso:#fff4dc;--rojo:#c2410c}
*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:var(--tinta);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1000px;margin:24px auto;background:#fff;padding:32px 40px;border:1px solid var(--linea);border-radius:10px}
header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;border-bottom:2px solid var(--acento);padding-bottom:16px}
h1{font-size:24px;margin:0 0 8px}h2{font-size:18px;margin:28px 0 10px;padding-bottom:4px;border-bottom:1px solid var(--linea)}
h3{font-size:15px;margin:16px 0 6px}
.tenue{color:var(--tenue);font-size:.92em}.acciones{text-align:right}.ayuda{display:block;margin-top:6px;max-width:220px}
.datos{display:grid;grid-template-columns:280px 1fr;gap:6px 16px;margin:0}.datos dt{color:var(--tenue)}.datos dd{margin:0}
header .datos{grid-template-columns:200px 1fr}
blockquote{margin:0 0 16px;padding:10px 14px;background:var(--suave);border-left:4px solid var(--acento);border-radius:4px}
table{width:100%;border-collapse:collapse;font-size:13.5px}th,td{padding:7px 8px;border-bottom:1px solid var(--linea);text-align:left;vertical-align:top}
th{background:var(--suave);font-weight:600}td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tabla{overflow-x:auto}table.comparacion{font-size:12.5px}table.comparacion th,table.comparacion td{padding:6px 5px}
.fila-elegida td{background:#e8f0ff;font-weight:600}.sello{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:10px;background:var(--acento);color:#fff;font-size:11px;font-weight:600}
.descartado ul{margin:0;padding-left:18px}code{background:var(--suave);padding:0 4px;border-radius:3px;font-size:12px}
.aviso{background:var(--aviso);padding:10px 14px;border-radius:6px}
figure{margin:16px 0 0}figcaption{color:var(--tenue);font-size:13px;margin-bottom:4px}svg{width:100%;height:auto}
svg .etq{font-size:11px;fill:var(--tinta)}svg .eje{font-size:10px;fill:var(--tenue)}
svg .rango{fill:#c7d5ee}svg .rango.elegido{fill:var(--acento)}svg .p50{stroke:var(--tinta);stroke-width:2}
svg .plazo{stroke:var(--rojo);stroke-width:2;stroke-dasharray:4 3}svg .plazo-t{fill:var(--rojo);font-weight:600}
footer{margin-top:32px;padding-top:12px;border-top:1px solid var(--linea)}footer h2{border:0;margin-top:0}footer p{margin:4px 0}
button{font:inherit;padding:8px 14px;border:1px solid var(--acento);background:var(--acento);color:#fff;border-radius:6px;cursor:pointer}
@media (max-width:700px){main{padding:20px 16px;margin:0;border-radius:0}header{display:block}.acciones{text-align:left;margin-top:12px}.datos,header .datos{grid-template-columns:1fr}.datos dt{margin-top:6px}table{display:block;overflow-x:auto}}
@media print{body{background:#fff}main{margin:0;border:0;padding:0;max-width:none}.acciones{display:none}h2,h3{break-after:avoid}tr,li{break-inside:avoid}.tabla{overflow:visible}table.comparacion{font-size:8.5px}table.comparacion th,table.comparacion td{padding:3px 2px}.fila-elegida td{background:#e8f0ff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def construir_informe(d: e.Decision, solicitud: Solicitud, cliente: str, vehiculo: Optional[str] = None,
                      generado: Optional[datetime] = None) -> str:
    """HTML imprimible. "Descargar PDF" usa la impresión del navegador (Guardar como PDF): sin librerías."""
    doc = construir_documento(d, solicitud, cliente, vehiculo, generado)
    s = doc.secciones
    cuerpo = []
    for sec in s[1:7]:
        extra = _grafico_tiempos(d, d.snapshot) if sec.numero == 5 and d.snapshot.candidatos else ""
        cuerpo.append(f"<section id='seccion-{sec.numero}'><h2>{sec.numero}. {_t(sec.titulo)}</h2>"
                      + "".join(_html_bloque(b) for b in sec.bloques) + extra + "</section>")
    nota = "".join(f"<p{'' if i == 0 else ' class=tenue'}>{_t(b.texto)}</p>" for i, b in enumerate(s[7].bloques))
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe {_t(d.decision_id)} · {_t(d.solicitud_id)}</title><style>{ESTILOS}</style></head>
<body><main>
<header id="seccion-1"><div><h1>{_t(s[0].titulo)}</h1>{"".join(_html_bloque(b) for b in s[0].bloques)}</div>
<div class="acciones"><button type="button" onclick="window.print()">Descargar PDF</button>
<span class="tenue ayuda">En la ventana de impresión elige «Guardar como PDF».</span></div></header>
{"".join(cuerpo)}
<footer id="seccion-8"><h2>{_t(s[7].titulo)}</h2>{nota}</footer>
</main></body></html>
"""


def nombre_archivo(d: e.Decision) -> str:
    return f"informe_{d.decision_id}_{d.solicitud_id}.html"
