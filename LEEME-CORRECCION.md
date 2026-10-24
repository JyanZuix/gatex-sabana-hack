# Gatex: desplegables y pantalla anclada

## Aplicar al proyecto original
Esta entrega se preparó a partir de C:\Users\ANDRES\OneDrive\Documentos\GitHub\gatex-sabana-hack. La sesión no tiene escritura en esa carpeta: no se modificaron sus archivos ni el backend.

1. Guarda una copia de seguridad del js/main.js original.
2. Copia js/main.js de esta entrega a la carpeta js/ del proyecto, sustituyendo el anterior.
3. Añade js/catalogos.js, js/desplegables.mjs y js/modelo-tablet.js a js/.
4. Añade assets/Gatex.glb a assets/.
5. Conserva el resto del proyecto, incluyendo backend/, docs/ y tus otros assets.

index.html y js/inicio.js se incluyen sin cambios para que esta carpeta también se pueda ejecutar de forma independiente.

## Problema encontrado y corrección
Los tres campos originales eran entradas de texto: no existían desplegables. Ahora Tipo de carga, Tipo de vehículo y Ciudad de destino abren listas dibujadas en el canvas 3D de la tablet. Solo hay una lista abierta; al elegir se conserva el valor y se cierra. Pulsar fuera o Escape cierra sin cambiar los otros campos. El fondo del menú intercepta el clic para impedir activar algo detrás.

Las listas muestran un máximo de cuatro opciones por página dentro de la pantalla. Si hay más, aparecen Anterior/Siguiente. En PC también se puede usar la rueda, flechas, Tab, PageUp/PageDown, Home/End y Enter. Mantener Enter no repite la selección. Los dos mandos conservan la protección selectstart/selectend; al apuntar se ilumina el rayo y se dibuja un borde en el control. La misma función de coordenadas UV se utiliza con ratón y mandos.

## Catálogos
Se centralizan en js/catalogos.js, sin llamadas al backend.
- Cargas: general, refrigerada, sobredimensionada y peligrosa, según backend/dominio.py.
- Vehículos: los cuatro de backend/datos_sinteticos/tipos_vehiculo.json, conservando sus identificadores.
- Ciudades: Bogotá y Medellín, las dos ubicaciones de tipo ciudad de backend/datos_sinteticos/ubicaciones.json. No se incluyeron puertos bajo Ciudad de destino.
Los vehículos y ciudades son datos sintéticos de ejemplo del proyecto; se identifican así en la interfaz. Falta confirmar los catálogos oficiales y si el destino también debe permitir puertos o bodegas. No se inventaron compatibilidades ni se modificó el filtrado del backend.
La carga general usa cadena vacía en el frontend y una marca selected para distinguirla de un campo aún no elegido. Su conversión a null corresponderá a la futura integración del backend.

## Modelo GLB y anclaje
Gatex.glb contiene Tarjeta1, SoporteTablet y AnclajeTablet. El último es un nodo vacío, sin malla; se utiliza como padre de PantallaInteractivaGatex, que contiene la pantalla existente. Se mantiene Tarjeta1 en su ubicación relativa original.

El anclaje original tiene escala aproximadamente (-1.1311, -0.01078, -1.7330), rotación y traslación propias. Por su eje Y comprimido, se tomó X/Z como superficie y Y como normal. No hay una malla de pantalla que aporte dimensiones exactas: la correspondencia con el área del soporte es una inferencia que necesita revisión visual.

Se aplica un grupo hijo con matriz fija que compensa la escala inicial negativa y no uniforme. La pantalla conserva proporción 4:3 y tamaño 1.15 x 0.8625 metros virtuales; se separa 0.035 unidades del plano local sin escala (unos 15 mm después de escalar el conjunto). El modelo se escala por 0.43, se orienta para que el texto esté derecho y la normal mire al usuario con inclinación suave, y se traslada hasta situar el anclaje en (0, 1.48, -1.35). Estos ajustes de presentación se realizan en memoria, sin alterar el GLB.

Cambios posteriores de posición, rotación o escala del anclaje o del modelo se heredan por la pantalla. Se actualiza su matriz mundial antes de raycasting, tanto con ratón como con cada mando. Al finalizar la carga se oculta la carcasa provisional. Si falla el modelo, se mantiene la tablet provisional y se muestra un aviso; el error detallado aparece en consola.

## Ejecutar y probar
Desde esta carpeta, con Python instalado:

    py -m http.server 8000 --bind 127.0.0.1

En Ubuntu/WSL:

    python3 -m http.server 8000 --bind 0.0.0.0

Abre http://localhost:8000/?preview=1 para probar en PC. Pulsa Abrir prueba en PC. La vista normal para Quest no debe llevar ?preview=1.

Para Quest 3 publica esta carpeta o tu proyecto completo mediante HTTPS válido, por ejemplo GitHub Pages. Abre la URL directamente en Meta Quest Browser y pulsa Entrar a VR. Se requiere internet para Three.js desde unpkg.com. No se generó APK ni se publicó esta entrega.

## Verificación realizada
- node --check en los módulos JavaScript.
- Pruebas de la lógica real de dibujo con canvas simulado: abrir/seleccionar/cerrar, valor vacío de carga general, conservación del peso y origen, exclusión de las zonas detrás del menú, clic fuera de la tablet, Escape, flechas y bloqueo de Enter repetido.
- Paginación con una lista de 17 opciones solo de prueba, comprobando límites de pantalla y correspondencia de zonas con coordenadas UV.
- Verificación de hover y de igualdad binaria entre el GLB copiado y el original.
- Inspección del nodo AnclajeTablet y revisión del cálculo de transformaciones.

Estas pruebas no renderizan WebGL. No se ha verificado visualmente el encaje del soporte ni el funcionamiento físico en un visor. La prueba del servidor local en esta sesión está limitada por restricciones de conexión.

## Pendiente en Quest 3
Comprobar orientación y tamaño de la pantalla sobre el soporte; ajustar los valores de presentación si hace falta. Probar ambos mandos, el borde al apuntar, selección de la última opción, cierre al pulsar fuera, y entrada/salida de VR. Confirmar legibilidad a la altura del usuario y que no haya intersecciones con la geometría del soporte. El GLB original no se ha modificado.
