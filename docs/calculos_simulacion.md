# Módulo de cálculos: Desempeño, Confianza, Costos y Simulación

> **Actualizado el 2026-10-24:** sin incidentes ni condiciones de vía; Q = (2/3)·S_desv + (1/3)·S_cump; carga siempre en contenedores (sección 5.3). Ver `decisiones.md`.
>
> **Para Claude Code / agentes de IA:** este documento es la **especificación** del módulo de cálculo de la Sala de Decisiones (reto COSCO SHIPPING, Sabana Hack 2026). Implementa las fórmulas **exactamente como están aquí**. Si una fórmula no se puede implementar con los datos disponibles, **no la cambies en silencio**: deja un `TODO` y avisa al equipo.
>
> Lee primero `../README.md` (contexto general) y `docs/concepto_sala_decisiones.md` (flujo de la sala). La base de datos la construye otro subequipo; la sección 7 dice **qué campos necesita este módulo**.

---

## 0. Principios del equipo (de aquí salen todos los pesos)

1. **La puntualidad es la mayor causal del Desempeño.** Un retraso puede detener la operación del cliente.
2. **La Confianza se basa en la consistencia de los tiempos** del historial, ajustada por:
   - la **cantidad de servicios** registrados;
   - el **historial con este cliente**: entre más hemos trabajado con el proveedor para ese cliente, más confiamos;
   - la **tasa de cumplimiento**.
3. **Los datos recientes pesan más, pero el historial no se olvida.** Vida media de **12 meses**: los proveedores tienen **oportunidad de redención** sin borrar su pasado.
4. **Los precios son fijos y pactados.** No modelamos cambios de precio. El costo depende solo de la **ruta A→B**, el **tipo de vehículo** y el **número de viajes**.
5. **El sistema no decide.** Calcula y explica. El funcionario elige.
6. **Pocos datos ≠ datos perfectos.** Un proveedor con 3 servicios perfectos no puede superar automáticamente a uno con 300 servicios muy buenos. Por eso todas las tasas usan **suavizado bayesiano** hacia el promedio del mercado.

---

## 1. Notación

Para un proveedor `p`, sea `S` el conjunto de sus **servicios históricos completados**. Para cada servicio `i ∈ S`:

| Símbolo | Significado | Unidad |
|---|---|---|
| `t_i` | Antigüedad del servicio: fecha de cálculo − fecha de entrega | días |
| `T_prom_i` | Tiempo de tránsito prometido o pactado | horas |
| `T_real_i` | Tiempo de tránsito real | horas |
| `a_i` | 1 si llegó dentro del plazo acordado, 0 si no | {0,1} |
| `Δ_i` | Desviación relativa de tiempo = `(T_real_i − T_prom_i) / T_prom_i` | fracción (puede ser negativa) |
| `r_i` | Magnitud del retraso = `min(max(Δ_i, 0), 1)` (solo cuenta si llegó tarde; tope 100 %) | [0,1] |
| `c_i` | 1 si el servicio fue para **el mismo cliente** de la solicitud actual | {0,1} |

### 1.1 Incidentes (fuera del modelo)

**Decisión (2026-10-24):** los incidentes no forman parte del modelo. No entran en la Confianza ni se simulan, aunque la base guarde `servicio.incidente`.

### 1.2 Peso por recencia (vida media de 12 meses)

```
w_i = 0.5 ^ ( t_i / H )        con H = 365 días
```
Un servicio de hoy pesa 1. Uno de hace 12 meses pesa 0.5. Uno de hace 24 meses pesa 0.25.

Sumas ponderadas que se reutilizan en todas las fórmulas:
```
W      = Σ w_i                     (volumen efectivo de evidencia)
W_a    = Σ w_i · a_i
W_r    = Σ w_i · r_i
W_c    = Σ w_i · c_i                (volumen efectivo con ESTE cliente)
W_ca   = Σ w_i · c_i · a_i
```

### 1.3 Valores de referencia del mercado (priors)

Se calculan con **todos los proveedores** en el mismo segmento: misma ruta, o si no hay suficientes datos, mismo corredor o promedio nacional.

| Símbolo | Significado | Valor por defecto si no hay datos |
|---|---|---|
| `P0` | Puntualidad promedio del mercado | 0.85 |
| `R0` | Magnitud de retraso promedio | 0.10 |
| `σ0` | Desviación estándar típica de `Δ` | 0.20 |

---

## 2. DESEMPEÑO `D` (0 a 100): "¿Qué tan bien cumple?"

### 2.1 Puntualidad ajustada `P`
```
P = ( W_a + m · P0 ) / ( W + m )            m = 10
```
`m = 10` equivale a "suponer 10 servicios promedio del mercado" antes de ver datos. Con pocos datos, `P` queda cerca de `P0`; con muchos datos, domina el historial real.

### 2.2 Magnitud de retraso ajustada `Ret`
```
Ret = ( W_r + m · R0 ) / ( W + m )
```

### 2.3 Fórmula
```
D = 100 · [ 0.75 · P  +  0.25 · (1 − Ret) ]
```

**Justificación de los pesos:**
- **0.75 a la puntualidad:** es la prioridad número 1 del equipo. Un retraso puede detener una producción o hacer incumplir al cliente, y es la consecuencia que el reto describe como más grave.
- **0.25 a la magnitud del retraso:** llegar 1 hora tarde no es lo mismo que llegar 2 días tarde. Este término diferencia a dos proveedores con la misma tasa de puntualidad.
- **Precio fuera del desempeño:** los precios son fijos y pactados, así que el desempeño mide solo el servicio.

---

## 3. CONFIANZA `C` (0 a 100): "¿Cuánto puedo creer en este proveedor para este cliente?"

La Confianza tiene dos partes que se multiplican:
- la **calidad del historial** `Q`: qué tan predecible y seguro ha sido el proveedor;
- el **factor de evidencia** `F`: cuánto lo conocemos, sobre todo con este cliente.

### 3.1 Consistencia de tiempos `S_desv`
Desviación estándar **ponderada y suavizada** de `Δ`:
```
Δ̄      = Σ w_i · Δ_i / W
σ²_obs = Σ w_i · (Δ_i − Δ̄)² / W
σ_aj   = sqrt( ( W · σ²_obs + m · σ0² ) / ( W + m ) )

S_desv = 1 − min( σ_aj / σ_max , 1 )          σ_max = 0.5
```
`σ_max = 0.5` significa que una variación típica de ±50 % del tiempo prometido equivale a consistencia 0.

### 3.2 Cumplimiento con este cliente `S_cump` (jerárquico)
La puntualidad **con este cliente** se suaviza hacia la puntualidad general del proveedor `P`, no hacia el mercado:
```
S_cump = ( W_ca + m · P ) / ( W_c + m )
```
Si nunca ha trabajado con el cliente, `S_cump = P`.

### 3.3 Calidad del historial `Q`
```
Q = (2/3) · S_desv  +  (1/3) · S_cump
```
**Justificación (2026-10-24):** al quitar los incidentes se conserva la proporción original entre consistencia (0.40) y cumplimiento con el cliente (0.20): 0.40 / 0.60 = 2/3 y 0.20 / 0.60 = 1/3. La consistencia sigue mandando y la puntualidad, que ya domina el Desempeño, no se cuenta dos veces. Los pesos viven en `backend/config/parametros.yaml`.

### 3.4 Factor de evidencia `F` (cantidad de servicios + historial con el cliente)
```
n_ef = W + α · W_c                 α = 2
E    = n_ef / ( n_ef + k )          k = 10
F    = 0.4 + 0.6 · E
```
- **`α = 2`:** cada servicio con **este cliente** cuenta como 3 servicios. Esto materializa "confío más entre más trabajo con él".
- **`k = 10`:** con 10 servicios efectivos, `E = 0.5`.
- **Piso de 0.4:** un proveedor nuevo no tiene confianza 0, sino una confianza baja pero real. Esto le da **oportunidad de entrar**; la confianza crece a medida que demuestra.

### 3.5 Fórmula
```
C = 100 · Q · F
```

### 3.6 Nivel de confianza (para mostrar en la interfaz)
| `C` | Etiqueta |
|---|---|
| ≥ 75 | Alta |
| 55 – 74 | Media |
| < 55 | Baja |

---

## 4. Ejemplo resuelto (validar la implementación contra estos números)

Supuestos de mercado: `P0 = 0.85`, `R0 = 0.10`, `σ0 = 0.20`, `m = 10`, `k = 10`, `α = 2`. Recalculado el 2026-10-24 con Q sin incidentes.

| Dato | Proveedor A (veterano) | Proveedor B (nuevo, perfecto) |
|---|---|---|
| `W` (servicios efectivos) | 30 | 4 |
| `W_a` (a tiempo) | 27 | 4 |
| `W_r` | 2.4 | 0 |
| `σ_obs` de Δ | 0.15 | 0.05 |
| `W_c` / `W_ca` (con este cliente) | 8 / 7 | 4 / 4 |

| Resultado | A | B |
|---|---|---|
| `P` | 0.887 | 0.893 |
| `Ret` | 0.085 | 0.071 |
| **`D`** | **89.4** | **90.2** |
| `σ_aj` → `S_desv` | 0.164 → 0.672 | 0.171 → 0.658 |
| `S_cump` | 0.882 | 0.923 |
| `Q` = (2/3)·S_desv + (1/3)·S_cump | 0.742 | 0.746 |
| `n_ef` → `E` → `F` | 46 → 0.821 → 0.893 | 12 → 0.545 → 0.727 |
| **`C`** | **66.3 (Media)** | **54.3 (Baja)** |

**Lectura:** B tiene un desempeño apenas mayor porque sus 4 servicios fueron perfectos. Pero el sistema **confía bastante más en A**, porque tiene mucha más evidencia, también con este cliente. Esto es exactamente lo que el equipo quiere que vea el funcionario. **Los tests unitarios deben reproducir estos valores con tolerancia ±0.1.**

---

## 5. COSTOS: modelo de datos y cálculo

### 5.1 Idea
El proveedor entrega una **tarifa fija por viaje** para cada combinación **(ruta A→B, tipo de vehículo)**. La distancia de A a B es fija. Se guarda **exactamente lo que el proveedor cotiza**, sin convertirlo a precio por km, y el costo se calcula contando cuántos viajes hacen falta.

### 5.2 Tablas necesarias (requerimiento para el subequipo de base de datos)

```sql
-- Ubicaciones (puertos, ciudades, bodegas)
ubicaciones (
  ubicacion_id      PK,
  nombre            TEXT,            -- "Puerto de Buenaventura", "Bogotá"
  tipo              TEXT,            -- puerto | ciudad | bodega_cliente
  lat, lon          REAL
)

-- Rutas DIRIGIDAS con distancia fija (A→B y B→A son filas distintas)
rutas (
  ruta_id           PK,
  origen_id         FK → ubicaciones,
  destino_id        FK → ubicaciones,
  distancia_km      REAL NOT NULL,   -- fija
  corredor          TEXT,            -- p. ej. "Buenaventura–Bogotá" (para riesgos de vía)
  UNIQUE (origen_id, destino_id)
)

-- Catálogo de tipos de vehículo y su CAPACIDAD (tabla real: transporte.tipo_vehiculo)
tipo_vehiculo (
  tipo_vehiculo     PK,              -- turbo | sencillo | tractomula | refrigerado | cama_baja
  nombre            TEXT,
  cap_teu           INTEGER,         -- contenedores de 20' que lleva; 0 = no lleva contenedores
  cap_kg            INTEGER,         -- peso máximo
  carga_especial    TEXT             -- refrigerado | sobredimensionado | peligrosa | NULL
)

-- Flota disponible de cada proveedor (condición actual, versionada)
vehiculos_proveedor (
  proveedor_id      FK,
  tipo_vehiculo_id  FK,
  unidades_disponibles INTEGER,
  vigente_desde     TIMESTAMP,
  PRIMARY KEY (proveedor_id, tipo_vehiculo_id, vigente_desde)
)

-- TARIFAS FIJAS: precio por VIAJE según proveedor + ruta + tipo de vehículo
tarifas (
  tarifa_id         PK,
  proveedor_id      FK,
  ruta_id           FK → rutas,
  tipo_vehiculo_id  FK → tipos_vehiculo,
  precio_viaje      NUMERIC NOT NULL,     -- COP por viaje completo A→B
  moneda            TEXT DEFAULT 'COP',
  tiempo_prometido_h REAL,                -- tránsito pactado (insumo de la simulación)
  vigente_desde     DATE,
  vigente_hasta     DATE NULL,
  UNIQUE (proveedor_id, ruta_id, tipo_vehiculo_id, vigente_desde)
)
-- Índice recomendado: (ruta_id, tipo_vehiculo_id) para filtrar rápido por solicitud.

-- Vista: solo la tarifa vigente a una fecha
v_tarifa_vigente = tarifas WHERE fecha BETWEEN vigente_desde AND COALESCE(vigente_hasta, ∞)
```

**Por qué así:**
- **Facilita el cálculo:** el costo se obtiene con un `JOIN` directo `solicitud → ruta → tarifa`, sin fórmulas de distancia.
- **Es fiel a cómo trabaja el proveedor:** se guarda el precio cotizado, tal cual.
- **Rutas dirigidas:** importación (puerto→interior) y exportación (interior→puerto) pueden tener precios distintos.
- **Vigencias:** aunque hoy no modelamos cambios de precio, permite revivir solicitudes pasadas con la tarifa de ese día (*backtesting*) sin rediseñar.
- **Indicadores derivados para los tableros:** `costo_km = precio_viaje / distancia_km` y `costo_ton_km = precio_viaje / (distancia_km · cap_kg / 1000)`. Se calculan al vuelo, **no se guardan**.

### 5.3 Cálculo del costo de una opción (actualizado el 2026-10-24)

Entrada: solicitud con la ruta, `n_contenedores` (todos de 20', 1 TEU cada uno; **no existe carga sin contenedores**), `peso_kg` (peso de **cada** contenedor) y, si aplica, el tipo de vehículo exigido.

Si la solicitud indica `tipo_vehiculo_id`, **solo ese tipo** se considera (tarifas y flota de ese tipo). Si no, se consideran los tipos que corresponden a la carga especial (o de carga general).

Para cada tipo de vehículo `v` válido:
```
por_vehiculo_v = min( cap_teu_v,  floor(cap_kg_v / peso_kg) )
vehiculos_v    = ceil( n_contenedores / por_vehiculo_v )
costo_v        = vehiculos_v · precio_viaje(p, ruta, v)

Si por_vehiculo_v = 0 (un contenedor excede el peso del vehículo, o el vehículo no lleva
contenedores, como turbo y sencillo con cap_teu = 0, que quedan obsoletos), ese tipo no es opción.
Factible solo si:  vehiculos_v ≤ unidades_disponibles(p, v)
```
```
Costo_opción(p) = min_v costo_v          (tipo de vehículo más económico que sirve)
```
- **Reparto:** se llena un vehículo antes de pasar al siguiente. 3 contenedores con 2 por vehículo → `[2, 1]`.
- **Ejemplo:** 3 contenedores de 20 000 kg en tractomula de 34 000 kg → `por_vehiculo = min(2, 1) = 1` → 3 vehículos `[1, 1, 1]`.
- Se guarda **qué vehículo, cuántos y cómo se reparten** los contenedores, para mostrarlo en la explicación.
- Si el proveedor no tiene tarifa para esa ruta y tipo de vehículo, **no es opción**: se descarta con el motivo "sin tarifa para la ruta".
- Si `vehiculos_v > unidades_disponibles`, el proveedor queda descartado (`VEHICULOS_INSUFICIENTES`). Viajes en varias tandas: por defecto **descartar**; configurable.
- **Combinaciones mixtas** (por ejemplo, 1 vehículo grande + 1 pequeño): fuera del alcance de la versión 1. Dejar un `TODO`.

---

## 6. SIMULACIÓN por opción (Monte Carlo)

Se corre **solo para los proveedores que pasaron el filtro de requisitos básicos**. Usar `N = 2000` iteraciones y una **semilla fija por solicitud**, para que el resultado sea reproducible y explicable.

### 6.1 Por cada iteración `j`
1. **Desviación de tiempo `Δ_j`** (*bootstrap* ponderado):
   - con probabilidad `W / (W + m)`: tomar un `Δ_i` del historial del proveedor en esa ruta (si `W_ruta < 5`, usar todo su historial), con probabilidad de selección proporcional a `w_i`;
   - en otro caso: tomar `Δ` del historial del **mercado** en esa ruta (si el mercado no tiene datos en la ruta: `Δ ~ Normal(0, σ0)`, con aviso).

   Así, con pocos datos el proveedor se parece al mercado; con muchos datos, se parece a sí mismo.
2. **Tiempo de tránsito:**
   ```
   T_j = T_prom · (1 + Δ_j)
   ```
3. **¿A tiempo?**
   ```
   a_j = 1 si T_j ≤ plazo_solicitud_h
   ```
4. **Costo:**
   ```
   costo_j = Costo_opción(p)  +  penal_retraso_h · max(0, T_j − plazo_h)
   ```
   `penal_retraso_h` es el costo por hora de retraso para el cliente. Por defecto vale 0 y lo puede ajustar el funcionario en la sala. La tarifa es fija; solo cambia la penalidad.

**Decisión (2026-10-24):** ni las condiciones o bloqueos de vía ni los incidentes se simulan.

### 6.2 Resultados por opción (lo que muestra la Sala)
| Resultado | Cálculo |
|---|---|
| Probabilidad de llegar a tiempo | `mean(a_j)` |
| Tiempo típico y en un mal caso | percentiles 50 y 90 de `T_j` |
| Costo (tarifa fija) | `Costo_opción(p)` + vehículo + n.º de viajes |
| Costo esperado con penalidad | `mean(costo_j)` y percentil 90 |
| Desempeño `D` y Confianza `C` | Secciones 2 y 3, con su desglose |
| Explicación | Texto con los 2–3 factores que más suben y que más bajan a la opción |

### 6.3 Escenarios ("¿y si…?")
El funcionario puede volver a simular cambiando dos supuestos: el plazo (`plazo_h`) o la penalidad por hora de retraso (`penal_hora_cop`). **No se modifican los datos históricos, solo los supuestos del escenario.**

---

## 7. Campos que este módulo necesita de la base de datos

| Tabla | Campos mínimos |
|---|---|
| `servicios_historicos` | `servicio_id, proveedor_id, cliente_id, ruta_id, tipo_vehiculo_id, fecha_entrega, tiempo_prometido_h, tiempo_real_h, plazo_acordado_h (o fecha_limite), a_tiempo` |
| `tarifas`, `rutas`, `tipo_vehiculo`, `vehiculos_proveedor` | Ver sección 5.2 |
| `capacidad_actual` | `proveedor_id, fecha_hora, servicios_disponibles` |

> Si `a_tiempo` no viene en los datos, se calcula: `a_tiempo = (tiempo_real_h ≤ plazo_acordado_h)`. Si falta `tiempo_prometido_h`, se usa el de la tarifa.

---

## 8. Parámetros (deben vivir en un archivo de configuración, no en el código)

| Parámetro | Valor | Por qué |
|---|---|---|
| `H` (vida media) | 365 días | Decisión del equipo: estable, con redención en ~1 año |
| `m` (fuerza del prior) | 10 | Equivale a 10 servicios promedio; evita que pocos datos dominen |
| `k` (evidencia media) | 10 | Con 10 servicios efectivos, la mitad del factor de evidencia |
| `α` (bono por cliente) | 2 | Un servicio con este cliente vale por 3 |
| Pesos de `D` | 0.75 / 0.25 | Puntualidad como mayor causal |
| Pesos de `Q` | 2/3 / 1/3 | Proporción original consistencia / cumplimiento sin incidentes (2026-10-24) |
| Piso de `F` | 0.4 | Oportunidad para proveedores nuevos |
| `σ_max` | 0.5 | ±50 % de variación = consistencia nula |
| `N` simulaciones | 2000 | Error de ~1 punto porcentual en la probabilidad de llegar a tiempo |

---

## 9. Pruebas obligatorias
1. El ejemplo de la sección 4 debe dar los mismos valores (±0.1).
2. Un proveedor sin historial: `D ≈ 100·(0.75·P0 + 0.25·(1−R0))`, `C = 100·Q0·0.4` con `Q0 = (2/3)·(1 − σ0/σ_max) + (1/3)·P0`.
3. Peso de la recencia: un retraso de hace 24 meses pesa 1/4 de uno de hoy.
4. Vehículos: 3 contenedores livianos con 2 por vehículo → 2 vehículos `[2, 1]`; 3 contenedores de 20 000 kg en tractomula de 34 000 kg → 3 vehículos `[1, 1, 1]`; se elige el vehículo más barato que sirva.
5. Un proveedor sin tarifa para la ruta → descartado con su motivo.
6. Misma solicitud y misma semilla → mismos resultados de simulación.
