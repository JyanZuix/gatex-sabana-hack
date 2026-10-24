"""Explicación en lenguaje natural: los factores que más suben y más bajan cada opción.

Cada opción se compara con el promedio de las DEMÁS opciones. Si es la única,
se compara con la referencia del mercado. Cada factor guarda su valor y su
referencia, para que todo texto sea trazable a los datos (regla 3 del README).
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.config import Config


@dataclass(frozen=True)
class ResumenOpcion:
    proveedor_id: str
    costo_cop: int
    prob_a_tiempo: float
    desempeno: float
    confianza: float
    servicios_con_cliente: float   # W_c


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

    r = media("prob_a_tiempo", ref.prob_a_tiempo)
    factores.append(Factor("prob_a_tiempo", o.prob_a_tiempo, r, o.prob_a_tiempo - r,
                           f"Probabilidad de llegar a tiempo de {_pct(o.prob_a_tiempo)} (referencia {_pct(r)})"))
    r = media("desempeno", ref.desempeno)
    factores.append(Factor("desempeno", o.desempeno, r, (o.desempeno - r) / 100,
                           f"Desempeño de {o.desempeno:.1f} (referencia {r:.1f})"))
    r = media("confianza", ref.confianza)
    factores.append(Factor("confianza", o.confianza, r, (o.confianza - r) / 100,
                           f"Confianza de {o.confianza:.1f} (referencia {r:.1f})"))
    r = media("servicios_con_cliente", 0.0)
    factores.append(Factor("servicios_con_cliente", o.servicios_con_cliente, r,
                           (o.servicios_con_cliente - r) / (o.servicios_con_cliente + r + k),
                           f"Historial con este cliente de {o.servicios_con_cliente:.1f} servicios efectivos (referencia {r:.1f})"))
    return factores


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


def riesgos(n_efectivo: float, servicios_con_cliente: float, cfg: Config) -> list[str]:
    """Riesgos visibles en la tarjeta: poca evidencia y falta de historial con el cliente."""
    lista = []
    if n_efectivo < cfg.confianza.k_evidencia:
        lista.append(f"Poca evidencia histórica ({n_efectivo:.1f} servicios efectivos)")
    if servicios_con_cliente == 0:
        lista.append("Sin historial con este cliente")
    return lista
