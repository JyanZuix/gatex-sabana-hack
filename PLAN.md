# PLAN.md · Plan de implementación

> Estado: **APROBADO el 2026-10-23.** Fases 0-3 terminadas y ajustadas al modelo del 2026-10-24 (sin incidentes ni vía, carga en contenedores). Fase 4 casi completa y conectada a Supabase.
> Fuentes de verdad: `README.md` (contexto, contrato de la API, reglas) y `docs/calculos_simulacion.md` (fórmulas).
> Convención: `- [ ] tarea — criterio de "listo"`. Cada tarea es de 1 a 3 horas. Una tarea solo se marca `[x]` si sus pruebas pasan y queda una línea en la Bitácora.

## Objetivo
Construir el backend de la Sala de Simulación de Proveedores: recibe una solicitud de transporte terrestre A→B, descarta proveedores con todas sus razones, simula a los candidatos y expone todo por una API estable.
La web de respaldo y las gafas Meta Quest 3 consumen esa API sin lógica de negocio. El funcionario decide y su decisión queda registrada con un snapshot.
Prioridad: flujo de principio a fin → explicaciones y descartados → tableros → gafas → extras.

## Decisiones tomadas
Registro completo en `docs/decisiones.md`. Resumen:

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-23 | Python 3.10 + FastAPI + pandas/numpy | Simple y adecuado para Monte Carlo |
| 2026-10-24 | **Python 3.12.7** (reemplaza 3.10) | Igual que el despliegue en Render |
| 2026-10-24 | Sin incidentes ni condiciones de vía; `Q = (2/3)·S_desv + (1/3)·S_cump` | Decisión del equipo |
| 2026-10-24 | Solicitud con `n_contenedores` y `peso_kg` por contenedor; vehículos = `ceil(n / min(cap_teu, floor(cap_kg/peso_kg)))` | Decisión del equipo |
| 2026-10-24 | Adaptador PostgreSQL contra Supabase (esquema `transporte`, tablas `tipo_vehiculo` y `cliente`) | Base del subequipo disponible |
| 2026-10-23 | Web de respaldo en HTML y JS plano con Chart.js | Sin build; coherente con el prototipo VR |
| 2026-10-23 | PostgreSQL (subequipo BD) | Definido por el equipo |
| 2026-10-23 | Gafas Meta Quest 3, Three.js + WebXR | Visor disponible |
| 2026-10-23 | `Profit = presupuesto − costo_proveedor − costo_esperado_retraso` | Confirmado por el equipo |
| 2026-10-23 | Acceso a datos por interfaz de repositorio con adaptador simulado y adaptador PostgreSQL | Avanzar sin la BD real |
| 2026-10-23 | Tests con `pytest`; configuración en YAML dentro de `backend/config/` | Estándar y legible |
| 2026-10-23 | Dinero en COP como enteros; tiempos en horas (float); aleatoriedad con `numpy.random.default_rng(semilla)` | Reproducibilidad (regla 7) |
| 2026-10-23 | Datos sintéticos en `backend/datos_sinteticos/` y no en `demo/` | El rol de este agente es solo backend y `demo/` aún no debe crearse |
| 2026-10-23 | Pruebas con `backend/pruebas.sh` (quita `PYTHONPATH`) | ROS Humble inyecta plugins de pytest que fallan en el entorno virtual |
| 2026-10-23 | `solicitud_id` consecutivo del backend (`REQ-0042`); `cliente_id` propio | Registro correcto de pedidos |
| 2026-10-23 | `penal_hora_cop` = 0 por defecto; viajes en tandas = descartar | Valores por defecto de la especificación |

TODO abiertos en el código: Δ del mercado sin datos en la ruta (respaldo provisional Normal(0, σ0)), viajes en tandas, combinaciones mixtas de vehículos, persistencia del registro en la base.

Supuestos abiertos: capacidades del catálogo de vehículos a confirmar con negocio; columnas en la base para el proveedor elegido, la justificación y el snapshot. Resuelto: solo contenedores (turbo y sencillo obsoletos).

## Resumen de avance
| Fase | Casillas | Avance |
|---|---|---|
| 0 Base | 9/9 | 100 % |
| 1 Filtro | 12/12 | 100 % |
| 2 Cálculos | 11/11 | 100 % |
| 3 Simulación | 9/9 | 100 % |
| 4 API | 14/14 | 100 % |
| 5 Web de respaldo | 1/9 | 11 % |
| 6 Tableros | 0/6 | 0 % |
| 7 Gafas | 3/8 | 38 % |
| 8 Validación y demo | 0/8 | 0 % |

---

## Fase 0 · Base del proyecto
- [x] Entorno Python — Python 3.12.7 con `uv venv` (antes `python3.10 -m venv`), `requirements.txt` (fastapi, uvicorn, pandas, numpy, pydantic, pyyaml, pytest, psycopg[binary]) y `pytest` corre con 0 tests sin error
- [x] Estructura de paquetes en `backend/` — `import backend.filtro, backend.calculos, backend.simulacion, backend.api` funciona; los `.gitkeep` se reemplazan por `__init__.py` (`backend/api/` se crea en la Fase 4)
- [x] `backend/config/parametros.yaml` — contiene **todos** los parámetros de la sección 8 del doc de cálculos (H=365, m=10, k=10, α=2, pesos de D y Q, piso de F=0.4, σ_max=0.5, severidades, N=2000, semilla, priors P0/R0/σ0/I0, umbrales de nivel de confianza 75/55, tandas=descartar, penal_hora=0)
- [x] Cargador de configuración — `cargar_config()` devuelve un objeto tipado; test: falta un parámetro → error claro que nombra el parámetro; no hay números mágicos en `calculos/` ni `simulacion/` (revisión con grep)
- [x] Modelos de dominio (pydantic) — `Solicitud`, `Proveedor`, `TipoVehiculo`, `Tarifa`, `ServicioHistorico`, `Incidente`, `CondicionVia`; test: se construyen desde un diccionario de ejemplo y rechazan valores negativos
- [x] Interfaz `Repositorio` — métodos para proveedores activos, tarifas vigentes por ruta, flota, cobertura, capacidad, historial, incidentes y condiciones de vía; documentada con docstrings
- [x] Adaptador simulado en memoria — implementa `Repositorio` leyendo JSON desde una carpeta configurable; test: devuelve los datos cargados
- [x] Datos sintéticos etiquetados — 10 proveedores, 4 rutas, 4 tipos de vehículo y 413 servicios con `"sintetico": true` en cada archivo, en `backend/datos_sinteticos/` (no en `demo/`, ver Decisiones) y generados por `generar.py` con semilla fija; test: ningún dato sintético se carga sin la etiqueta
- [x] Adaptador PostgreSQL — `RepositorioPostgres` lee las 9 tablas de `transporte` en Supabase (incluidas `tipo_vehiculo` y `cliente`); el backend arranca con `REPOSITORIO=simulado|postgres` desde el entorno; `tests/test_fase5_postgres.py` y verificación contra la base real

## Fase 1 · Filtro (`backend/filtro/`)
Entrada: solicitud + datos del proveedor. Salida: `Candidato` o `Cancelado` con lista de `Razon(codigo, mensaje, requerido, disponible)`. Se evalúan **todas** las reglas.

- [x] Estructura de reglas — cada regla es una función registrada en una lista; agregar una regla no toca `simulacion/`; test: una regla de prueba agregada en el test aparece en el resultado
- [x] Regla `SIN_COBERTURA` — test: proveedor sin la ruta A→B devuelve la razón con el trayecto en el mensaje
- [x] Regla `SIN_TARIFA` — test: sin tarifa vigente a la fecha de la solicitud para ningún tipo de vehículo válido → razón; con tarifa vencida → razón
- [x] Regla `VEHICULO_NO_DISPONIBLE` — test: carga sobredimensionada y proveedor sin cama baja → razón con el tipo requerido
- [x] Regla `CARGA_NO_SOPORTADA` — test: carga peligrosa y proveedor que no la maneja → razón
- [x] Cálculo de vehículos necesarios para el filtro — usa `ceil(n_contenedores / min(cap_teu, floor(cap_kg/peso_kg)))` (compartido con Fase 2); test: 3 contenedores de 20 000 kg en tractomula de 34 000 kg → 3
- [x] Regla `VEHICULOS_INSUFICIENTES` — test: necesita 2, tiene 1 → razón con `requerido=2`, `disponible=1`; con tandas=descartar el resultado es el mismo
- [x] Regla `SIN_CAPACIDAD` — test: capacidad de servicio en la fecha menor a lo requerido → razón con la fecha
- [x] Regla `PLAZO_INCUMPLIBLE` — test: tiempo prometido 52 h vs plazo 40 h devuelve la razón con `requerido=40` y `disponible=52`
- [x] Regla `PROVEEDOR_INACTIVO` — test: póliza vencida, suspendido o inactivo → razón con la causa
- [x] Orquestador del filtro — test: un proveedor que incumple 3 reglas devuelve las **3** razones; uno que cumple todas queda en candidatos; el orden de entrada no altera el resultado
- [x] Caso "0 candidatos" — devuelve `sin_candidatos=true` y los "casi elegibles" (cancelados con exactamente 1 razón) con qué flexibilizar; test: 0 candidatos con 2 casi elegibles los lista y no decide por el funcionario

## Fase 2 · Cálculos (`backend/calculos/`)
Entradas: historial ponderado por recencia. Todas las fórmulas del doc de cálculos, sin cambios.

- [x] Peso por recencia — `w = 0.5^(t/H)`; test: servicio de hoy → 1, de 12 meses → 0.5, de 24 meses → 0.25
- [x] Sumas ponderadas (`W, W_a, W_r, W_inc, W_c, W_ca`) — test con 3 servicios hechos a mano; `s_i` toma el máximo si hay varios incidentes
- [x] Priors del mercado — por ruta, luego corredor, luego nacional, luego valores por defecto; test: ruta con pocos datos cae al nivel siguiente y lo informa
- [x] Puntualidad `P` y retraso `Ret` suavizados — test: coinciden con A (0.887 / 0.085) y B (0.893 / 0.071) del ejemplo, ±0.001
- [x] Desempeño `D` — test: A = 89.4 y B = 90.2 (±0.1)
- [x] Consistencia `S_desv` — test: A → σ_aj 0.164 y S_desv 0.672; B → 0.171 y 0.658 (±0.001)
- [x] Cumplimiento con cliente `S_cump` — test: A → 0.882; B → 0.923 (±0.001); sin historial con el cliente `S_cump = P`. (Incidentes `S_inc` eliminados el 2026-10-24)
- [x] Calidad `Q = (2/3)·S_desv + (1/3)·S_cump`, factor de evidencia `F` y confianza `C` con nivel — test: A = 66.3 (Media) y B = 54.3 (Baja), ±0.1
- [x] Proveedor sin historial — test: `D ≈ 100·(0.75·P0 + 0.25·(1−R0))` y `C = 100·Q0·0.4`; el resultado marca "sin historial" en lugar de inventar datos (se muestra como riesgo "Poca evidencia histórica")
- [x] Costo y vehículos — elige el tipo de vehículo más barato que cumple y reparte llenando un vehículo antes del siguiente; test: 3 contenedores con 2 por vehículo → `[2, 1]`; contenedor más pesado que el vehículo o vehículo sin `cap_teu` → no es opción; sin tarifa → no es opción
- [x] Profit — `presupuesto − costo − costo_esperado_retraso`, margen sobre el presupuesto; test: presupuesto 12 000 000, costo 9 800 000, retraso 0 → profit 2 200 000 y margen 18.3 %; costo mayor al presupuesto → profit negativo, no se oculta

## Fase 3 · Simulación (`backend/simulacion/`)
- [x] Muestreo de desviación `Δ` — bootstrap ponderado con mezcla `W/(W+m)` proveedor/mercado, y uso de todo el historial si `W_ruta < 5`; test: con `W` grande la media simulada se acerca a la del proveedor, con `W=0` a la del mercado
- [x] ~~Demora por condiciones de vía~~ — eliminada del modelo el 2026-10-24
- [x] Tiempo de tránsito y llegada a tiempo — `T = T_prom·(1+Δ)`; test con datos fijos calculados a mano
- [x] ~~Incidentes simulados~~ — eliminados del modelo el 2026-10-24
- [x] Costo esperado de retraso — `penal_hora · max(0, T−plazo)` promediado; test: penal=0 → 0; plazo muy corto → crece con la penal
- [x] Resultados por opción — P50, P90, `prob_a_tiempo`, profit esperado y profit P10; test: con semilla fija los números coinciden con un caso guardado (*golden*, regenerado el 2026-10-24)
- [x] Reproducibilidad — test: misma solicitud + misma semilla → resultados idénticos; semilla distinta → distintos
- [x] Escenarios "¿y si…?" — recalcula con otro plazo o `penal_hora` sin tocar el historial; test: el historial en memoria no cambia y una penalidad mayor baja el profit
- [x] Explicación en lenguaje natural — los 2-3 factores que más suben y que más bajan la opción, trazables a datos; test: cada frase referencia un valor del desglose

## Fase 4 · API (`backend/api/`)
- [x] Aplicación FastAPI y `GET /salud` — responde 200 con el tipo de repositorio activo
- [x] Esquemas pydantic del contrato — `POST /solicitudes/evaluar` devuelve las claves de la sección 5 del README; test: los ejemplos guardados en `backend/api/ejemplos/` validan contra los esquemas
- [x] Consecutivos — `solicitud_id` `REQ-0001...` generado por el backend y `cliente_id` validado contra el catálogo; test: dos solicitudes seguidas reciben IDs consecutivos distintos y un `cliente_id` inexistente da 422 con mensaje claro
- [x] `POST /solicitudes/evaluar` — integra filtro + cálculos + simulación; test de integración con datos sintéticos y con filas de la base: devuelve candidatos y cancelados con todas las razones
- [x] Caso sin candidatos en la API — `sin_candidatos=true` y casi elegibles; verificado contra Supabase (carga peligrosa Buenaventura → Cali)
- [x] `POST /solicitudes/{id}/escenario` — test: devuelve resultados distintos con otros supuestos y deja la solicitud original intacta
- [x] `POST /decisiones` — guarda elección, justificación (obligatoria) y snapshot de lo mostrado; test: sin justificación → 422; con ella se puede recuperar el snapshot idéntico
- [x] `GET /proveedores/{id}` — historial, tendencia de D, fortalezas y debilidades; test: proveedor inexistente → 404
- [x] CORS, documentación OpenAPI y errores en español — verificado con `uvicorn` y preflight CORS desde otro origen; `GET /catalogos` y 503 si la base no responde
- [x] Persistencia de la solicitud al decidir — número reservado de la secuencia de `transporte.solicitud` al evaluar e INSERT al decidir; 409 si se repite y 503 si la base no responde; test con almacén en memoria y verificación contra Supabase dentro de una transacción con ROLLBACK
- [x] Cierre de viajes — `POST /solicitudes/{id}/cierre` inserta el resultado real en `transporte.servicio`, recarga el repositorio y devuelve D antes y después; `tests/test_fase6_bd.py` (ciclo evaluar → decidir → cerrar → D cambia) y prueba contra Supabase con ROLLBACK
- [x] Caché de PostgreSQL con vencimiento y recarga tras escribir — test: relee al vencer, conserva datos si el refresco falla
- [x] Informe descargable de la decisión — `GET /decisiones/{id}/informe` (HTML imprimible); test: contiene la decisión, todos los descartados con sus razones y escapa el texto
- [x] Informe en 8 secciones y variante JSON — mismo endpoint con «Descargar PDF» (impresión del navegador) y `?formato=json` para las gafas, ambos desde un solo documento; `tests/test_informe_decision.py`: las 8 secciones en orden con datos reales de una solicitud de prueba, mismo contenido en HTML y JSON, snapshot idéntico a lo mostrado
- [ ] ~~Persistencia del proveedor elegido, justificación y snapshot en la base~~ — descartada por el equipo el 2026-10-24; el informe cumple ese papel

## Fase 5 · Web de respaldo (`frontend_web/`)
Depende de la Fase 4. Misma funcionalidad que las gafas.
- [ ] Formulario de solicitud — origen, destino, carga, TEU, peso, vehículo, fecha límite, plazo, cliente, presupuesto y `penal_hora`; valida campos y envía a la API
- [ ] Tarjetas de elegibles — costo, profit esperado y P10, margen, P50/P90, probabilidad a tiempo, D, C con nivel y vehículos; verificación: los valores coinciden con la respuesta de la API
- [ ] Desglose de D y C — cada componente visible y rastreable; verificación manual contra el ejemplo
- [ ] Explicación y riesgos por tarjeta — se muestran los textos de la API sin modificarlos
- [ ] Abanico de tiempos simulados — gráfica de distribución con P50, P90 y el plazo marcado
- [ ] Sección "Descartados" — todas las razones y el dato que las causó, siempre visible, también con 0 candidatos
- [ ] Ordenamiento — por profit, tiempo o confianza sin ocultar ninguna opción ni marcar un "ganador"
- [ ] Escenarios — controles para bloqueo, plazo y `penal_hora` que llaman a `/escenario`
- [x] "Elegir proveedor" — pide confirmación y justificación, llama a `/decisiones` y muestra el registro; ningún texto del tipo "el sistema asignó" (panel compartido con las gafas; en la web se usa `index.html?preview=1`, ver Fase 7)

## Fase 6 · Tableros
- [ ] Precios — costo por viaje, costo/km y costo/ton·km por proveedor y ruta, calculados al vuelo
- [ ] Tiempos de tránsito — prometido vs real por proveedor y ruta
- [ ] Capacidad y disponibilidad de vehículos — unidades por tipo y proveedor
- [ ] Tendencias de desempeño — D en el tiempo por proveedor
- [ ] Ranking de proveedores — ordenable por D y por C, sin imponer un único criterio
- [ ] Endpoints `GET /tableros/...` — test: cada uno devuelve datos con los datos sintéticos

## Fase 7 · Display en gafas (`ar_display/`, Meta Quest 3)
Depende de las fases 4 y 5. Sin lógica de negocio. El prototipo actual (`index.html`, `js/`) se reutiliza.
- [ ] Cliente de la API en el prototipo WebXR — `fetch` a `/solicitudes/evaluar`; no hay cálculos locales (revisión del código)
- [ ] Formulario en la tablet conectado a la API — los campos del prototipo se amplían con los de la solicitud real
- [ ] Tarjetas flotantes comparables — muestran los mismos valores que la web
- [x] Panel de descartados — todas las razones visibles: la tarjeta de un descartado abre una alerta con cada razón y el dato requerido frente al disponible, indica si es casi elegible y solo tiene «Entendido»; `tests/decision.test.mjs`
- [x] Tarjetas interactivas — se seleccionan con mando, pinch o clic, se resaltan al apuntar y al seleccionar; candidato → confirmación con resumen y motivo obligatorio → `POST /decisiones` una sola vez («Registrando…», reintento sin perder el motivo, 409 recupera la decisión ya guardada); descartado en ámbar con insignia «No elegible» y nunca abre la confirmación; `tests/decision.test.mjs` y recorrido en la vista web
- [x] Informe de la decisión en las gafas — panel legible con desplazamiento (botones, joystick o rueda), «Abrir en el navegador» y «Copiar enlace» para la web o la tableta; mismo contenido que el HTML (`?formato=json`)
- [ ] Abanico de tiempos y mapa de la ruta con riesgos — datos de la API
- [ ] Prueba en Quest 3 real por HTTPS — legibilidad y mandos verificados; si falla, se usa la web de respaldo

## Fase 8 · Validación y demo
- [ ] Backtesting — reproduce solicitudes históricas con tarifas y condiciones de ese día; informe: porcentaje de veces que el proveedor elegido por COSCO estaba entre los candidatos
- [ ] Calibración del tiempo — compara P50/P90 simulados con los tiempos reales; informe con el error medio
- [ ] Caso demo 1: típico — varios candidatos y descartados con razones
- [ ] Caso demo 2: urgente — plazo corto que descarta a varios por `PLAZO_INCUMPLIBLE`
- [ ] Caso demo 3: vehículo escaso — `VEHICULOS_INSUFICIENTES` visible
- [ ] Caso demo 4: sin candidatos — casi elegibles sin decidir por el funcionario
- [ ] Caso demo 5: proveedor nuevo con pocos datos — confianza baja pero no cero, con explicación
- [ ] Guion de presentación — 5 minutos, ligado a los criterios de evaluación del README

---

## Dependencias entre fases
```
Fase 0 ─► Fase 1 ─┐
   │              ├─► Fase 3 ─► Fase 4 ─► Fase 5 ─► Fase 7
   └────► Fase 2 ─┘                 │         │
                                    └─► Fase 6 ┘      Fase 8 (necesita 4 y datos reales)
```
- **Paralelo con el subequipo de BD:** las fases 0 a 3 no necesitan la base real. Cuando esté lista se implementa `RepositorioPostgres` y se corre el mismo conjunto de pruebas.
- **Paralelo con frontend y gafas:** desde la Fase 4, con el contrato JSON fijo y un ejemplo en `/docs`, pueden trabajar contra datos sintéticos.
- **Las fases 1 y 2 son paralelas** entre sí; la Fase 3 necesita ambas.
- **La Fase 8 (backtesting)** exige datos históricos reales.

## Riesgos y mitigación
| Riesgo | Mitigación |
|---|---|
| La BD no está lista o su esquema difiere | Interfaz `Repositorio` con adaptador simulado; solo cambia el adaptador |
| Los datos reales no tienen algún campo (por ejemplo `tiempo_real_h`) | Marcar el dato, dejar `TODO` y preguntar; nunca inventar (regla 4) |
| Un parámetro del doc no se puede implementar con datos reales | No cambiarlo; `TODO` y consulta al equipo |
| Las gafas fallan en la demo | La web de respaldo tiene las mismas funciones |
| Quest 3 sin HTTPS o sin red en el lugar de la demo | Publicar con HTTPS con antelación y llevar la web local |
| Pocos datos históricos hacen inestable la simulación | Suavizado bayesiano y caída al mercado, ya especificados; la confianza lo refleja |
| Datos confidenciales de COSCO en un repo público | No subir datos reales; revisar el repo antes de cada push (regla 10) |
| Tiempo insuficiente para todas las fases | Respetar la prioridad: flujo completo → explicaciones y descartados → tableros → gafas |
| Profit negativo confunde al usuario | Se muestra tal cual con una etiqueta "supera el presupuesto" |

## Definición de "Terminado" global
Una solicitud real entra por la web o las gafas, se filtra (con todas las razones de descarte visibles), se simula de forma reproducible, se muestra en la web y en las gafas, y el funcionario registra su decisión con justificación y snapshot. Todas las pruebas pasan. El ejemplo de la sección 4 del doc de cálculos se reproduce con ±0.1.

## Reglas de trabajo
- Fase por fase. No se programa sin aprobación del plan.
- Al terminar una tarea: marcar la casilla, actualizar la tabla de avance y agregar una línea en la Bitácora.
- Cada función de filtro, cálculo o simulación lleva sus pruebas. Si no pasan, no se marca.
- No se decide por el funcionario, no se inventan datos, no se hardcodean parámetros, el contrato de la API no cambia sin actualizar el README.
- **Nada de `git push` sin permiso explícito del equipo.** Se trabaja en local hasta tener la primera versión del backend.

## Bitácora
| Fecha | Qué se hizo | Cómo se verificó |
|---|---|---|
| 2026-10-23 | Estructura de `docs/`, carpeta `backend/` vacía, README actualizado, decisiones registradas y plan redactado | Revisión manual de archivos; sin código todavía |
| 2026-10-23 | Fase 0: entorno `.venv` (Python 3.10.12), `requirements.txt`, `parametros.yaml` con todos los parámetros, cargador tipado, modelos de dominio, interfaz `Repositorio`, adaptador simulado, esqueleto PostgreSQL, fábrica por `REPOSITORIO` y datos sintéticos | `tests/test_fase0_base.py`: 19 pruebas pasan |
| 2026-10-23 | Fase 2: recencia, historial ponderado, priors por segmento, Desempeño, Confianza, vehículos, costo y profit | `tests/test_fase2_calculos.py`: reproduce el ejemplo de la sección 4 (A: D 89.4 / C 73.7; B: D 90.2 / C 60.6) dentro de ±0.1; 27 pruebas pasan |
| 2026-10-23 | Fase 1: 8 reglas registrables, orquestador que evalúa todas, opción de vehículo más barata que cumple el plazo y casi elegibles | `tests/test_fase1_filtro.py`: 21 pruebas pasan, incluido 52 h vs 40 h y el caso PROV-07 del README con datos sintéticos |
| 2026-10-23 | Fase 3: Monte Carlo con semilla por (solicitud, proveedor), escenarios inmutables, explicaciones trazables y riesgos | `tests/test_fase3_simulacion.py`: 25 pruebas pasan, incluido un caso *golden* y el flujo filtro → cálculos → simulación con datos sintéticos |
| 2026-10-23 | Revisión de parámetros hardcodeados en `filtro/`, `calculos/` y `simulacion/` | grep de literales numéricos: solo 0, 1 y la base 0.5 de la fórmula de recencia. Total: 92 pruebas pasan con `backend/pruebas.sh` |
| 2026-10-24 | Suite reparada (pruebas que importaban `CondicionVia`); Python 3.12.7 con `uv` | `backend/pruebas.sh`: 87 pruebas pasan |
| 2026-10-24 | Sin incidentes en dominio, cálculos, simulación, API y datos sintéticos; `Q = (2/3)·S_desv + (1/3)·S_cump` | 87 pruebas pasan; ejemplo de la sección 4 recalculado (A 66.3, B 54.3) |
| 2026-10-24 | Solicitud con `n_contenedores` y `peso_kg`; tipo de vehículo indicado obligatorio; primera suite de la API | 107 pruebas pasan |
| 2026-10-24 | Fórmula nueva de vehículos y reparto de contenedores | 116 pruebas pasan, incluido 3 × 20 000 kg en tractomula → 3 vehículos `[1, 1, 1]` |
| 2026-10-24 | Adaptador PostgreSQL con `tipo_vehiculo` y `cliente`; `GET /catalogos`; 503 si la base cae; ejemplos del contrato | 131 pruebas pasan; `uvicorn` contra Supabase: 15 solicitudes pendientes evaluadas, CORS, escenarios, decisiones y ficha verificados |
| 2026-10-24 | Solo contenedores (turbo y sencillo obsoletos); persistencia de la solicitud al decidir en `transporte.solicitud`; 409/503 en decisiones; vehículo de los casi elegibles; protección de credenciales | 145 pruebas pasan; INSERT verificado contra Supabase con ROLLBACK (la base sigue con 495 filas); `uvicorn` contra Supabase con IDs `REQ-0498` de la secuencia |
| 2026-10-24 | Comunicación completa con la base: cierre de viajes en `servicio`, caché con vencimiento, informe descargable; vehículos obsoletos fuera de `/catalogos/formulario` | 156 pruebas pasan (+1 opcional contra Supabase con ROLLBACK: pasa; la base sigue con 495 solicitudes y 480 servicios) |
| 2026-10-24 | Tarjetas interactivas (candidato → confirmación → `POST /decisiones` → informe; descartado → alerta «No elegible»), panel 3D compartido por gafas y vista web, informe en 8 secciones con `?formato=json`. Se actualizaron las pruebas viejas de `tests/frontend.test.mjs`, que ya fallaban antes (formulario sin `n_contenedores`, `toneladas`, 9 campos) | `backend/pruebas.sh`: 160 pruebas pasan (+4 del informe); `npm test` con Node 22: 8 pruebas pasan, incluidas las 5 pedidas; recorrido completo en `?preview=1` con Chromium sin interfaz y la API simulada con `backend/api/ejemplos/` (sin escribir en Supabase). **Falta probar en Quest 3 real** |
