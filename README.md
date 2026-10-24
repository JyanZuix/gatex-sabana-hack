# Sala de Simulación de Proveedores · COSCO SHIPPING Colombia
### Sabana Hack 2026 · Sistema de apoyo a la decisión para transporte terrestre

> **Para todos los agentes de IA (Claude Code y otros): lean este archivo COMPLETO antes de escribir código, proponer cambios o responder preguntas.** Aquí está qué construimos, por qué, cómo funciona el flujo de filtrado y simulación, y las reglas que no se negocian. Si una tarea contradice este documento, **deténganse y pregunten al equipo**.
>
> Documentos complementarios, que también son obligatorios:
> - `docs/calculos_simulacion.md`: especificación exacta de los cálculos y la simulación.
> - `docs/decisiones.md`: registro fechado de decisiones y supuestos.
> - `PLAN.md`: plan de implementación y checklist de avance.
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

> **Principio rector: el sistema sugiere, el funcionario decide.** Nunca seleccionamos automáticamente un proveedor. Ordenamos las opciones viables con un **puntaje de fórmula pública** y sugerimos un **Top 4**, con sus consecuencias simuladas y sus explicaciones; el funcionario elige (puede ser fuera del Top 4) y justifica. Mensajes como "El sistema asignó al proveedor X" están **prohibidos**.

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

### Glosario
| Término | Significado |
|---|---|
| **Solicitud (request)** | Pedido para mover una carga de un origen A a un destino B, con tipo de carga, cantidad, vehículo requerido y plazo |
| **Ruta** | Trayecto **dirigido** A→B con **distancia fija** (A→B ≠ B→A) |
| **Tarifa** | Precio **fijo por viaje** que cobra un proveedor por una ruta con un tipo de vehículo. **No cambia** en este modelo |
| **Candidato** | Proveedor que **sigue siendo elegible** para la solicitud |
| **Cancelado** | Proveedor **descartado** por incumplir al menos un requisito mínimo; guarda **la lista completa** de razones |
| **Desempeño (D)** | Qué tan bien ha cumplido el proveedor (dominado por la puntualidad) |
| **Confianza (C)** | Cuánto le creemos al proveedor **para este cliente**: consistencia de tiempos, cumplimiento con el cliente, cantidad y recencia del historial |
| **Profit** | Lo que le sobra a COSCO del presupuesto disponible para el envío = presupuesto − costo pagado al proveedor |
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
                                                    │  + flota/capacidad  │
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
- capacidad de servicio en la fecha.

> **Decisión (2026-10-24):** los incidentes y las condiciones o bloqueos de vía **no forman parte del modelo**. No se simulan ni entran en la Confianza.

### 3.2 Paso 3: filtro (Candidatos → Cancelados)

> **La capacidad decide cuántos vehículos reservar.** Toda carga viaja en contenedores de 20' (1 TEU cada uno). Se compara lo que pide la solicitud (`n_contenedores` y `peso_kg` de cada contenedor) con la capacidad de cada tipo de vehículo (`cap_teu`, `cap_kg`, tabla `tipo_vehiculo`) y con las unidades disponibles del proveedor. Así se valida que el requerimiento sea compatible con los recursos del proveedor. Ver 3.3 y `docs/calculos_simulacion.md`, sección 5.3.

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
| `SIN_MARGEN` | Su opción más barata que cumple cuesta más que el presupuesto (daría pérdida) | "Costo $8.000.000 supera el presupuesto de $7.500.000" |

- Cada razón se guarda con su **código**, el **mensaje legible** y el **dato que la causó** (valor requerido frente a valor del proveedor).
- Las reglas viven en un **módulo propio y configurable** (`backend/filtro/`). Agregar una regla nueva no debe obligar a tocar la simulación.
- **Si quedan 0 candidatos:** no se devuelve una pantalla vacía. Se informa la situación y se muestran los cancelados que fallan **una sola regla**, como "casi elegibles", marcando qué habría que flexibilizar. **La decisión de flexibilizar es del funcionario.**

### 3.3 Paso 4: cálculos por candidato
Las fórmulas exactas están en `docs/calculos_simulacion.md`. Este es el resumen:

| Resultado | Cómo se obtiene |
|---|---|
| **N.º de vehículos** | `por_vehiculo = min(cap_teu, floor(cap_kg / peso_kg))` y `vehículos = ceil(n_contenedores / por_vehiculo)`; si `por_vehiculo = 0` el tipo no es opción. Se usa el tipo **más económico** que cumple y se llena un vehículo antes del siguiente (3 contenedores, 2 por vehículo → `[2, 1]`) |
| **Costo para COSCO** | `vehículos × precio_viaje(proveedor, ruta, tipo_vehículo)`; la tarifa es **fija** |
| **Tiempo estimado** | Simulación Monte Carlo (N = 2000, semilla fija) con el historial de desviaciones del proveedor y del mercado → tiempo típico (P50), mal escenario (P90) y **probabilidad de llegar a tiempo** |
| **Desempeño D** | `100·[0.75·Puntualidad + 0.25·(1 − Magnitud de retraso)]`, con suavizado bayesiano y recencia (vida media de 12 meses). **Siempre se calcula del historial** (`servicio`); nunca es dato de entrada. `servicio.calificacion` no se usa |
| **Confianza C** | `100 · Q · F`: Q = (2/3) consistencia de tiempos + (1/3) cumplimiento con este cliente; F = evidencia (cantidad de servicios y peso extra al historial con este cliente) |
| **Profit COSCO** | `Profit = Presupuesto_disponible − Costo_proveedor` (ver 3.4) |

### 3.4 Profit para COSCO SHIPPING
```
Presupuesto_disponible  = dinero disponible en COSCO antes del envío terrestre (dato de la solicitud)
Costo_proveedor         = vehículos × precio_viaje
Profit                  = Presupuesto_disponible − Costo_proveedor
Margen %                = Profit / Presupuesto_disponible
```
- El profit es un número fijo (no se simula): la tarifa es fija y **el costo por retraso se eliminó** (decisión 2026-10-24). El riesgo de llegar tarde se muestra como probabilidad de llegar a tiempo, no como pesos.
- **Decisión (2026-10-23):** COSCO no tiene una tarifa al cliente. El "ingreso" es el **presupuesto disponible** antes del envío; lo que sobra tras pagar al proveedor es el profit. La solicitud lo recibe como campo de entrada (`presupuesto_cop`). Si el costo supera el presupuesto, el profit es negativo y se muestra así. **Por confirmar con negocio.** No inventen valores.

### 3.5 Paso 5: qué ve el funcionario
**Sección "Elegibles" (candidatos):** ordenados por **puntaje** de mayor a menor; los 4 primeros van marcados como **sugeridos (Top 4)**. Una tarjeta por proveedor con:
- **Puesto y puntaje:** `S = 100·(0,40·M + 0,30·P_a + 0,15·D/100 + 0,15·C/100)`, con `M` = profit frente al mejor profit entre los candidatos y `P_a` = probabilidad de llegar a tiempo, y los puntos que aporta cada factor (ver `docs/calculos_simulacion.md` §6.4).
- **Económico:** costo, profit y margen.
- **Tiempo en palabras** (`tiempo_h.resumen`): *"Normalmente llega en 26 h; en un día malo, hasta 40 h. Plazo: 33 h → llega a tiempo en el 72 % de los casos simulados"*, más el **abanico** para el gráfico.
- **Capacidad** (`capacidad.texto`): vehículos que necesita frente a los libres esta semana y servicios que acepta ese día (o "sin dato", que no descarta).
- **Desempeño y confianza:** valor de 0 a 100, etiqueta, **desglose** y una frase que dice de dónde sale (`texto`).
- **Historial real:** servicios en total y con este cliente (conteos, no ponderados).
- **Fortalezas y debilidades** (máx. 2 de cada una): primero las de esta ruta, vehículo o carga; cada una cita su porcentaje, el promedio del proveedor y cuántos servicios la respaldan.
- **Riesgos con su dato:** pocos datos (N servicios), nunca trabajó con el cliente, probabilidad de llegar a tiempo menor al 70 %, confianza baja con su causa.
- **Logística:** tipo de vehículo y **número de vehículos** a pedir.
- **Explicación en lenguaje natural:** los 2–3 factores que más suben y más bajan a esta opción, comparados con los otros candidatos.

Además:
- El funcionario ve el Top 4 sugerido y todos los demás candidatos (nada se oculta), y puede correr **escenarios "¿y si…?"** con otro plazo (`plazo_h`): el orden se recalcula. Estos escenarios cambian supuestos, nunca los datos históricos.

**Sección "Descartados" (cancelados), obligatoria:** lista de proveedores descartados con **todas** sus razones y el dato que causó cada una. Sirve para transparencia y auditoría.

**Botón "Elegir proveedor":** pide la confirmación y una justificación breve, y guarda la decisión junto con un **snapshot** de todo lo que se mostró.

### 3.6 Display en gafas de realidad aumentada
- Las gafas son la **interfaz principal de la demo**: tarjetas comparables flotantes, un mapa de la ruta A→B, el abanico de tiempos simulados y el panel de descartados.
- Las gafas **consumen la misma API** que la web. **Nada de lógica de negocio en el cliente de realidad aumentada.**
- **La web de respaldo debe tener las mismas funciones.** Si las gafas fallan en la demo, la web la salva.
- *(Opcional)* El robot humanoide AgiBot X2 puede narrar las opciones y los riesgos (vía ROS 2 + TTS) consumiendo la misma API. **Nunca decide.**

---

### 3.7 Identificadores
- **`solicitud_id`:** consecutivo generado por el **backend** (secuencia), no por el frontend. Se muestra como `REQ-0042`.
- **`cliente_id`:** identificador propio de cada cliente en el catálogo `clientes`, para registrar bien sus pedidos y calcular el historial con ese cliente.

---

## 4. Modelo de datos (resumen)

La base es **PostgreSQL en Supabase**, esquema `transporte`, construida por el subequipo de BD. El backend la lee con `backend/datos/postgres.py` (`REPOSITORIO=postgres` y `DATABASE_URL` en `.env`, que no se sube).

| Capa | Tablas reales |
|---|---|
| **Catálogos** | `proveedor`, `cliente` (`cliente_id` → `CLI-001`), `ruta` (dirigida, `distancia_km` fija), `tipo_vehiculo` (`cap_teu`, `cap_kg`, `carga_especial`) |
| **Condiciones actuales** | `tarifa` (proveedor + ruta + tipo de vehículo → `precio_cop`, `transito_estimado_h`), `flota` (`disponibles_semana`), `capacidad_actual` (servicios por día; sin fila = dato desconocido) |
| **Historial** | `solicitud` (cliente, ruta, vehículo, carga, `peso_kg`, recogida y fecha límite) y `servicio` (tránsito real, `a_tiempo`) |
| **Operación del sistema** | Al **decidir**, la API inserta la solicitud en `transporte.solicitud` (queda pendiente). El número sale de la secuencia de la base al evaluar (`REQ-0496`…). Al **cerrar el viaje** con su resultado real (`POST /solicitudes/{id}/cierre`), la API inserta la fila de `transporte.servicio` y el modelo la usa de inmediato: así cada viaje nuevo actualiza D y C. Evaluaciones, escenarios, proveedor elegido, justificación y snapshot viven en memoria (la base no tiene columnas para ellos); el informe descargable de cada decisión los deja por escrito |

Lo que la base no guarda se deduce (cobertura = rutas con tarifa) o sale de `backend/datos/mapeo_postgres.yaml` (qué ubicaciones son puertos). La base también trae vistas (`v_desempeno_proveedor`, `v_candidatos`…); el backend **no** las usa: calcula todo desde el historial.

> El detalle de campos que necesita el módulo de cálculo está en `docs/calculos_simulacion.md`, secciones 5.2 y 7.

---

## 5. Contrato de la API (mantener estable: lo consumen web y gafas)

Documentación interactiva en `/docs` (OpenAPI). Respuestas reales guardadas en `backend/api/ejemplos/` para trabajar sin levantar el backend. Errores siempre en español: `{"detalle": "...", "errores": [{"campo": "...", "mensaje": "..."}]}`.

| Método y ruta | Qué hace |
|---|---|
| `GET /salud` | Estado y tipo de repositorio (`postgres` o `simulado`) |
| `GET /catalogos` | Clientes, ubicaciones, rutas, tipos de vehículo y de carga **con los IDs que acepta la API**. Los desplegables deben llenarse de aquí. Solo lista vehículos que llevan contenedores (turbo y sencillo quedan fuera) |
| `POST /solicitudes/evaluar` | Filtra, calcula y simula. Devuelve candidatos, cancelados con todas sus razones y casi elegibles |
| `GET /solicitudes/{id}` | Evaluación original |
| `POST /solicitudes/{id}/escenario` | "¿Y si…?" con otro `plazo_h`; la solicitud original no cambia |
| `POST /decisiones` · `GET /decisiones/{id}` | Elección del funcionario con justificación obligatoria y snapshot de lo que vio. Inserta la solicitud en `transporte.solicitud`. Una sola decisión por solicitud (409 si se repite); 503 si la base no responde (no queda nada registrado) |
| `GET /decisiones/{id}/informe` | **Informe descargable** (HTML autocontenido, imprimible o guardable como PDF): solicitud, decisión y justificación, comparación de opciones con gráfico de tiempos, descartados con todas sus razones y cómo se calculó. `?descargar=false` lo abre en el navegador |
| `POST /solicitudes/{id}/cierre` | Registra el **resultado real del viaje** en `transporte.servicio` y actualiza el modelo. Responde el D del proveedor antes y después |
| `GET /proveedores/{id}` | Ficha: historial, tendencia mensual de D, fortalezas y debilidades |

**Entrada de `POST /solicitudes/evaluar`:**
```json
{
  "cliente_id": "CLI-016",
  "origen_id": "Buenaventura",
  "destino_id": "Bogotá",
  "fecha_servicio": "2026-11-03",
  "plazo_h": 33,
  "n_contenedores": 3,
  "peso_kg": 20000,
  "tipo_carga": null,
  "tipo_vehiculo_id": "tractomula",
  "presupuesto_cop": 30000000
}
```
- **Toda carga va en contenedores de 20'** (1 TEU cada uno). `n_contenedores` ≥ 1 y `peso_kg` (peso de **cada** contenedor) > 0 son obligatorios. No existe carga suelta: turbo y sencillo (`cap_teu = 0`) son **obsoletos** y pedirlos da 422.
- `tipo_carga`: `null` (general), `"refrigerado"`, `"sobredimensionado"` o `"peligrosa"`. Ojo: la base escribe `refrigerada`/`sobredimensionada`; la API usa estos valores.
- `tipo_vehiculo_id` es opcional; **si se envía es obligatorio**: solo se evalúan tarifas y flota de ese tipo.
- `presupuesto_cop` lo introduce el funcionario.
- Responde **422** si el cliente, la ruta o el tipo de vehículo no existen, si un contenedor de ese peso no cabe en el tipo exigido o en ningún vehículo del catálogo, o si faltan campos. Responde **503** si la base no responde.

**Respuesta** (extracto real de `backend/api/ejemplos/evaluacion_respuesta.json`; datos de prueba inventados):
```json
{
  "solicitud_id": "REQ-0496",
  "escenario_id": null,
  "ruta": {"ruta_id": "RUTA-02", "origen": "Buenaventura", "destino": "Bogotá", "distancia_km": 515.0},
  "candidatos": [
    {
      "proveedor_id": "PROV-01",
      "nombre": "Transportes Andinos del Sur",
      "vehiculos": {
        "tipo_vehiculo_id": "tractomula",
        "tipo": "Tractomula",
        "cantidad": 3,
        "contenedores_por_vehiculo": [1, 1, 1]
      },
      "costo_cop": 14370000,
      "profit": {"cop": 15630000, "margen_pct": 52.1},
      "tiempo_h": {
        "p50": 26.2,
        "p90": 40.0,
        "prob_a_tiempo": 0.716,
        "abanico": {"5": 22.8, "50": 26.2, "95": 42.0}
      },
      "desempeno": {
        "valor": 72.7,
        "desglose": {"puntualidad": 0.698, "magnitud_retraso": 0.188}
      },
      "confianza": {
        "valor": 47.7,
        "nivel": "Baja",
        "desglose": {"consistencia": 0.409, "cumplimiento_cliente": 0.74, "evidencia": 0.919}
      },
      "riesgos": [],
      "explicacion": "Ha hecho 5 servicios para este cliente (los otros candidatos, 3 en promedio); Opción más económica ($14.370.000, 7 % menos que la siguiente); Confianza en sus datos de 48/100 (los otros candidatos, 42 en promedio); Llega a tiempo en el 72 % de las simulaciones (los otros candidatos, 82 % en promedio); Desempeño de 73/100 (los otros candidatos, 82 en promedio).",
      "avisos": []
    }
  ],
  "cancelados": [
    {
      "proveedor_id": "PROV-02",
      "nombre": "Pacífico Express Logística",
      "razones": [
        {
          "codigo": "VEHICULO_NO_DISPONIBLE",
          "mensaje": "No tiene Tractomula disponible",
          "requerido": "Tractomula",
          "disponible": "refrigerado"
        }
      ]
    }
  ],
  "casi_elegibles": [],
  "sin_candidatos": false,
  "parametros_escenario": {"plazo_h": 33.0, "semilla": 42, "n_simulaciones": 2000}
}
```
- `vehiculos.tipo_vehiculo_id` (clave del catálogo) y `vehiculos.contenedores_por_vehiculo`: cuántos contenedores lleva cada vehículo (se llena uno antes del siguiente).
- `tiempo_h.abanico`: percentil → horas, para el gráfico de abanico (5, 10, 25, 50, 75, 90, 95).
- `confianza.desglose`: `consistencia`, `cumplimiento_cliente` y `evidencia` (sin incidentes).
- `avisos`: datos faltantes que no descartan pero deben verse (p. ej. sin dato de capacidad para la fecha).
- `casi_elegibles` solo se llena si `sin_candidatos` es `true`; cada uno trae `vehiculos` (lo que habría que pedirle si se flexibiliza, o `null` si no tiene tarifa).
- `solicitud_id` sale de la secuencia de `transporte.solicitud`: no se reinicia, pero puede saltar números (cada evaluación reserva uno aunque no se decida).

**Entrada de `POST /solicitudes/{id}/cierre`:** `{"fecha_entrega_real": "2026-11-04T08:30:00", "proveedor_id": null, "precio_cop": null, "incidente": null, "calificacion": null}`.
- `fecha_entrega_real` es obligatoria (hora local de Colombia; si trae zona horaria se convierte).
- `proveedor_id` y `precio_cop` toman por defecto el proveedor y el costo de la decisión registrada; si el servidor se reinició o la solicitud la cargó el equipo de BD, hay que enviarlos.
- `incidente` (`ninguno`, `retraso`, `dano`, `robo`, `varado`, `documental`) vale `ninguno` por defecto y `calificacion` (1–5) vale **3** (neutro) si no se envía; el modelo no usa ninguno de los dos.
- La API calcula `transito_real_h` (horas desde la recogida) y `a_tiempo` (entrega ≤ `fecha_entrega_limite`). Responde 201 con `desempeno_antes`/`desempeno_despues` y `servicios_antes`/`servicios_despues`; 404 si la solicitud no está en la base, 409 si ya tiene servicio, 422 si la entrega es anterior a la recogida.

**Entrada de `POST /decisiones`:** `{"solicitud_id": "REQ-0496", "proveedor_id": "PROV-01", "justificacion": "…", "escenario_id": null}`. La respuesta trae `decision_id`, `tipo_vehiculo_id` con el que se guardó la solicitud, `flexibilizado` y el `snapshot` completo. En la base se guarda: cliente, ruta, vehículo, tipo de carga, peso total (`n_contenedores × peso_kg`), `fecha_recogida` (00:00 de `fecha_servicio`) y `fecha_entrega_limite` (recogida + `plazo_h`; el del escenario si se decidió sobre uno).

> Si se cambia el contrato, **hay que actualizar este README**, regenerar `backend/api/ejemplos/` y avisar al equipo de frontend y de realidad aumentada.

---

## 6. Estructura del repositorio (propuesta)

```
/
├── README.md                 ← este archivo
├── PLAN.md                   ← plan de implementación + checklist (lo mantiene Claude Code)
├── docs/
│   ├── README.md             ← índice de la documentación
│   ├── calculos_simulacion.md
│   ├── decisiones.md
│   ├── concepto_sala_decisiones.md   (pendiente)
│   └── valor_negocio.md              (pendiente)
├── database/                 ← (aún no creada) subequipo BD: esquema, migraciones, datos semilla
├── backend/                  ← API FastAPI conectada a Supabase
│   ├── filtro/               ← reglas de descarte (Candidatos → Cancelados)
│   ├── calculos/             ← desempeño, confianza, costos, profit, vehículos
│   ├── simulacion/           ← Monte Carlo y escenarios
│   ├── api/                  ← endpoints y ejemplos/ del contrato
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

1. **Nunca decidir por el funcionario.** El sistema ordena y sugiere un Top 4 con una fórmula pública; siempre opciones, consecuencias, explicación y confirmación humana con justificación.
2. **Toda razón de descarte debe ser visible.** Evaluar todas las reglas, no solo la primera que falle.
3. **Ningún número sin explicación.** Cada valor de D, C, tiempo, costo y profit debe poder desglosarse y rastrearse hasta los datos.
4. **No inventar datos.** Si falta un dato, márquenlo y muestren cómo afecta la confianza. Los datos sintéticos de prueba van **etiquetados** como tales, por ahora en `backend/datos_sinteticos/`. Las credenciales van solo en `.env` (nunca en `.env.example`).
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
| Comprensión del problema | 15 | Los 7 factores, las tensiones entre ellos y el contexto colombiano (cobertura y capacidad de los proveedores) |
| Calidad de la recomendación | 20 | El filtro garantiza que todo candidato cumple los requisitos y no da pérdida; un puntaje público ordena y sugiere un Top 4; los "casi elegibles" cubren los casos sin opción ideal |
| Metodología y transparencia | 20 | Fórmulas documentadas, desglose por componente y razones de descarte visibles |
| Funcionamiento y demostración | 20 | Flujo de principio a fin con datos históricos y de prueba en varios casos distintos |
| Análisis y visualización | 10 | Tarjetas comparables, abanico de simulación, ficha por proveedor y tableros |
| Valor de negocio y viabilidad | 10 | Profit por decisión, tiempo ahorrado al funcionario y plan de implementación |
| Comunicación | 5 | Demo en realidad aumentada con la web de respaldo y una historia clara |

**Validación (backtesting):** se reviven solicitudes históricas con las tarifas y la flota de ese día. Se revisa: ¿el proveedor elegido por COSCO estaba entre los candidatos? ¿la simulación predijo bien el tiempo y la puntualidad reales?

---

## 9. Decisiones y preguntas abiertas
El registro completo y fechado está en `docs/decisiones.md`.

**Resueltas**
- [x] **Stack:** Python 3.12.7 + FastAPI + pandas/numpy; web de respaldo en HTML y JS plano con Chart.js.
- [x] **Base de datos:** PostgreSQL.
- [x] **Gafas:** Meta Quest 3, con Three.js y WebXR.
- [x] **Origen del "ingreso" para el profit:** presupuesto disponible de COSCO antes del envío (ver 3.4). Confirmado.
- [x] **Viajes en varias tandas:** se descartan por defecto (configurable).
- [x] **Identificadores:** `solicitud_id` consecutivo del backend y `cliente_id` propio (ver 3.7).

- [x] **Esquema real de la BD y conexión:** Supabase, esquema `transporte`, adaptador `backend/datos/postgres.py` (2026-10-24).
- [x] **Cobertura:** se deduce de las tarifas (rutas en las que el proveedor tiene tarifa).
- [x] **Tipos de vehículo:** tabla `tipo_vehiculo` (turbo, sencillo, tractomula, refrigerado, cama baja). **Tipos de carga:** general, refrigerada, peligrosa, sobredimensionada.
- [x] **Campos de la solicitud:** `n_contenedores` + `peso_kg` por contenedor (sección 5).
- [x] **Incidentes y bloqueos de vía:** fuera del modelo (2026-10-24).
- [x] **Turbo y sencillo:** obsoletos; el grupo decidió transportar solo contenedores (2026-10-24). Su historial sigue contando para el desempeño de cada proveedor.
- [x] **Persistencia:** la solicitud se guarda en `transporte.solicitud` al decidir (2026-10-24).

**Pendientes**
- [ ] `transporte.solicitud` no tiene columnas para el proveedor elegido, la justificación, el snapshot ni `n_contenedores`: viven en memoria (decisión del 2026-10-24: no agregar columnas). El informe descargable deja el registro por escrito; hay que descargarlo antes de reiniciar el servidor.
- [ ] El usuario `postgres` de la conexión tiene todos los permisos. Para el testeo conviene un rol que solo lea las tablas y escriba en `solicitud` y `servicio`.
- [ ] Las pruebas de la demo escriben en la base real: definir cómo identificar o limpiar esos viajes de prueba.
- [ ] Las solicitudes de prueba #487, #491 y #495 de la base piden turbo o sencillo: con la decisión anterior siempre dan 422. Actualizarlas o quitarlas.
- [ ] Capacidades del catálogo de vehículos: confirmar con negocio.
