# Registro de decisiones

Una decisión por fila. Si una decisión cambia, se agrega una fila nueva; no se borra la anterior.

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-23 | Backend en Python 3.10 + FastAPI + pandas/numpy | Simple, rápido de montar y adecuado para cálculo numérico y Monte Carlo |
| 2026-10-23 | Web de respaldo en HTML y JS plano con Chart.js, sin paso de build | Igual que el prototipo VR; nada que compilar en la demo |
| 2026-10-23 | Base de datos: PostgreSQL | La construye el subequipo de BD. El esquema real se lee cuando esté disponible |
| 2026-10-23 | Gafas: Meta Quest 3, con Three.js y WebXR | Es el visor disponible; el prototipo ya usa WebXR |
| 2026-10-23 | `Profit = presupuesto_disponible − costo_proveedor − costo_esperado_retraso` | No hay tarifa de COSCO al cliente. El "ingreso" es el dinero disponible antes del envío; lo que sobra es el profit. **Confirmado** por el equipo el 2026-10-23 |
| 2026-10-23 | `solicitud_id` consecutivo generado por el backend y `cliente_id` propio | Registrar correctamente los pedidos de cada cliente, sin depender del frontend |
| 2026-10-23 | `SIN_CAPACIDAD` y `VEHICULOS_INSUFICIENTES` validan capacidad por TEU y por peso | La capacidad define cuántos vehículos reservar y si el proveedor puede atender la solicitud |
| 2026-10-23 | Viajes en varias tandas: se descartan (configurable) | Valor por defecto del documento de cálculos |
| 2026-10-23 | Esquema de BD, cobertura, tipos de vehículo y de carga: pendientes hasta leer la BD real | Dependen del subequipo de BD |
| 2026-10-23 | Trabajo solo local; cada `git push` requiere permiso explícito | Decisión del equipo hasta tener la primera versión del backend |
| 2026-10-23 | `penal_hora_cop` vale 0 por defecto y el funcionario lo ajusta | Valor por defecto del documento de cálculos; no hay referencia de negocio todavía |
| 2026-10-23 | El backend accede a datos mediante una interfaz de repositorio, con adaptador simulado y adaptador PostgreSQL | Permite avanzar sin la BD del subequipo y conectarla después sin tocar filtro, cálculos ni simulación |
| 2026-10-23 | Datos sintéticos en `backend/datos_sinteticos/`, no en `demo/` | El trabajo de este subequipo es solo backend; `demo/` aún no se crea |
| 2026-10-23 | Carga general solo usa vehículos sin carga especial; carga especial solo vehículos de ese tipo | Regla de compatibilidad de la v1; ajustable cuando se conozcan los tipos reales |
| 2026-10-23 | `SIN_CAPACIDAD` exige `servicios_disponibles ≥ 1` en la fecha; si falta el dato no se descarta, se avisa | No inventar datos; la unidad real de capacidad se confirma con el esquema de BD |
| 2026-10-23 | Si el mercado no tiene historial en la ruta, la simulación usa Δ ~ Normal(0, σ0) y lo avisa | La especificación no cubre el caso. **TODO: confirmar con el equipo** |
| 2026-10-24 | Python 3.12.7 (antes 3.10). `.venv` recreado con `uv`; `render.yaml` ya usaba 3.12.7 | Misma versión en local y en el despliegue |
| 2026-10-24 | Se eliminan del modelo los incidentes y las condiciones o bloqueos de vía (`CondicionVia`, `p_evento`, `d_min`, `d_max`, `prob_incidente`, `S_inc`, `I0`, severidades) | Decisión del equipo. Reemplaza las filas sobre incidentes y vía anteriores |
| 2026-10-24 | Confianza: `Q = (2/3)·S_desv + (1/3)·S_cump`; F y `C = 100·Q·F` no cambian. Pesos en `parametros.yaml` | Proporción original 0.40 / 0.20 sin el término de incidentes. El ejemplo de la sección 4 queda A = 66.3 (Media), B = 54.3 (Baja) |
| 2026-10-24 | Escenarios "¿y si…?" solo con `plazo_h` y `penal_hora_cop` | Consecuencia de quitar las condiciones de vía |
| 2026-10-24 | Solicitud: `n_contenedores` (≥ 1, todos de 20' = 1 TEU) y `peso_kg` por contenedor reemplazan a `n_teu` y `toneladas`. No existe carga sin contenedores | Mismo nombre que la base (`solicitud.peso_kg`) |
| 2026-10-24 | Si la solicitud indica `tipo_vehiculo_id`, es obligatorio: solo se consideran tarifas y flota de ese tipo | Decisión del equipo |
| 2026-10-24 | Vehículos: `por_vehiculo = min(cap_teu, floor(cap_kg/peso_kg))`, `vehiculos = ceil(n/por_vehiculo)`; `por_vehiculo = 0` → no es opción; reparto llenando un vehículo antes del siguiente | Reemplaza la fórmula por TEU y toneladas de la sección 5.3 |
| 2026-10-24 | La API responde 422 si un contenedor de ese peso no cabe en el tipo exigido o en ningún vehículo del catálogo | Evita descartar a todos los proveedores con razones engañosas. Propuesto por el agente; revertible |
| 2026-10-24 | Catálogo de vehículos y clientes desde las tablas `transporte.tipo_vehiculo` y `transporte.cliente` (`CLI-001`). `mapeo_postgres.yaml` solo guarda qué ubicaciones son puertos | Las tablas ya existen en Supabase. Se mantiene compatibilidad con el texto `solicitud.cliente` si faltara la tabla |
| 2026-10-24 | El Desempeño siempre se calcula del historial (`servicio`); nunca es dato de entrada. `servicio.calificacion` no se usa. La tabla `desempeno_proveedor` (registro de lo calculado) aún no existe | Decisión del equipo |
| 2026-10-24 | Nuevo `GET /catalogos` y respuesta 503 si la base no responde | El frontend necesita los IDs reales de la base para armar solicitudes válidas |
| 2026-10-24 | El registro de solicitudes, escenarios y decisiones sigue en memoria | Las tablas de operación no existen en la base. **Pendiente:** decidir quién las crea |
| 2026-10-24 | Solo se transportan contenedores. Turbo y sencillo (`cap_teu = 0`) quedan obsoletos: `GET /catalogos` no los ofrece y pedirlos da 422. Sin carga suelta ni volumen | Decisión del grupo. Su historial sigue contando para el desempeño del proveedor |
| 2026-10-24 | Persistencia "solicitud al decidir": el número se reserva de la secuencia de `transporte.solicitud` al evaluar y la fila se inserta al decidir (peso total = `n_contenedores × peso_kg`; recogida 00:00 de `fecha_servicio`; límite = recogida + `plazo_h`). La API nunca escribe en `servicio` | Reemplaza la fila anterior "registro en memoria". `servicio` exige datos reales de entrega; escribirlo al decidir sería inventar historial |
| 2026-10-24 | Una sola decisión por solicitud (409 si se repite). Si la base no responde al decidir: 503 y no se registra nada | Integridad del registro |
| 2026-10-24 | Proveedor elegido, justificación, snapshot y `n_contenedores` siguen en memoria | `transporte.solicitud` no tiene columnas para ellos. **Pendiente** con el equipo de BD |
| 2026-10-24 | `.gitignore` ignora `.env` y `.env.*` (salvo `.env.example`); `tests/test_sin_credenciales.py` falla si una cadena de conexión con contraseña aparece en el repo | La contraseña nunca debe llegar al repositorio |
| 2026-10-24 | Cierre de viajes: `POST /solicitudes/{id}/cierre` inserta el resultado real en `transporte.servicio` (tránsito y `a_tiempo` calculados de las fechas de la solicitud) y recarga el repositorio. Reemplaza "la API nunca escribe en `servicio`": ahora escribe, pero solo con datos reales de entrega | Cada viaje nuevo debe actualizar D y C sin reiniciar el servidor |
| 2026-10-24 | `servicio.calificacion` vale 3 (neutro) si no se envía; `incidente` vale `ninguno`. Ambos en `parametros.yaml` (`cierre`) | Decisión del equipo; el modelo no usa ninguno de los dos |
| 2026-10-24 | No se agregan columnas para proveedor elegido, justificación y snapshot; en su lugar, `GET /decisiones/{id}/informe` genera un informe HTML descargable e imprimible | Decisión del equipo: registro de decisiones para la empresa sin cambiar el esquema |
| 2026-10-24 | Caché de PostgreSQL con vencimiento (`datos.refresco_cache_s` = 300 s) y recarga tras escribir; si el refresco falla se usan los datos anteriores | La base cambia mientras la API está encendida |
