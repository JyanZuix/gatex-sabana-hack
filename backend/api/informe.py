"""Informe descargable de una decisión (HTML autocontenido, imprimible o guardable como PDF).

Muestra lo que vio el funcionario (el snapshot): la solicitud, la opción que eligió con su
justificación, la comparación con las demás opciones, los descartados con sus razones y los
parámetros de la simulación. No ordena ni recomienda: el elegido se marca como decisión del
funcionario (regla 1 del README). No usa recursos externos para que funcione sin internet.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from typing import Iterable, Optional

from backend.dominio import Solicitud

from . import esquemas as e

NOMBRES_CARGA = {None: "General", "refrigerado": "Refrigerada", "sobredimensionado": "Sobredimensionada",
                 "peligrosa": "Peligrosa"}
HORA_COLOMBIA = timezone(timedelta(hours=-5))


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


def _reparto(v: e.Vehiculos) -> str:
    return " + ".join(str(n) for n in v.contenedores_por_vehiculo)


def _barra(valor: float, maximo: float = 100, clase: str = "") -> str:
    ancho = max(0.0, min(100.0, 100 * valor / maximo)) if maximo else 0
    return f'<span class="barra {clase}"><span style="width:{ancho:.1f}%"></span></span>'


def _tabla(encabezados: Iterable[str], filas: Iterable[str], clase: str = "") -> str:
    th = "".join(f"<th>{h}</th>" for h in encabezados)
    return f'<table class="{clase}"><thead><tr>{th}</tr></thead><tbody>{"".join(filas)}</tbody></table>'


# --- Secciones --------------------------------------------------------------

def _datos_solicitud(s: Solicitud, ev: e.Evaluacion, cliente: str) -> str:
    vehiculo = s.tipo_vehiculo_id or "Cualquiera que cumpla"
    filas = [
        ("Cliente", f"{_t(cliente)} <span class='tenue'>({_t(s.cliente_id)})</span>"),
        ("Ruta", f"{_t(ev.ruta.origen)} → {_t(ev.ruta.destino)} · {_num(ev.ruta.distancia_km, 0)} km"),
        ("Fecha del servicio", _t(s.fecha_servicio.isoformat())),
        ("Plazo", _horas(s.plazo_h)),
        ("Carga", f"{s.n_contenedores} contenedor(es) de 20' × {_num(s.peso_kg, 0)} kg · "
                  f"{NOMBRES_CARGA.get(s.tipo_carga, s.tipo_carga)}"),
        ("Vehículo exigido", _t(vehiculo)),
        ("Presupuesto disponible", _cop(s.presupuesto_cop)),
    ]
    if ev.escenario_id:
        filas.append(("Escenario", f"{_t(ev.escenario_id)} (supuestos cambiados por el funcionario)"))
    return "<dl class='datos'>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in filas) + "</dl>"


def _bloque_elegido(d: e.Decision, ev: e.Evaluacion) -> str:
    c = next((x for x in ev.candidatos if x.proveedor_id == d.proveedor_id), None)
    casi = next((x for x in ev.casi_elegibles if x.proveedor_id == d.proveedor_id), None)
    cabecera = (f"<p class='elegido-nombre'>{_t(d.nombre)} <span class='tenue'>({_t(d.proveedor_id)})</span></p>"
                f"<blockquote>{_t(d.justificacion)}</blockquote>")
    if c is not None:
        v = c.vehiculos
        cifras = [
            ("Vehículos", f"{v.cantidad} × {_t(v.tipo)} · contenedores por vehículo: {_reparto(v)}"),
            ("Costo", _cop(c.costo_cop)),
            ("Profit", _cop(c.profit.cop)),
            ("Margen", "—" if c.profit.margen_pct is None else f"{_num(c.profit.margen_pct)} %"),
            ("Puesto y puntaje", f"#{c.puesto} · {_num(c.puntaje.valor)} / 100"),
            ("Tiempo", _t(c.tiempo_h.resumen)),
            ("Capacidad", _t(c.capacidad.texto)),
            ("Desempeño", f"{_barra(c.desempeno.valor)} {_t(c.desempeno.texto)}"),
            ("Confianza", f"{_barra(c.confianza.valor, clase='conf')} {_t(c.confianza.texto)}"),
        ]
        cuerpo = "<dl class='datos'>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in cifras) + "</dl>"
        cuerpo += f"<p><strong>Explicación:</strong> {_t(c.explicacion)}</p>"
        for titulo, lista in (("Fortalezas", c.fortalezas), ("Debilidades", c.debilidades)):
            if lista:
                cuerpo += f"<p><strong>{titulo}:</strong> " + "; ".join(_t(x) for x in lista) + ".</p>"
        if c.riesgos or c.avisos:
            cuerpo += "<ul class='riesgos'>" + "".join(f"<li>{_t(r)}</li>" for r in [*c.riesgos, *c.avisos]) + "</ul>"
    elif casi is not None:
        cuerpo = (f"<p class='aviso'><strong>Proveedor casi elegible: el funcionario decidió flexibilizar.</strong><br>"
                  f"No cumplía: {_t('; '.join(c.razon.mensaje for c in casi.condiciones))}.<br>"
                  f"Habría que: {_t('; '.join(c.flexibilizar for c in casi.condiciones))}.</p>")
        if casi.vehiculos is not None:
            v = casi.vehiculos
            cuerpo += f"<p>Vehículos: {v.cantidad} × {_t(v.tipo)} · contenedores por vehículo: {_reparto(v)}</p>"
    else:
        cuerpo = ""
    return cabecera + cuerpo


def _comparacion(d: e.Decision, ev: e.Evaluacion) -> str:
    if not ev.candidatos:
        return "<p>No hubo candidatos que cumplieran todos los requisitos.</p>"
    filas = []
    top_n = ev.parametros_escenario.pesos_puntaje.top_n
    for c in sorted(ev.candidatos, key=lambda x: x.puesto):
        marca = " class='fila-elegida'" if c.proveedor_id == d.proveedor_id else ""
        etiqueta = " <span class='sello'>Elegido por el funcionario</span>" if marca else ""
        sugerido = f" <span class='sello top'>Top {top_n}</span>" if c.top else ""
        filas.append(
            f"<tr{marca}><td class='n'>{c.puesto}</td><td>{_t(c.nombre)}{sugerido}{etiqueta}</td>"
            f"<td class='n'>{_num(c.puntaje.valor)}</td>"
            f"<td>{c.vehiculos.cantidad} × {_t(c.vehiculos.tipo)}</td>"
            f"<td class='n'>{_cop(c.costo_cop)}</td><td class='n'>{_cop(c.profit.cop)}</td>"
            f"<td class='n'>{'—' if c.profit.margen_pct is None else _num(c.profit.margen_pct) + ' %'}</td>"
            f"<td class='n'>{_horas(c.tiempo_h.p50)}</td><td class='n'>{_horas(c.tiempo_h.p90)}</td>"
            f"<td class='n'>{_pct(c.tiempo_h.prob_a_tiempo)}</td>"
            f"<td class='n'>{_num(c.desempeno.valor)}</td>"
            f"<td class='n'>{_num(c.confianza.valor)} <span class='tenue'>{_t(c.confianza.nivel)}</span></td></tr>")
    tabla = _tabla(["#", "Proveedor", "Puntaje", "Vehículos", "Costo", "Profit", "Margen", "Tiempo habitual", "Día malo", "A tiempo",
                    "Desempeño", "Confianza"], filas, "comparacion")
    return (f"<p class='tenue'>Ordenado por puntaje, de mayor a menor. El sistema sugiere los {top_n} primeros; "
            "la elección y su justificación son del funcionario.</p>" + tabla + _grafico_tiempos(d, ev))


def _grafico_tiempos(d: e.Decision, ev: e.Evaluacion) -> str:
    """Rango P10–P90 simulado de cada candidato, con P50 y el plazo marcados (SVG en línea)."""
    plazo = ev.parametros_escenario.plazo_h
    cands = sorted(ev.candidatos, key=lambda x: x.puesto)
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
    return ("<figure><figcaption>Tiempo de tránsito simulado: la barra va de un día bueno (percentil 10) a un día malo (percentil 90), la raya es el tiempo habitual (mediana) "
            "y línea roja en el plazo.</figcaption>" + "".join(partes) + "</figure>")


def _descartados(ev: e.Evaluacion) -> str:
    if not ev.cancelados:
        return "<p>Ningún proveedor fue descartado.</p>"
    filas = []
    for x in sorted(ev.cancelados, key=lambda c: c.proveedor_id):
        razones = "".join(
            f"<li><code>{_t(r.codigo)}</code> {_t(r.mensaje)}"
            f"<span class='tenue'> · requerido: {_t(r.requerido if r.requerido is not None else '—')}"
            f" · disponible: {_t(r.disponible if r.disponible is not None else '—')}</span></li>" for r in x.razones)
        filas.append(f"<tr><td>{_t(x.nombre)}<br><span class='tenue'>{_t(x.proveedor_id)}</span></td>"
                     f"<td><ul>{razones}</ul></td></tr>")
    return _tabla(["Proveedor", "Razones (todas las reglas que incumple)"], filas, "descartados")


def _casi(ev: e.Evaluacion) -> str:
    if not ev.casi_elegibles:
        return ""
    filas = []
    for x in ev.casi_elegibles:
        sello = " <span class='sello'>Opción viable con condición</span>" if x.recomendada else ""
        no_cumple = "<br>".join(_t(c.razon.mensaje) for c in x.condiciones)
        flexibilizar = "<br>".join(_t(c.flexibilizar) for c in x.condiciones)
        filas.append(f"<tr><td class='n'>{x.puesto}</td><td>{_t(x.nombre)}{sello}</td><td>{no_cumple}</td>"
                     f"<td>{flexibilizar}</td></tr>")
    return ("<h2>Casi elegibles</h2><p class='tenue'>Ningún proveedor cumplía todo: se muestran los que fallan menos "
            "condiciones, del vehículo más barato al más caro.</p>"
            + _tabla(["#", "Proveedor", "No cumple", "Qué habría que flexibilizar"], filas))


# --- Documento ----------------------------------------------------------------

ESTILOS = """
:root{--tinta:#16243b;--tenue:#5b6b82;--linea:#d9e0ea;--acento:#175cde;--suave:#eef3fb;--aviso:#fff4dc;--rojo:#c2410c}
*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:var(--tinta);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1000px;margin:24px auto;background:#fff;padding:32px 40px;border:1px solid var(--linea);border-radius:10px}
header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;border-bottom:2px solid var(--acento);padding-bottom:16px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:28px 0 10px;padding-bottom:4px;border-bottom:1px solid var(--linea)}
.tenue{color:var(--tenue);font-size:.92em}.ids{font-variant-numeric:tabular-nums;text-align:right}
.datos{display:grid;grid-template-columns:260px 1fr;gap:6px 16px;margin:0}.datos dt{color:var(--tenue)}.datos dd{margin:0}
.elegido-nombre{font-size:20px;font-weight:700;color:var(--acento);margin:0 0 8px}
blockquote{margin:0 0 16px;padding:10px 14px;background:var(--suave);border-left:4px solid var(--acento);border-radius:4px}
.barra{display:inline-block;width:120px;height:8px;background:var(--linea);border-radius:4px;vertical-align:middle;margin-left:8px}
.barra span{display:block;height:100%;background:var(--acento);border-radius:4px}.barra.conf span{background:#0f766e}
table{width:100%;border-collapse:collapse;font-size:13.5px}th,td{padding:7px 8px;border-bottom:1px solid var(--linea);text-align:left;vertical-align:top}
th{background:var(--suave);font-weight:600}td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.fila-elegida td{background:#e8f0ff;font-weight:600}.sello{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:10px;background:var(--acento);color:#fff;font-size:11px;font-weight:600}.sello.top{background:#2f7d4f}
.descartados ul{margin:0;padding-left:18px}code{background:var(--suave);padding:0 4px;border-radius:3px;font-size:12px}
.aviso{background:var(--aviso);padding:10px 14px;border-radius:6px}.riesgos{color:var(--rojo)}
figure{margin:16px 0 0}figcaption{color:var(--tenue);font-size:13px;margin-bottom:4px}svg{width:100%;height:auto}
svg .etq{font-size:11px;fill:var(--tinta)}svg .eje{font-size:10px;fill:var(--tenue)}
svg .rango{fill:#c7d5ee}svg .rango.elegido{fill:var(--acento)}svg .p50{stroke:var(--tinta);stroke-width:2}
svg .plazo{stroke:var(--rojo);stroke-width:2;stroke-dasharray:4 3}svg .plazo-t{fill:var(--rojo);font-weight:600}
footer{margin-top:32px;padding-top:12px;border-top:1px solid var(--linea);color:var(--tenue);font-size:12.5px}
button{font:inherit;padding:8px 14px;border:1px solid var(--acento);background:var(--acento);color:#fff;border-radius:6px;cursor:pointer}
@media (max-width:700px){main{padding:20px 16px;margin:0;border-radius:0}.datos{grid-template-columns:1fr}.datos dt{margin-top:6px}table{display:block;overflow-x:auto}}
@media print{body{background:#fff}main{margin:0;border:0;padding:0;max-width:none}button{display:none}.fila-elegida td{background:#e8f0ff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def construir_informe(d: e.Decision, solicitud: Solicitud, cliente: str,
                      generado: Optional[datetime] = None) -> str:
    ev = d.snapshot
    generado = (generado or datetime.now(timezone.utc)).astimezone(HORA_COLOMBIA)
    decidido = d.fecha_hora.astimezone(HORA_COLOMBIA)
    p = ev.parametros_escenario
    w = p.pesos_puntaje
    flex = " · proveedor casi elegible (flexibilizado)" if d.flexibilizado else ""
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe {_t(d.decision_id)} · {_t(d.solicitud_id)}</title><style>{ESTILOS}</style></head>
<body><main>
<header><div><h1>Informe de decisión de transporte terrestre</h1>
<div class="tenue">Sala de Simulación de Proveedores · COSCO SHIPPING Colombia</div></div>
<div class="ids"><strong>{_t(d.decision_id)}</strong><br>{_t(d.solicitud_id)}<br>
<span class="tenue">Decidido {decidido:%Y-%m-%d %H:%M} (hora Colombia)</span><br>
<button type="button" onclick="window.print()">Imprimir o guardar PDF</button></div></header>

<h2>Solicitud</h2>{_datos_solicitud(solicitud, ev, cliente)}

<h2>Decisión del funcionario{flex}</h2>{_bloque_elegido(d, ev)}

<h2>Opciones que cumplían los requisitos ({len(ev.candidatos)})</h2>{_comparacion(d, ev)}

<h2>Proveedores descartados ({len(ev.cancelados)})</h2>{_descartados(ev)}
{_casi(ev)}
<h2>Cómo se calcularon los valores</h2>
<ul>
<li><strong>Vehículos:</strong> contenedores por vehículo = mín(puestos TEU, ⌊capacidad kg / peso del contenedor⌋); se usa el tipo más económico que cumple.</li>
<li><strong>Tiempo:</strong> simulación Monte Carlo con {p.n_simulaciones} iteraciones y semilla {p.semilla} (resultados reproducibles), a partir del historial del proveedor y del mercado en la ruta.</li>
<li><strong>Profit:</strong> presupuesto − costo del proveedor. Quien da pérdida se descarta (<code>SIN_MARGEN</code>).</li>
<li><strong>Puntaje:</strong> 100 · ({_num(w.profit, 2)} · profit frente al mejor + {_num(w.a_tiempo, 2)} · probabilidad de llegar a tiempo + {_num(w.desempeno, 2)} · desempeño/100 + {_num(w.confianza, 2)} · confianza/100). Ordena a los candidatos; se sugieren los {w.top_n} primeros.</li>
<li><strong>Desempeño:</strong> 100 · [0,75 · puntualidad + 0,25 · (1 − magnitud del retraso)], con recencia de 12 meses y suavizado hacia el mercado.</li>
<li><strong>Confianza:</strong> 100 · Q · F, con Q = ⅔ consistencia de tiempos + ⅓ cumplimiento con este cliente y F = evidencia histórica.</li>
</ul>
<h2>Glosario</h2>
<dl class='datos'>
<dt>Tiempo habitual</dt><dd>La mitad de los viajes simulados llega antes de este tiempo (mediana, P50).</dd>
<dt>Día malo</dt><dd>Solo 1 de cada 10 viajes simulados tarda más que esto (percentil 90, P90).</dd>
<dt>Llega a tiempo</dt><dd>Porcentaje de los {p.n_simulaciones} viajes simulados que llegan dentro del plazo.</dd>
<dt>Desempeño</dt><dd>De 0 a 100: qué tanto cumplió los plazos en su historial y cuánto se atrasó cuando no cumplió.</dd>
<dt>Confianza</dt><dd>De 0 a 100: qué tan confiables son esos datos (cuántos servicios hay y qué tan estables son sus tiempos).</dd>
<dt>Puntaje</dt><dd>De 0 a 100: combina profit, llegar a tiempo, desempeño y confianza con los pesos de arriba.</dd>
</dl>

<footer>Generado el {generado:%Y-%m-%d %H:%M} (hora Colombia). El sistema ordena las opciones por puntaje y explica sus
consecuencias; la decisión y su justificación son del funcionario. Este informe reproduce exactamente lo que se
mostró al decidir.</footer>
</main></body></html>
"""


def nombre_archivo(d: e.Decision) -> str:
    return f"informe_{d.decision_id}_{d.solicitud_id}.html"
