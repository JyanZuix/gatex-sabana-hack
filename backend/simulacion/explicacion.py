"""Explicación en lenguaje natural: los factores que más suben y más bajan cada opción.

Cada opción se compara con el promedio de las DEMÁS opciones. Si es la única,
se compara con un proveedor promedio del mercado. Cada factor guarda su valor y su
referencia, para que todo texto sea trazable a los datos (regla 3 del README).
Los textos usan lenguaje llano: nada de "referencia" ni de "servicios efectivos".
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.calculos.confianza import Confianza
from backend.config import Config


@dataclass(frozen=True)
class ResumenOpcion:
    proveedor_id: str
    costo_cop: int
    prob_a_tiempo: float
    desempeno: float
    confianza: float
    servicios_con_cliente: int     # servicios reales con este cliente (sin ponderar)


@dataclass(frozen=True)
class ReferenciaMercado:
    """Valores de un proveedor promedio, para comparar cuando hay una sola opción."""
    prob_a_tiempo: float
    desempeno: float
    confianza: float


@dataclass(frozen=True)
class Factor:
    clave: str
    valor: float
    referencia: float
    impacto: float      # > 0 favorece la opción, < 0 la perjudica
    texto: str


@dataclass(frozen=True)
class Explicacion:
    a_favor: tuple[Factor, ...]
    en_contra: tuple[Factor, ...]

    @property
    def texto(self) -> str:
        partes = [f.texto for f in self.a_favor + self.en_contra]
        return ("; ".join(partes) + ".") if partes else "Sin diferencias relevantes frente a las demás opciones."


def _pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def _cop(x: float) -> str:
    return "$" + f"{x:,.0f}".replace(",", ".")


def _factores(o: ResumenOpcion, otras: list[ResumenOpcion], ref: ReferenciaMercado, k: float) -> list[Factor]:
    def media(attr: str, por_defecto: float) -> float:
        return sum(getattr(x, attr) for x in otras) / len(otras) if otras else por_defecto

    factores = []
    if otras:
        minimo = min(x.costo_cop for x in otras)
        impacto = (minimo - o.costo_cop) / minimo
        if o.costo_cop <= minimo:
            texto = f"Opción más económica ({_cop(o.costo_cop)}, {_pct(impacto)} menos que la siguiente)"
        else:
            texto = f"Costo {_pct(-impacto)} mayor que la opción más económica ({_cop(o.costo_cop)} frente a {_cop(minimo)})"
        factores.append(Factor("costo_cop", o.costo_cop, minimo, impacto, texto))

    frente = "los otros candidatos, {} en promedio" if otras else "un proveedor promedio de la ruta, {}"

    r = media("prob_a_tiempo", ref.prob_a_tiempo)
    factores.append(Factor("prob_a_tiempo", o.prob_a_tiempo, r, o.prob_a_tiempo - r,
                           f"Llega a tiempo en el {_pct(o.prob_a_tiempo)} de las simulaciones ({frente.format(_pct(r))})"))
    r = media("desempeno", ref.desempeno)
    factores.append(Factor("desempeno", o.desempeno, r, (o.desempeno - r) / 100,
                           f"Desempeño de {o.desempeno:.0f}/100 ({frente.format(f'{r:.0f}')})"))
    r = media("confianza", ref.confianza)
    factores.append(Factor("confianza", o.confianza, r, (o.confianza - r) / 100,
                           f"Confianza en sus datos de {o.confianza:.0f}/100 ({frente.format(f'{r:.0f}')})"))
    if otras:  # sin otras opciones no hay con quién comparar el historial con el cliente
        r = media("servicios_con_cliente", 0.0)
        n = o.servicios_con_cliente
        if n == 0:
            texto = f"Nunca ha trabajado con este cliente (los otros candidatos, {r:.0f} servicios en promedio)"
        else:
            texto = f"Ha hecho {_servicios(n)} para este cliente (los otros candidatos, {r:.0f} en promedio)"
        factores.append(Factor("servicios_con_cliente", n, r, (n - r) / (n + r + k), texto))
    return factores


def _servicios(n: int) -> str:
    return "1 servicio" if n == 1 else f"{n} servicios"


def explicar(opciones: list[ResumenOpcion], referencia: ReferenciaMercado, cfg: Config) -> dict[str, Explicacion]:
    """Explicación por proveedor_id. No ordena ni elige: solo describe cada opción."""
    n = cfg.explicacion.max_factores
    umbral = cfg.explicacion.umbral_impacto
    resultado = {}
    for o in opciones:
        otras = [x for x in opciones if x.proveedor_id != o.proveedor_id]
        fs = _factores(o, otras, referencia, cfg.confianza.k_evidencia)
        a_favor = sorted((f for f in fs if f.impacto > umbral), key=lambda f: -f.impacto)[:n]
        en_contra = sorted((f for f in fs if f.impacto < -umbral), key=lambda f: f.impacto)[:n]
        resultado[o.proveedor_id] = Explicacion(tuple(a_favor), tuple(en_contra))
    return resultado


def describir_consistencia(valor: float, cfg: Config) -> str:
    """Palabras para la consistencia de tiempos S_desv (umbrales en `textos` de parametros.yaml)."""
    t = cfg.textos
    if valor >= t.consistencia_estable:
        return "tiempos estables"
    if valor >= t.consistencia_variable:
        return "tiempos algo variables"
    return "tiempos muy variables"


def riesgos(n_servicios: int, conf: Confianza, servicios_con_cliente: int, prob_a_tiempo: float,
            cfg: Config) -> list[str]:
    """Riesgos visibles en la tarjeta, cada uno con el dato que lo causa.

    "Pocos datos" se decide con la evidencia ponderada (`n_efectivo`, la misma de la Confianza),
    pero se informa con el conteo real de servicios, que es lo que cualquiera entiende.
    """
    lista = []
    pocos = conf.n_efectivo < cfg.confianza.k_evidencia
    if pocos:
        lista.append(f"Pocos datos: {_servicios(n_servicios)} en su historial")
    if servicios_con_cliente == 0:
        lista.append("Nunca ha trabajado con este cliente")
    if prob_a_tiempo < cfg.riesgo.min_a_tiempo:
        lista.append(f"Llega a tiempo solo en el {_pct(prob_a_tiempo)} de las simulaciones "
                     f"(se espera al menos {_pct(cfg.riesgo.min_a_tiempo)})")
    if conf.nivel == "Baja":
        causas = (["pocos datos"] if pocos else []) + [describir_consistencia(conf.consistencia, cfg)]
        lista.append(f"Confianza baja ({conf.valor:.0f}/100): {' y '.join(causas)}")
    return lista
