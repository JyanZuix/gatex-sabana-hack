# Gatex-sim VR: API, tablet y tarjetas de proveedores

## Qué queda implementado
La tablet tiene dos páginas con nueve campos: Cliente, Fecha del servicio, Plazo (h), Presupuesto (miles de COP), Peso (kg), Origen, Destino, Tipo de carga y Tipo de vehículo. Fecha límite se omite por tu indicación; no se inventa una hora de recogida ni se envía una fecha de entrega.

Los catálogos proceden de la API, no de archivos de ejemplo. El frontend no accede directamente a PostgreSQL/Supabase y no contiene credenciales de base de datos. El cliente escribe su nombre o lo elige en Ver clientes registrados; debe corresponder a un registro existente.

Evaluar solicitud envía una petición explícita. Listo del teclado solo cierra la edición. Los resultados muestran datos de la API, incluidos profit negativo, explicación, riesgos y avisos, sin un ranking calculado en el navegador ni asignación automática de proveedor.

Después de una evaluación válida, solo los candidatos efectivos quedan en su posición de presentación. Descartados y casi elegibles bajan 3 metros mediante una animación de 850 ms y dejan de ser seleccionables. Se muestran motivos en Descartados y las sugerencias en Casi elegibles, separados. Esos valores visuales se pueden cambiar en ANIMACION_TARJETAS, dentro de config.js.

Nueva consulta cancela peticiones pendientes del navegador, borra el resultado y formulario, y devuelve las tarjetas a las posiciones originales guardadas del GLB. No acumula descensos ni cambia sus rotaciones o escalas. Cancelar una petición en el navegador no revierte una evaluación que el servidor ya hubiera procesado; por eso no se reintentan automáticamente los POST.

## Aplicar al proyecto original
Esta es una copia preparada en outputs. No se modificó la carpeta original de OneDrive.

1. Haz una copia de seguridad de tu proyecto.
2. Copia el contenido de js/ al js/ de tu proyecto. No borres otros archivos de esa carpeta.
3. index.html y assets/Gatex5.glb se incluyen sin cambios; puedes conservar los que ya tienes si son los mismos.
4. Aplica también los TRES archivos de backend/api/ que contiene esta entrega al backend completo original: app.py, esquemas.py y catalogos.py. La carpeta backend de esta entrega es una actualización parcial, no un backend autónomo.
5. Reinicia o recarga el servidor que publica la API. Si corre en otro computador, esos archivos deben aplicarse allí.
6. Recarga completamente el frontend.

El cambio del backend es necesario: API.md y el código revisado no tenían GET /catalogos. Si no se instala, la tablet mostrará que falta ese endpoint y no fabricará listas locales.

Los archivos originales de configuración y las credenciales del backend deben permanecer en el servidor. No copies .env al sitio web. No se modificó el esquema de la base de datos, sus datos, los cálculos de selección ni CORS_ORIGENES.

## Dirección y acceso
La dirección nueva que proporcionaste está configurada SOLO en js/config.js. Cambia API_BASE allí cuando se reinicie el túnel.

Para revisar el frontend desde Windows, en esta carpeta y con Python instalado:

    py -m http.server 8080 --bind 0.0.0.0

En Ubuntu/WSL:

    python3 -m http.server 8080 --bind 0.0.0.0

En PC abre http://localhost:8080/?preview=1 y pulsa Abrir prueba en PC.

Para ejecutar el backend completo con sus dependencias existentes:

    python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000

Conserva su selección actual de repositorio y variables de entorno. No se cambian automáticamente. El frontend y backend usan puertos diferentes para evitar conflictos.

En las Quest usa la dirección HTTPS de tu frontend sin preview=1 y una API_BASE HTTPS accesible desde las gafas. localhost en Quest apunta al propio visor, no al PC. El servidor debe permitir el origen del frontend mediante su CORS_ORIGENES existente. La configuración CORS fue inspeccionada en el código, pero no se pudo comprobar una petición desde un navegador contra el servidor real.

## API utilizada y contrato nuevo
El frontend utiliza:
- GET /catalogos: origenes, destinos, clientes, cargas, vehículos y proveedores.
- GET /catalogos?origen_id=...&fecha_servicio=...: actualiza los destinos para el origen, conservando selecciones que sigan siendo válidas.
- POST /solicitudes/evaluar: evaluación real de la solicitud.

La documentación existente también permite /salud, recuperar solicitudes, escenarios, fichas y decisiones. Se revisaron, pero esta versión no registra decisiones ni contratos y no envía POST /decisiones.

GET /catalogos se añadió a app.py, con respuesta tipada en esquemas.py y lectura en catalogos.py. OpenAPI lo documentará al iniciar la API actualizada. No crea tablas ni escribe registros.

Respuesta:
- repositorio: identifica el adaptador activo; si es simulado, se indica expresamente en la tablet.
- origenes y destinos: listas de {id, nombre}.
- rutas: listas de {ruta_id, origen_id, destino_id}, limitadas a rutas con cobertura registrada de algún proveedor conocido.
- clientes: {id, nombre}, del repositorio.
- tipos_carga: {id, nombre}; id=null significa general.
- tipos_vehiculo: {id, nombre}, del repositorio.
- proveedores: {proveedor_id, nombre, estado}.
- fecha_servicio: fecha enviada, si la hay.
- nota: aclara el alcance del catálogo.

Los destinos reflejan cobertura registrada, no una promesa de capacidad. Flota, póliza, capacidad en la fecha y demás reglas de elegibilidad siguen siendo responsabilidad del endpoint de evaluación. No se inventaron dependencias entre carga y vehículo. Automático (backend) envía tipo_vehiculo_id=null y permite que el servidor elija el vehículo conforme a su lógica existente.

## Asociación entre proveedores y tarjetas
js/proveedores.mjs centraliza exactamente la tabla de nombres que proporcionaste para Tarjeta1 a Tarjeta12. El catálogo del backend aporta el ID real de cada proveedor. Se compara el nombre normalizado —mayúsculas, acentos, espacios y puntuación—, sin coincidencias aproximadas ni suponer que el número del objeto equivale al ID.

Así, Pacifíco del texto proporcionado puede relacionarse con Pacífico del catálogo, pero un nombre distinto o ambiguo produce un aviso y bloquea la evaluación hasta corregir la asociación. No se asigna a otra tarjeta silenciosamente.

La respuesta debe clasificar las doce tarjetas identificadas. Si aparece un ID desconocido, un proveedor figura en grupos incompatibles o faltan tarjetas por clasificar, se informa y se conserva su posición previa. Casi elegibles puede ser un subconjunto de cancelados, como indica API.md.

Al apuntar y pulsar sobre una tarjeta candidata se abre su ficha de evaluación en la tablet. No se crea una elección definitiva. Los nombres ya incluidos en el GLB no se sustituyen ni se añaden rótulos duplicados sobre las tarjetas.

## Validaciones y conversiones
- Cliente: se resuelve el nombre a su ID real de catálogo; un cliente desconocido no se crea automáticamente.
- Origen y destino: IDs de la API y ruta con cobertura.
- Peso positivo en kg → toneladas dividiendo entre 1.000.
- Presupuesto en miles de COP → COP multiplicando por 1.000, con validación de pesos enteros y límites numéricos.
- Plazo positivo en horas, admite decimales.
- Fecha real AAAA-MM-DD, sin convertirla a otra zona horaria.
- Tipo de carga y vehículo: valores del catálogo; general=null.

El formato numérico acepta 24.000 como 24.000 kg y 6.000 como 6.000 miles de COP (=6.000.000 COP). Para decimales puede usarse coma. Las probabilidades solo se formatean a porcentaje; no se recalculan métricas ni rankings.

Los errores 422 se asocian con los campos conocidos. Un fallo de red, respuesta no JSON, tiempo agotado o catálogo vacío se distingue de una evaluación válida sin candidatos. No se borran los datos ante un fallo de evaluación. Las respuestas antiguas de catálogos o evaluaciones se ignoran; cambiar un campo no filtra tarjetas automáticamente.

## Configuración conservada
Se conservaron el modelo Gatex5 sin modificar su archivo, la entrada 1 cm después de la punta de Usuario y su altura e inclinación completas, el cono oculto, calibración una vez por sesión y movimiento natural de cabeza y mandos. También la geometría de tablet, aumento del 30 %, inclinación de atril de 45 grados, descenso de 1 metro, ubicación, fondo azul/gris y ausencia de niebla.

La interfaz canvas ahora ocupa dos páginas para no comprimir nueve campos. Las únicas posiciones del escenario que cambian son las de las tarjetas durante el filtrado solicitado; regresan a las originales al reiniciar.

## Verificación realizada
- Sintaxis de los módulos JavaScript y de los archivos Python modificados.
- Pruebas del constructor de catálogos con un repositorio de prueba y validación de su salida con Pydantic.
- Cliente HTTP probado con respuestas simuladas: 422, respuesta no JSON y validación del resultado.
- Conversiones, cliente registrado, IDs fuera de orden, fechas inválidas y peso cero.
- Flujo completo simulado: formulario → POST → solo tarjetas 1, 5 y 7 arriba; resto abajo; nueva consulta devuelve las doce a sus posiciones originales.
- Casi elegibles abajo, sin selección, con motivo y flexibilización en panel separado.
- Cancelación, doble envío, respuestas antiguas, animaciones sin acumulación y errores sin mover tarjetas.
- Comparación literal de la configuración de cámara/tablet y comparación binaria del GLB original con la copia.

Las pruebas del frontend se pueden ejecutar sin instalar dependencias, con Node.js moderno:

    node --test tests/frontend.test.mjs

Después de aplicar esta entrega al backend completo, puedes ejecutar:

    python tests/catalogos_backend.py

No se probó HTTP de FastAPI en esta sesión porque ese entorno no tiene FastAPI/httpx instalados. Las dependencias ya figuran en backend/requirements.txt del proyecto original.

## Límites pendientes
No se verificó la conexión real con la API ni con Supabase. La nueva dirección devolvió error de resolución DNS desde el acceso disponible. La comprobación externa adicional fue rechazada por la política de permisos de esta sesión; no se desactivó ni eludió esa restricción. No se sustituyeron los datos por ejemplos para aparentar conexión.

Tampoco se realizó renderizado WebGL ni prueba física en Quest 3. Falta comprobar la carga del endpoint instalado, CORS desde el frontend publicado, evaluación real, legibilidad de paneles, selección con ambos mandos y fluidez de las animaciones.

El backend actual guarda solicitudes, escenarios y decisiones en memoria, según API.md. Reiniciar ese servicio pierde esos registros temporales; esta entrega no cambia su persistencia ni confirma automáticamente decisiones.

## Archivos modificados y añadidos
- js/main.js: integra la tablet nueva, selección de tarjetas candidatas y actualización de animaciones.
- js/config.js: dirección única de API y configuración de presentación.
- js/api.mjs: peticiones, errores, tiempo de espera y validación de respuestas.
- js/formulario.mjs: validación, conversiones y control de consultas pendientes.
- js/proveedores.mjs: correspondencia de las doce tarjetas con nombres e IDs reales.
- js/tarjetas.mjs: estados, descenso y restauración de tarjetas.
- js/tablet-ui.mjs: nueve campos, paginación, teclado, catálogos y paneles de resultados.
- backend/api/app.py: nuevo GET /catalogos; resto de endpoints conservados.
- backend/api/catalogos.py: lectura de catálogos desde el repositorio.
- backend/api/esquemas.py: contrato de salida de catálogos para OpenAPI.
- package.json y tests/: ejecución de pruebas sin dependencias JavaScript nuevas.

Se incluyen sin modificaciones index.html, inicio.js, escenario.js, entrada-vr.mjs, referencia-cono.mjs, desplegables.mjs y assets/Gatex5.glb para facilitar la prueba del frontend completo.

---

## Corrección de entrada VR y publicación en Netlify

### Causa corregida
La versión de integración usaba starting y xrSession en el botón Entrar a VR, pero esas variables se habían eliminado al separar la interfaz en módulos. Al pulsar se producía un ReferenceError antes de llamar a navigator.xr.requestSession. Se reprodujo ese fallo con el controlador real del botón.

Se declararon ambas variables y se añadieron mensajes de progreso y errores visibles. También se capturan fallos de inicialización que antes podían dejar la pantalla esperando sin mostrar la causa.

La tablet, el formulario, la cámara, Gatex5, el cono Usuario, la animación de tarjetas y la configuración de API permanecen iguales. Solo cambian js/main.js y js/inicio.js. Esta carpeta incluye todos los archivos del frontend para facilitar una nueva publicación; no incluye el backend Python.

### Publicar
1. Descomprime el ZIP.
2. En tu sitio de Netlify, vuelve a desplegar la carpeta que contiene directamente index.html, js/ y assets/. No subas una carpeta exterior que deje index.html en un nivel interno.
3. Espera a que la publicación termine y recarga la página en Meta Quest Browser. Si la pestaña conserva la versión anterior, ciérrala y abre la dirección publicada de nuevo.
4. Pulsa Entrar a VR y acepta el permiso si aparece. Durante la entrada se muestra Solicitando acceso a VR y Preparando la sesión VR.

Sitio indicado: https://lighthearted-fenglisu-8f3ae6.netlify.app/
Para probar con ratón en PC añade ?preview=1 a esa dirección. Para Quest abre la dirección sin ese parámetro.

Netlify Drop: https://docs.netlify.com/start/quickstarts/netlify-drop-quickstart/

Actualiza también js/main.js y js/inicio.js en tu copia local del proyecto para conservar la corrección. La carpeta original de OneDrive no se modificó automáticamente.

### Verificación y límites
Pasaron las pruebas de sintaxis, la reproducción del fallo anterior y las pruebas simuladas de entrada, salida, reentrada, doble clic, denegación de permiso y modo PC. También pasó la regresión del formulario y de animaciones de tarjetas.

No se pudo inspeccionar la página desplegada: el acceso disponible a su dominio falló por resolución/conexión. No se ha probado en unas Quest físicas ni se ha publicado desde esta sesión. La comprobación pendiente es volver a desplegar y pulsar el botón en el visor.

La disponibilidad del backend se sigue informando dentro de la tablet. Esta corrección no depende de que los catálogos respondan para solicitar la sesión VR; no introduce datos simulados ni modifica los archivos Python entregados antes.
