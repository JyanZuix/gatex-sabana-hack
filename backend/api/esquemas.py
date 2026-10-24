"""Contrato JSON de la API (README, sección 5). Lo consumen la web y las gafas.

Si cambia una clave hay que actualizar el README y avisar a frontend y realidad aumentada.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.dominio import CargaEspecial

Valor = Union[int, float, str, None]


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Entradas ---------------------------------------------------------------

class SolicitudEntrada(_Esquema):
    """Lo que envía el frontend. `solicitud_id` lo asigna el backend.

    Toda carga va en contenedores de 20' (1 TEU cada uno). `peso_kg` es el peso de cada contenedor.
    `tipo_vehiculo_id`, si se envía, es obligatorio: solo se evalúan tarifas y flota de ese tipo.
    """
    cliente_id: str
    origen_id: str
    destino_id: str
    fecha_servicio: date
    plazo_h: float = Field(gt=0)
    n_contenedores: int = Field(ge=1)
    peso_kg: float = Field(gt=0)
    tipo_carga: Optional[CargaEspecial] = None
    tipo_vehiculo_id: Optional[str] = None
    presupuesto_cop: int = Field(gt=0)


class EscenarioEntrada(_Esquema):
    """Supuestos que cambia el funcionario. Nunca cambian el historial."""
    plazo_h: float = Field(gt=0)


class DecisionEntrada(_Esquema):
    solicitud_id: str
    proveedor_id: str
    justificacion: str = Field(min_length=1)
    escenario_id: Optional[str] = None   # si eligió mirando un escenario, el snapshot es ese

    @field_validator("justificacion")
    @classmethod
    def _no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La justificación no puede estar vacía")
        return v.strip()


# --- Evaluación -------------------------------------------------------------

class RutaSalida(_Esquema):
    ruta_id: str
    origen: str
    destino: str
    distancia_km: float


class Vehiculos(_Esquema):
    tipo_vehiculo_id: str                  # clave del catálogo (`tractomula`)
    tipo: str
    cantidad: int
    contenedores_por_vehiculo: list[int]   # se llena un vehículo antes del siguiente: 3 en 2 por vehículo → [2, 1]


class Profit(_Esquema):
    cop: int                              # presupuesto − costo del proveedor
    margen_pct: Optional[float]


class TiempoH(_Esquema):
    p50: float
    p90: float
    prob_a_tiempo: float
    abanico: dict[str, float]            # percentil → horas, para el gráfico
    resumen: str                         # frase llana: tiempo habitual, día malo, plazo y probabilidad


class CapacidadSalida(_Esquema):
    vehiculos_necesarios: int
    vehiculos_libres: int                # unidades libres esta semana del tipo elegido
    servicios_libres_dia: Optional[int]  # servicios que acepta en la fecha; null = sin dato (no descarta)
    texto: str


class HistorialSalida(_Esquema):
    servicios: int                       # servicios reales en su historial (sin ponderar)
    servicios_con_cliente: int


class DesgloseDesempeno(_Esquema):
    puntualidad: float
    magnitud_retraso: float


class DesempenoSalida(_Esquema):
    valor: float
    desglose: DesgloseDesempeno
    texto: str


class DesgloseConfianza(_Esquema):
    consistencia: float
    cumplimiento_cliente: float
    evidencia: float


class ConfianzaSalida(_Esquema):
    valor: float
    nivel: Literal["Alta", "Media", "Baja"]
    desglose: DesgloseConfianza
    texto: str


class DesglosePuntaje(_Esquema):
    """Puntos que aporta cada factor; suman `PuntajeSalida.valor`."""
    profit: float
    a_tiempo: float
    desempeno: float
    confianza: float


class PuntajeSalida(_Esquema):
    valor: float                          # 0-100; ordena a los candidatos
    desglose: DesglosePuntaje


class CandidatoSalida(_Esquema):
    proveedor_id: str
    nombre: str
    puesto: int                           # 1 = mayor puntaje; `candidatos` llega en este orden
    top: bool                             # entre los `puntaje.top_n` sugeridos
    puntaje: PuntajeSalida
    vehiculos: Vehiculos
    costo_cop: int
    profit: Profit
    tiempo_h: TiempoH
    capacidad: CapacidadSalida
    historial: HistorialSalida
    desempeno: DesempenoSalida
    confianza: ConfianzaSalida
    fortalezas: list[str]                # máx. `ficha.max_en_tarjeta`; primero las de esta ruta, vehículo o carga
    debilidades: list[str]
    riesgos: list[str]
    explicacion: str
    avisos: list[str] = []


class RazonSalida(_Esquema):
    codigo: str
    mensaje: str
    requerido: Valor
    disponible: Valor


class CanceladoSalida(_Esquema):
    proveedor_id: str
    nombre: str
    razones: list[RazonSalida]


class CondicionSalida(_Esquema):
    razon: RazonSalida
    flexibilizar: str


class CasiElegibleSalida(_Esquema):
    """Solo cuando no hay candidatos: los que fallan el menor número de condiciones (siempre hay al menos uno)."""
    proveedor_id: str
    nombre: str
    puesto: int                            # 1 = la opción viable con condición que se muestra primero
    recomendada: bool                      # true solo para el puesto 1
    razon: RazonSalida                     # primera condición (compatibilidad); todas en `condiciones`
    flexibilizar: str
    condiciones: list[CondicionSalida]
    vehiculos: Optional[Vehiculos] = None  # lo que tendría que pedirle si se flexibiliza; null si no tiene tarifa


class PesosPuntaje(_Esquema):
    profit: float
    a_tiempo: float
    desempeno: float
    confianza: float
    top_n: int


class ParametrosEscenario(_Esquema):
    plazo_h: float
    pesos_puntaje: PesosPuntaje
    semilla: int
    n_simulaciones: int


class Evaluacion(_Esquema):
    solicitud_id: str
    escenario_id: Optional[str] = None
    ruta: RutaSalida
    candidatos: list[CandidatoSalida]
    cancelados: list[CanceladoSalida]
    casi_elegibles: list[CasiElegibleSalida] = []
    sin_candidatos: bool
    parametros_escenario: ParametrosEscenario


# --- Decisiones -------------------------------------------------------------

class Decision(_Esquema):
    decision_id: str
    solicitud_id: str
    escenario_id: Optional[str]
    proveedor_id: str
    nombre: str
    tipo_vehiculo_id: str                # vehículo con el que se registró la solicitud en la base
    flexibilizado: bool                  # eligió un "casi elegible"
    justificacion: str
    fecha_hora: datetime
    snapshot: Evaluacion                 # exactamente lo que vio el funcionario


# --- Cierre del viaje (resultado real → transporte.servicio) -----------------

Incidente = Literal["ninguno", "retraso", "dano", "robo", "varado", "documental"]


class CierreEntrada(_Esquema):
    """Resultado real de un viaje ya decidido. Alimenta el historial con el que se calculan D y C."""
    fecha_entrega_real: datetime            # hora local de Colombia si no trae zona horaria
    proveedor_id: Optional[str] = None      # por defecto, el de la decisión registrada
    precio_cop: Optional[int] = Field(default=None, gt=0)   # por defecto, el costo de la opción elegida
    incidente: Optional[Incidente] = None   # por defecto `cierre.incidente_por_defecto`
    calificacion: Optional[int] = Field(default=None, ge=1, le=5)   # por defecto `cierre.calificacion_por_defecto`


class ServicioSalida(_Esquema):
    servicio_id: int
    solicitud_id: str
    proveedor_id: str
    nombre: str
    precio_cop: int
    fecha_servicio: date
    fecha_entrega_real: datetime
    transito_real_h: int
    plazo_h: float
    a_tiempo: bool
    incidente: str
    calificacion: int
    calificacion_por_defecto: bool          # true si no la enviaron y se guardó el valor neutro
    desempeno_antes: float                  # D del proveedor sin este viaje
    desempeno_despues: float                # D del proveedor con este viaje (el modelo ya lo usa)
    servicios_antes: int
    servicios_despues: int
    avisos: list[str] = []


# --- Catálogos (para llenar los desplegables del frontend y las gafas) ----------

class ClienteCatalogo(_Esquema):
    cliente_id: str
    nombre: str


class UbicacionCatalogo(_Esquema):
    ubicacion_id: str
    nombre: str
    tipo: str


class RutaCatalogo(_Esquema):
    ruta_id: str
    origen_id: str
    destino_id: str
    distancia_km: float


class TipoVehiculoCatalogo(_Esquema):
    tipo_vehiculo_id: str
    nombre: str
    cap_teu: int                         # contenedores de 20' por vehículo; 0 = no lleva contenedores
    cap_kg: float
    carga_especial: Optional[CargaEspecial]


class TipoCargaCatalogo(_Esquema):
    tipo_carga: Optional[CargaEspecial]  # null = carga general
    nombre: str


class Catalogos(_Esquema):
    clientes: list[ClienteCatalogo]
    ubicaciones: list[UbicacionCatalogo]
    rutas: list[RutaCatalogo]
    tipos_vehiculo: list[TipoVehiculoCatalogo]
    tipos_carga: list[TipoCargaCatalogo]


# --- Ficha de proveedor -------------------------------------------------------

class PuntoTendencia(_Esquema):
    mes: str                             # AAAA-MM
    servicios: int
    a_tiempo_pct: float                  # % de esos servicios entregados a tiempo (sin ponderar)
    nivel: Literal["alto", "medio", "bajo"]  # color para la tabla mes a mes (umbrales en parametros.yaml)
    desempeno: float


class FichaProveedor(_Esquema):
    proveedor_id: str
    nombre: str
    estado: str
    cargas_especiales: list[str]
    servicios: int
    ultimo_servicio: Optional[date]
    puntualidad_pct: Optional[float]
    desempeno: DesempenoSalida
    confianza: ConfianzaSalida
    tendencia: list[PuntoTendencia]
    fortalezas: list[str]
    debilidades: list[str]


class HistorialProveedores(_Esquema):
    """Track record de todos los proveedores, mes a mes (GET /historial/proveedores)."""
    generado: date
    meses: list[str]                     # AAAA-MM con al menos un servicio de algún proveedor, en orden
    proveedores: list[FichaProveedor]    # de mayor a menor desempeño; sin historial al final

# --- Catálogos de solo lectura para frontend / Quest ---------------------------
class OpcionCatalogo(_Esquema):
    id: Optional[str]
    nombre: str

class RutaCobertura(_Esquema):
    ruta_id: str
    origen_id: str
    destino_id: str

class ProveedorCatalogo(_Esquema):
    proveedor_id: str
    nombre: str
    estado: str

class CatalogosSalida(_Esquema):
    repositorio: str
    origenes: list[OpcionCatalogo]
    destinos: list[OpcionCatalogo]
    rutas: list[RutaCobertura]
    clientes: list[OpcionCatalogo]
    tipos_carga: list[OpcionCatalogo]
    tipos_vehiculo: list[OpcionCatalogo]
    proveedores: list[ProveedorCatalogo]
    fecha_servicio: Optional[date]
    nota: str
