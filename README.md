# Sala de Simulación de Proveedores · COSCO SHIPPING Colombia
### Sabana Hack 2026 · Sistema de apoyo a la decisión para transporte terrestre

> **Para todos los agentes de IA (Claude Code y otros): lean este archivo COMPLETO antes de escribir código, proponer cambios o responder preguntas.** Aquí está qué construimos, por qué, cómo funciona el flujo de filtrado y simulación, y las reglas que no se negocian. Si una tarea contradice este documento, **deténganse y pregunten al equipo**.
>
> Documentos complementarios, que también son obligatorios:
> - `docs/calculos_simulacion.md`: especificación exacta de los cálculos y la simulación.
> - `docs/decisiones.md`: registro fechado de decisiones y supuestos.
> - `PLAN.md`: plan de implementación y checklist de avance (aún por redactar y aprobar).
> - `docs/README.md`: índice de la documentación.

---

## 1. ¿Qué es este sistema?

Una **sala de simulación virtual** que **acompaña** al funcionario de COSCO SHIPPING cuando decide **qué proveedor de transporte terrestre** atiende una solicitud de envío **dentro de Colombia**.

El sistema:
1. Guarda en una **base de datos** el **historial** de cada proveedor y sus **condiciones actuales**: tarifas fijas por **ruta** y **tipo de vehículo**, flota disponible y cobertura.
2. Cuando entra una solicitud de A a B, **filtra** a los proveedores que no cumplen los requisitos mínimos y deja a cada descartado con **sus razones**.
3. Para los que quedan, **calcula y simula** qué pasaría si el funcionario eligiera a cada uno:
   - **Confianza** en el proveedor (0–100);
   - **Desempeño** del proveedor (0–100);
   - **Tiempo de entrega estimado**, con su incertidumbre;
   - **Profit final para COSCO SHIPPING**;
   - **Cuántos vehículos y qué tipo de vehículo** hay que pedirle al proveedor para cumplir el envío.
   - **Debilidades y Fortalezas** históricas de ese proveedor en específico.
4. Muestra todo en un **display de realidad aumentada (gafas)** y en una **interfaz web de respaldo**. Allí el funcionario compara las consecuencias económicas, de tiempo y de confianza de cada opción.
5. **El funcionario toma la decisión final.** El sistema la registra con su justificación.

> **Principio rector: el sistema acompaña, no decide.** Nunca seleccionamos automáticamente un proveedor ni presentamos un "ganador" impuesto. Mostramos opciones viables, sus consecuencias simuladas y sus explicaciones. Mensajes como "El sistema asignó al proveedor X" están **prohibidos**.

---

## 2. Contexto del negocio (resumen)

- COSCO SHIPPING ofrece en Colombia **transporte terrestre** (*inland trucking*) entre puertos y bodegas o plantas de clientes, en ambos sentidos.
- **No opera camiones propios:** contrata a **más de 10 proveedores locales** con precios, tiempos, vehículos, capacidad y desempeño distintos.
- Hoy la elección es **manual, lenta, inconsistente y difícil de explicar**.
- El reto pide un sistema **rápido, consistente, explicable y basado en datos** que considere **7 factores**:
  1. precio;
  2. tiempo de tránsito;
  3. disponibilidad del tipo de vehículo;
  4. capacidad disponible;
  5. desempeño histórico;
  6. confiabilidad o entregas a tiempo;
  7. fortalezas y debilidades específicas.
- **Contexto Colombia:** bloqueos y cierres de vías frecuentes. Colfecar reporta más de 2.000 bloqueos desde 2023. Por eso importan las **condiciones actuales**, no solo el historial.

### Glosario
| Término | Significado |
|---|---|
| **Solicitud (request)** | Pedido para mover una carga de un origen A a un destino B, con tipo de carga, cantidad, vehículo requerido y plazo |
| **Ruta** | Trayecto **dirigido** A→B con **distancia fija** (A→B ≠ B→A) |
| **Tarifa** | Precio **fijo por viaje** que cobra un proveedor por una ruta con un tipo de vehículo. **No cambia** en este modelo |
| **Candidato** | Proveedor que **sigue siendo elegible** para la solicitud |
| **Cancelado** | Proveedor **descartado** por incumplir al menos un requisito mínimo; guarda **la lista completa** de razones |
| **Desempeño (D)** | Qué tan bien ha cumplido el proveedor (dominado por la puntualidad) |
| **Confianza (C)** | Cuánto le creemos al proveedor **para este cliente**: consistencia de tiempos, incidentes, cantidad y recencia del historial |
| **Profit** | Lo que le sobra a COSCO del presupuesto disponible para el envío = presupuesto − costo pagado al proveedor − costo esperado de retraso |
| **Presupuesto disponible** | Dinero con que cuenta COSCO antes de contratar el transporte terrestre de esta solicitud |

---

## 3. Flujo completo del sistema

```
 ┌───────────────┐   1. Solicitud A→B, carga, plazo, vehículo
 │  Funcionario  │──────────────────────────────────────────────┐
 └───────────────┘                                              ▼
                                                    ┌─────────────────────┐
                                                    │  Backend (API)      │
                                                    └─────────┬───────────┘
              2. Consulta proveedores con datos de la ruta A→B│
                                                              ▼
                                                    ┌─────────────────────┐
                                                    │  Base de datos      │
                                                    │  historial + tarifas│
                                                    │  + condiciones hoy  │
                                                    └─────────┬───────────┘
                                                              ▼
                              3. FILTRO de requisitos mínimos
                     ┌────────────────────────┴─────────────────────────┐
                     ▼                                                  ▼
            ┌─────────────────┐                              ┌────────────────────┐
            │   CANDIDATOS    │                              │    CANCELADOS      │
            │ (cumplen todo)  │                              │ + lista de razones │
            └────────┬────────┘                              └─────────┬──────────┘
                     ▼                                                 │
   4. CÁLCULOS + SIMULACIÓN por candidato                              │
   Confianza · Desempeño · Tiempo estimado ·                           │
   N.º de vehículos · Costo · Profit                                   │
                     ▼                                                 ▼
          ┌──────────────────────────────────────────────────────────────────┐
          │ 5. DISPLAY: gafas de realidad aumentada + web de respaldo         │
          │   · Elegibles: comparación de consecuencias simuladas            │
          │   · Descartados: quién y POR QUÉ                                 │
          └──────────────────────────────┬───────────────────────────────────┘
                                         ▼
                         6. El FUNCIONARIO decide → se registra la decisión
```

### 3.1 Paso 2: consulta a la base de datos
La base de datos es **PostgreSQL** (la construye el subequipo de BD). Mientras no esté lista, el backend usa un adaptador simulado.
El backend trae **todos los proveedores activos** con lo relacionado a la ruta A→B de la solicitud:
- tarifas vigentes por tipo de vehículo;
- flota disponible;
- cobertura;
- tiempo prometido;
- historial de servicios (para calcular D y C);
- condiciones actuales del corredor.

### 3.2 Paso 3: filtro (Candidatos → Cancelados)

> **La capacidad decide cuántos vehículos reservar.** Se compara lo que pide la solicitud (número de contenedores y peso) con la capacidad de cada tipo de vehículo del proveedor (`cap_teu`, `cap_toneladas`) y con las unidades disponibles. Así se valida que el requerimiento sea compatible con los recursos del proveedor. Ver 3.3 y `docs/calculos_simulacion.md`, sección 5.3.

Todos los proveedores empiezan en la lista **Candidatos**. Se evalúan **TODAS** las reglas sobre cada uno, sin detenerse en la primera falla, para que el funcionario vea **todas** las razones de descarte. Si un proveedor incumple **al menos una** regla, pasa a **Cancelados** con su lista de razones.

| Código | Regla (incumple si…) | Mensaje para el funcionario (ejemplo) |
|---|---|---|
| `SIN_COBERTURA` | No cubre la ruta A→B en el territorio | "No opera el trayecto Buenaventura → Bogotá" |
| `SIN_TARIFA` | No tiene tarifa vigente para la ruta y un tipo de vehículo válido | "Sin tarifa vigente para esta ruta" |
| `VEHICULO_NO_DISPONIBLE` | No tiene el tipo de vehículo que exige la carga | "No tiene cama baja (requerida para sobredimensionado)" |
| `VEHICULOS_INSUFICIENTES` | Unidades disponibles < vehículos necesarios | "Necesita 3 tractocamiones, solo tiene 1 disponible" |
| `SIN_CAPACIDAD` | No tiene capacidad de servicio en la fecha | "Capacidad agotada para el 28-oct" |
| `PLAZO_INCUMPLIBLE` | Su tiempo prometido no alcanza a cumplir el plazo de la solicitud | "Tránsito pactado 52 h; plazo disponible 40 h" |
| `CARGA_NO_SOPORTADA` | No maneja el tipo de carga (refrigerada, peligrosa, etc.) | "No transporta carga peligrosa" |
| `PROVEEDOR_INACTIVO` | Suspendido, sin documentación vigente o inactivo | "Póliza vencida desde el 15-oct" |

- Cada razón se guarda con su **código**, el **mensaje legible** y el **dato que la causó** (valor requerido frente a valor del proveedor).
- Las reglas viven en un **módulo propio y configurable** (`backend/filtro/`). Agregar una regla nueva no debe obligar a tocar la simulación.
- **Si quedan 0 candidatos:** no se devuelve una pantalla vacía. Se informa la situación y se muestran los cancelados que fallan **una sola regla**, como "casi elegibles", marcando qué habría que flexibilizar. **La decisión de flexibilizar es del funcionario.**

### 3.3 Paso 4: cálculos por candidato
Las fórmulas exactas están en `docs/calculos_simulacion.md`. Este es el resumen:

| Resultado | Cómo se obtiene |
|---|---|
| **N.º de vehículos** | `vehículos = max( ceil(TEU / cap_teu), ceil(toneladas / cap_ton) )` por tipo de vehículo válido; se usa el tipo **más económico** que cumple |
| **Costo para COSCO** | `vehículos × precio_viaje(proveedor, ruta, tipo_vehículo)`; la tarifa es **fija** |
| **Tiempo estimado** | Simulación Monte Carlo (N = 2000, semilla fija) con el historial de desviaciones del proveedor + condiciones actuales del corredor → tiempo típico (P50), mal escenario (P90) y **probabilidad de llegar a tiempo** |
| **Desempeño D** | `100·[0.75·Puntualidad + 0.25·(1 − Magnitud de retraso)]`, con suavizado bayesiano y recencia (vida media de 12 meses) |
| **Confianza C** | `100 · Q · F`: Q = 40 % consistencia de tiempos + 40 % incidentes + 20 % cumplimiento con este cliente; F = evidencia (cantidad de servicios y peso extra al historial con este cliente) |
| **Profit COSCO** | `Profit = Presupuesto_disponible − Costo_proveedor − Costo_esperado_retraso` (ver 3.4) |

### 3.4 Profit para COSCO SHIPPING
```
Presupuesto_disponible  = dinero disponible en COSCO antes del envío terrestre (dato de la solicitud)
Costo_proveedor         = vehículos × precio_viaje
Costo_esperado_retraso  = Σ_simulaciones [ penal_hora × max(0, T_sim − plazo) ] / N
Profit                  = Presupuesto_disponible − Costo_proveedor − Costo_esperado_retraso
Margen %                = Profit / Presupuesto_disponible
```
- Se muestran el **profit esperado** y el **profit en un mal escenario** (P10).
- **Decisión (2026-10-23):** COSCO no tiene una tarifa al cliente. El "ingreso" es el **presupuesto disponible** antes del envío; lo que sobra tras pagar al proveedor y el retraso esperado es el profit. La solicitud lo recibe como campo de entrada (`presupuesto_cop`). Si el costo supera el presupuesto, el profit es negativo y se muestra así. **Por confirmar con negocio.** No inventen valores.
- `penal_hora` (costo por hora de retraso) es un **parámetro del escenario**. Vale 0 por defecto y el funcionario lo puede ajustar.

### 3.5 Paso 5: qué ve el funcionario
**Sección "Elegibles" (candidatos):** una tarjeta por proveedor con:
- **Económico:** costo, profit esperado, profit en mal escenario y margen.
- **Tiempo:** P50 y P90, probabilidad de llegar a tiempo y el **abanico** de resultados simulados.
- **Confianza y desempeño:** valor de 0 a 100, etiqueta (Alta, Media o Baja) y **desglose** de cada componente.
- **Logística:** tipo de vehículo y **número de vehículos** a pedir.
- **Explicación en lenguaje natural:** los 2–3 factores que más suben y más bajan a esta opción.

Además:
- El funcionario puede **ordenar** las opciones por el criterio que prefiera (profit, tiempo, confianza) y correr **escenarios "¿y si…?"**, por ejemplo un bloqueo en el corredor o un plazo distinto. Estos escenarios cambian supuestos, nunca los datos históricos.

**Sección "Descartados" (cancelados), obligatoria:** lista de proveedores descartados con **todas** sus razones y el dato que causó cada una. Sirve para transparencia y auditoría.

**Botón "Elegir proveedor":** pide la confirmación y una justificación breve, y guarda la decisión junto con un **snapshot** de todo lo que se mostró.

### 3.6 Display en gafas de realidad aumentada
- Las gafas son la **interfaz principal de la demo**: tarjetas comparables flotantes, un mapa de la ruta A→B con el corredor y sus riesgos, el abanico de tiempos simulados y el panel de descartados.
- Las gafas **consumen la misma API** que la web. **Nada de lógica de negocio en el cliente de realidad aumentada.**
- **La web de respaldo debe tener las mismas funciones.** Si las gafas fallan en la demo, la web la salva.
- *(Opcional)* El robot humanoide AgiBot X2 puede narrar las opciones y los riesgos (vía ROS 2 + TTS) consumiendo la misma API. **Nunca decide.**

---

### 3.7 Identificadores
- **`solicitud_id`:** consecutivo generado por el **backend** (secuencia), no por el frontend. Se muestra como `REQ-0042`.
- **`cliente_id`:** identificador propio de cada cliente en el catálogo `clientes`, para registrar bien sus pedidos y calcular el historial con ese cliente.

---

## 4. Modelo de datos (resumen)

La base de datos la construye un subequipo propio. Estas son las entidades que el resto del sistema espera encontrar:

| Capa | Tablas |
|---|---|
| **Catálogos** | `proveedores`, `clientes`, `ubicaciones`, `rutas` (dirigidas, `distancia_km` fija), `tipos_vehiculo` (cap. TEU, toneladas, m³, carga especial) |
| **Condiciones actuales** (versionadas con fecha) | `tarifas` (proveedor + ruta + tipo_vehiculo → `precio_viaje`, `tiempo_prometido_h`, vigencia), `vehiculos_proveedor` (unidades disponibles), `cobertura_proveedor`, `capacidad_actual`, `condiciones_via` (por corredor) |
| **Historial** (inmutable) | `servicios_historicos` (tiempos prometido y real, plazo, a tiempo, cliente, ruta, vehículo), `incidentes` (severidad 0.3 / 0.6 / 1.0) |
| **Operación del sistema** | `solicitudes`, `evaluaciones` (candidatos y cancelados con sus razones), `simulaciones` (resultados por candidato), `decisiones` (elección, justificación y snapshot) |

> El detalle de campos que necesita el módulo de cálculo está en `docs/calculos_simulacion.md`, secciones 5.2 y 7.

---

## 5. Contrato de la API (base; mantener estable: lo consumen web y gafas)

`POST /solicitudes/evaluar`: recibe la solicitud y devuelve candidatos simulados y cancelados.
```json
{
  "solicitud_id": "REQ-0042",
  "ruta": {"origen": "Buenaventura", "destino": "Bogotá", "distancia_km": 515},
  "candidatos": [
    {
      "proveedor_id": "PROV-03",
      "nombre": "Transportes Andinos",
      "vehiculos": {"tipo": "Tractocamión 40'", "cantidad": 2},
      "costo_cop": 9800000,
      "profit": {"esperado_cop": 3100000, "p10_cop": 2600000, "margen_pct": 24.0},
      "tiempo_h": {"p50": 26.5, "p90": 34.0, "prob_a_tiempo": 0.87},
      "desempeno": {"valor": 89.4, "desglose": {"puntualidad": 0.887, "magnitud_retraso": 0.085}},
      "confianza": {"valor": 73.7, "nivel": "Media",
                    "desglose": {"consistencia": 0.672, "incidentes": 0.950, "cumplimiento_cliente": 0.882, "evidencia": 0.893}},
      "riesgos": ["Corredor con 15% de probabilidad de bloqueo esta semana"],
      "explicacion": "Alta puntualidad y amplio historial con este cliente; costo 6% mayor que la opción más económica."
    }
  ],
  "cancelados": [
    {
      "proveedor_id": "PROV-07",
      "nombre": "Carga Express",
      "razones": [
        {"codigo": "VEHICULOS_INSUFICIENTES", "mensaje": "Necesita 2 tractocamiones, tiene 1", "requerido": 2, "disponible": 1},
        {"codigo": "PLAZO_INCUMPLIBLE", "mensaje": "Tránsito pactado 52 h; plazo 40 h", "requerido": 40, "disponible": 52}
      ]
    }
  ],
  "sin_candidatos": false,
  "parametros_escenario": {"penal_hora_cop": 0, "semilla": 42, "n_simulaciones": 2000}
}
```
- `POST /solicitudes/{id}/escenario`: vuelve a simular con otros supuestos.
- `POST /decisiones`: registra la elección, la justificación y el snapshot.
- `GET /proveedores/{id}`: ficha con historial, tendencias, fortalezas y debilidades.
- `GET /tableros/...`: datos para los tableros de precios, tiempos, capacidad, vehículos y tendencias.

> Si se cambia el contrato, **hay que actualizar este README** y avisar al equipo de frontend y de realidad aumentada.

---

## 6. Estructura del repositorio (propuesta)

```
/
├── README.md                 ← este archivo
├── PLAN.md                   ← plan de implementación + checklist (por redactar; lo mantiene Claude Code)
├── docs/
│   ├── README.md             ← índice de la documentación
│   ├── calculos_simulacion.md
│   ├── decisiones.md
│   ├── concepto_sala_decisiones.md   (pendiente)
│   └── valor_negocio.md              (pendiente)
├── database/                 ← (aún no creada) subequipo BD: esquema, migraciones, datos semilla
├── backend/                  ← en construcción
│   ├── filtro/               ← reglas de descarte (Candidatos → Cancelados)
│   ├── calculos/             ← desempeño, confianza, costos, profit, vehículos
│   ├── simulacion/           ← Monte Carlo y escenarios
│   ├── api/                  ← endpoints
│   ├── config/               ← parámetros (pesos, vida media, N, semilla…)
│   ├── datos/                ← interfaz Repositorio + adaptadores (simulado, PostgreSQL)
│   ├── datos_sinteticos/     ← datos de prueba SINTÉTICOS etiquetados y su generador
│   └── tests/
├── frontend_web/             ← (aún no creada) web de respaldo: elegibles, descartados, tableros
├── ar_display/               ← (aún no creada) cliente de las gafas; el prototipo WebXR vive hoy en la raíz
└── demo/                     ← (aún no creada) solicitudes de prueba y guion de la demostración

En la raíz también están `index.html`, `js/`, `assets/` y `LEEME.md`: prototipo WebXR para Meta Quest 3.
```

---

## 7. Reglas para agentes de IA

1. **Nunca decidir por el funcionario.** Siempre opciones, consecuencias, explicación y confirmación humana.
2. **Toda razón de descarte debe ser visible.** Evaluar todas las reglas, no solo la primera que falle.
3. **Ningún número sin explicación.** Cada valor de D, C, tiempo, costo y profit debe poder desglosarse y rastrearse hasta los datos.
4. **No inventar datos.** Si falta un dato, márquenlo y muestren cómo afecta la confianza. Los datos sintéticos de prueba van **etiquetados** como tales, por ahora en `backend/datos_sinteticos/`.
5. **Las tarifas son fijas.** No modelen variación de precios de los proveedores.
6. **Los parámetros van en `backend/config/`, no en el código** (pesos, vida media de 365 días, N = 2000, semilla, escala de severidad).
7. **Resultados reproducibles:** misma solicitud + misma semilla = mismos resultados.
8. **El contrato de la API es sagrado:** lo usan la web y las gafas. Cambios = actualizar este README.
9. **Prioridad de construcción:** (1) flujo de principio a fin con datos reales → (2) explicaciones y descartados → (3) tableros → (4) realidad aumentada → (5) extras (robot).
10. **Confidencialidad:** los datos de COSCO solo se usan para este reto. No los envíen a servicios externos ni los suban a repositorios públicos.
11. **Interfaz en español.** Código y comentarios en español o inglés técnico.
12. **Actualizar `PLAN.md`** al terminar cada tarea, marcando el checklist.

---

## 8. Cómo nos evalúan (100 puntos) y cómo respondemos

| Criterio | Pts | Nuestra respuesta |
|---|---|---|
| Comprensión del problema | 15 | Los 7 factores, las tensiones entre ellos y el contexto colombiano (bloqueos, cobertura) |
| Calidad de la recomendación | 20 | El filtro garantiza que todo candidato cumple los requisitos; los "casi elegibles" cubren los casos sin opción ideal |
| Metodología y transparencia | 20 | Fórmulas documentadas, desglose por componente y razones de descarte visibles |
| Funcionamiento y demostración | 20 | Flujo de principio a fin con datos históricos y de prueba en varios casos distintos |
| Análisis y visualización | 10 | Tarjetas comparables, abanico de simulación, ficha por proveedor y tableros |
| Valor de negocio y viabilidad | 10 | Profit por decisión, tiempo ahorrado al funcionario y plan de implementación |
| Comunicación | 5 | Demo en realidad aumentada con la web de respaldo y una historia clara |

**Validación (backtesting):** se reviven solicitudes históricas con las condiciones de ese día. Se revisa: ¿el proveedor elegido por COSCO estaba entre los candidatos? ¿la simulación predijo bien el tiempo y la puntualidad reales?

---

## 9. Decisiones y preguntas abiertas
El registro completo y fechado está en `docs/decisiones.md`.

**Resueltas**
- [x] **Stack:** Python 3.10 + FastAPI + pandas/numpy; web de respaldo en HTML y JS plano con Chart.js.
- [x] **Base de datos:** PostgreSQL.
- [x] **Gafas:** Meta Quest 3, con Three.js y WebXR.
- [x] **Origen del "ingreso" para el profit:** presupuesto disponible de COSCO antes del envío (ver 3.4). Confirmado.
- [x] **Viajes en varias tandas:** se descartan por defecto (configurable).
- [x] **Identificadores:** `solicitud_id` consecutivo del backend y `cliente_id` propio (ver 3.7).

**Pendientes** (se resuelven al poder leer la base de datos del subequipo)
- [ ] ¿Cómo viene representada la **cobertura** de cada proveedor en los datos?
- [ ] ¿Qué **tipos de vehículo y de carga** existen en los datos del reto?
- [ ] ¿Cuál es el esquema real de la base de datos y cómo se conecta el backend?
- [ ] Campos definitivos de la solicitud, una vez conectados backend, frontend, gafas y base de datos.
