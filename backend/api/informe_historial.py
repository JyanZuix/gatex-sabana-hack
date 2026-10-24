"""Informe HTML del track record de todos los proveedores, mes a mes (GET /historial/proveedores/informe).

Reutiliza los estilos y utilidades del informe de decisión. Todo sale de `HistorialProveedores`,
que a su vez sale de la ficha de cada proveedor: el informe, la tablet y la API muestran lo mismo.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.config import Config

from . import esquemas as e
from .informe import ESTILOS, HORA_COLOMBIA, _barra, _num, _t, _tabla

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

ESTILOS_HISTORIAL = """
.matriz td.c{text-align:center;font-variant-numeric:tabular-nums;white-space:nowrap;padding:5px 4px}
.matriz td.alto{background:#dcf2e3}.matriz td.medio{background:#fff1d6}.matriz td.bajo{background:#fde2dc}
.matriz td.vacio{color:var(--tenue)}.matriz small{display:block;color:var(--tenue);font-size:10.5px}
.matriz th.c{text-align:center}.leyenda span{display:inline-block;padding:1px 8px;border-radius:4px;margin-right:8px}
svg.linea{vertical-align:middle}svg.linea polyline{fill:none;stroke:var(--acento);stroke-width:2}
svg.linea circle{fill:var(--acento)}.prov h3{margin:18px 0 4px;font-size:16px}
"""


def etiqueta_mes(mes: str) -> str:
    """'2026-05' → 'may-26'."""
    anio, m = mes.split("-")
    return f"{MESES[int(m) - 1]}-{anio[2:]}"


def _sparkline(f: e.FichaProveedor, meses: list[str]) -> str:
    """Desempeño mes a mes (0-100) como línea; los meses sin servicios se saltan."""
    por_mes = {p.mes: p.desempeno for p in f.tendencia}
    puntos = [(i, por_mes[m]) for i, m in enumerate(meses) if m in por_mes]
    if not puntos:
        return "<span class='tenue'>sin datos</span>"
    ancho, alto = 150, 30
    paso = ancho / max(1, len(meses) - 1)
    xy = [(4 + i * paso * (ancho - 8) / ancho, alto - 3 - (alto - 6) * v / 100) for i, v in puntos]
    trazo = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    ultimo = xy[-1]
    return (f'<svg class="linea" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" '
            f'aria-label="Desempeño mes a mes de {_t(f.nombre)}"><polyline points="{trazo}"/>'
            f'<circle cx="{ultimo[0]:.1f}" cy="{ultimo[1]:.1f}" r="2.5"/></svg>')


def _resumen(h: e.HistorialProveedores) -> str:
    filas = []
    for i, f in enumerate(h.proveedores, start=1):
        punt = "—" if f.puntualidad_pct is None else f"{_num(f.puntualidad_pct, 0)} %"
        ultimo = "—" if f.ultimo_servicio is None else f.ultimo_servicio.isoformat()
        filas.append(
            f"<tr><td class='n'>{i}</td><td>{_t(f.nombre)}<br><span class='tenue'>{_t(f.estado)}</span></td>"
            f"<td class='n'>{f.servicios}</td><td class='n'>{punt}</td>"
            f"<td class='n'>{_num(f.desempeno.valor, 0)} {_barra(f.desempeno.valor)}</td>"
            f"<td class='n'>{_num(f.confianza.valor, 0)} <span class='tenue'>{_t(f.confianza.nivel)}</span></td>"
            f"<td>{_sparkline(f, h.meses)}</td><td class='n'>{ultimo}</td></tr>")
    return _tabla(["#", "Proveedor", "Servicios", "A tiempo", "Desempeño", "Confianza", "Desempeño mes a mes",
                   "Último servicio"], filas)


def _matriz(h: e.HistorialProveedores, cfg: Config) -> str:
    encabezado = "".join(f"<th class='c'>{etiqueta_mes(m)}</th>" for m in h.meses)
    filas = []
    for f in h.proveedores:
        por_mes = {p.mes: p for p in f.tendencia}
        celdas = []
        for m in h.meses:
            p = por_mes.get(m)
            if p is None:
                celdas.append("<td class='c vacio'>—</td>")
            else:
                celdas.append(f"<td class='c {p.nivel}'>{_num(p.a_tiempo_pct, 0)} %"
                              f"<small>{p.servicios} serv. · D {_num(p.desempeno, 0)}</small></td>")
        filas.append(f"<tr><td>{_t(f.nombre)}</td>{''.join(celdas)}</tr>")
    return (f"<table class='matriz'><thead><tr><th>Proveedor</th>{encabezado}</tr></thead>"
            f"<tbody>{''.join(filas)}</tbody></table>")


def _detalle(h: e.HistorialProveedores) -> str:
    partes = []
    for f in h.proveedores:
        if not (f.fortalezas or f.debilidades):
            continue
        lineas = [f"<li><strong>Fortaleza:</strong> {_t(x)}</li>" for x in f.fortalezas]
        lineas += [f"<li><strong>Debilidad:</strong> {_t(x)}</li>" for x in f.debilidades]
        partes.append(f"<div class='prov'><h3>{_t(f.nombre)}</h3><ul>{''.join(lineas)}</ul></div>")
    return "".join(partes) or "<p class='tenue'>Ningún proveedor tiene diferencias marcadas por ruta, vehículo o carga.</p>"


def construir_informe_historial(h: e.HistorialProveedores, cfg: Config, generado: Optional[datetime] = None) -> str:
    generado = (generado or datetime.now(timezone.utc)).astimezone(HORA_COLOMBIA)
    h = h.model_copy(update={"meses": h.meses[-cfg.ficha.meses_informe:]})
    alto, medio = _num(100 * cfg.textos.puntualidad_alta, 0), _num(100 * cfg.riesgo.min_a_tiempo, 0)
    periodo = f"{etiqueta_mes(h.meses[0])} a {etiqueta_mes(h.meses[-1])}" if h.meses else "sin servicios"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Historial de proveedores</title><style>{ESTILOS}{ESTILOS_HISTORIAL}</style></head>
<body><main>
<header><div><h1>Historial de proveedores, mes a mes</h1>
<div class="tenue">Sala de Simulación de Proveedores · COSCO SHIPPING Colombia · {periodo}</div></div>
<div class="ids"><strong>{len(h.proveedores)} proveedores</strong><br>
<span class="tenue">Datos al {h.generado.isoformat()}</span><br>
<button type="button" onclick="window.print()">Imprimir o guardar PDF</button></div></header>

<h2>Resumen</h2>
<p class="tenue">Ordenado por desempeño, de mayor a menor. Servicios y "a tiempo" cubren todo el historial; la línea y
la tabla mensual, los últimos {len(h.meses)} meses. Desempeño y confianza con el mismo cálculo que usa la sala
(lo reciente pesa más; con pocos datos se acerca al promedio del mercado).</p>
{_resumen(h)}

<h2>Entregas a tiempo, mes a mes</h2>
<p class="leyenda tenue"><span style="background:#dcf2e3">≥ {alto} %</span><span style="background:#fff1d6">{medio}–{alto} %</span><span style="background:#fde2dc">&lt; {medio} %</span>
Debajo de cada porcentaje: servicios del mes y desempeño (D) de ese mes.</p>
{_matriz(h, cfg)}

<h2>Fortalezas y debilidades</h2>
<p class="tenue">Rutas, vehículos o tipos de carga donde su puntualidad se aparta 10 puntos o más de su propio promedio,
con al menos 5 servicios.</p>
{_detalle(h)}

<footer>Generado el {generado:%Y-%m-%d %H:%M} (hora Colombia). Fuente: historial de servicios de la base
(tabla <code>servicio</code>); los porcentajes mensuales no se ponderan.</footer>
</main></body></html>
"""
