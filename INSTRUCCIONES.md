# Escenario actualizado Gatex5

Guarda una copia de seguridad de main.js y escenario.js. Copia a tu proyecto los tres archivos de esta entrega:
- js/main.js: sustituye el actual; únicamente actualiza el nombre del modelo en los mensajes de error.
- js/escenario.js: sustituye el actual; únicamente actualiza la ruta a assets/Gatex5.glb y su mensaje de error.
- assets/Gatex5.glb: nuevo, copia binaria idéntica al modelo de Downloads.

Conserva entrada-vr.mjs, referencia-cono.mjs, catalogos.js, desplegables.mjs, inicio.js e index.html. Gatex4.glb ya no se carga, aunque permanezca como archivo. El cargador conserva su lógica para mantener una sola instancia de escenario y no utiliza el modelo anterior como sustituto ante un error.

El modelo contiene 18 nodos, incluidas las doce tarjetas con nombres únicos Tarjeta1 a Tarjeta12, y Usuario. Se conserva íntegro tal como fue exportado: no se editan sus textos, posiciones, rotaciones, escalas, materiales o jerarquía. No requiere recursos externos ni contiene SoporteTablet o AnclajeTablet.

Se comparó Usuario con Gatex4: mantiene posición, rotación, escala, geometría, normales, UV e índices. La cámara sigue iniciando 1 cm después de la punta, a la altura del modelo y con su dirección completa, en PC y VR. El cono permanece oculto y el ajuste de espacio de referencia sigue ocurriendo una vez por sesión, con cabeza y mandos alineados.

La tablet mantiene su centrado, descenso de 1 metro, aumento del 30 %, inclinación de atril de 45 grados, tamaño proporcional, formulario, desplegables, teclado y controles. Se conserva el fondo azul/gris y la ausencia de niebla. No se añade conexión al backend ni animación de disponibilidad: esta entrega solo sustituye el escenario.

Se verificó la sintaxis de ambos módulos, la presencia de las doce tarjetas únicas, la referencia del cono y la igualdad binaria del GLB entregado con el original. Se confirmó que, aparte del nombre del archivo del modelo, ambos módulos son idénticos a los del proyecto actual.

No se ha hecho renderizado WebGL ni prueba física en Quest 3. Falta comprobar la legibilidad de los nombres en las tarjetas, la apariencia y fluidez del nuevo escenario y la selección de la tablet con los mandos.

Recarga completamente la página después de copiar los archivos. Para PC usa el servidor HTTP con ?preview=1; para Quest usa HTTPS sin ese parámetro. No abras index.html con doble clic.

La carpeta original de OneDrive y el modelo original no se modificaron: los archivos preparados se entregan en esta carpeta de outputs.
