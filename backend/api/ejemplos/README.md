# Ejemplos del contrato de la API

Respuestas reales de la API, guardadas para que la web de respaldo y las gafas trabajen contra ellas
sin levantar el backend. Se generaron el 2026-10-24 leyendo la base de Supabase (sin escribir en ella: las escrituras se simularon en memoria), cuyos datos son de
**prueba e inventados** (`02_datos.sql`: "No corresponde a proveedores reales").

| Archivo | Endpoint |
|---|---|
| `catalogos_respuesta.json` | `GET /catalogos`: IDs válidos para los desplegables |
| `solicitud_entrada.json` → `evaluacion_respuesta.json` | `POST /solicitudes/evaluar` |
| `escenario_entrada.json` → `escenario_respuesta.json` | `POST /solicitudes/{id}/escenario` |
| `decision_entrada.json` → `decision_respuesta.json` | `POST /decisiones` (el `snapshot` real es la evaluación completa) |
| `ficha_proveedor_respuesta.json` | `GET /proveedores/{id}` |
| `error_422_respuesta.json` | Error de validación (contenedor que no cabe en ningún vehículo) |
| `sin_candidatos_entrada.json` → `sin_candidatos_respuesta.json` | 0 candidatos: `casi_elegibles` con qué flexibilizar y qué vehículo tendrían |
| `decision_repetida_409_respuesta.json` | Segunda decisión sobre la misma solicitud |
| `informe_decision_ejemplo.html` | `GET /decisiones/{id}/informe`: informe descargable de la decisión |
| `cierre_entrada.json` → `cierre_respuesta.json` | `POST /solicitudes/{id}/cierre`: resultado real del viaje (los `null` toman el valor de la decisión o el valor por defecto) |

`backend/tests/test_fase4_api.py` valida que estos archivos sigan cumpliendo el contrato.
Si cambia el contrato, regenérelos y actualice `README.md` (sección 5).
