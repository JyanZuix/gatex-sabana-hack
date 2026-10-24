# Corrección de soporte y altura

Sustituye únicamente js/modelo-tablet.js en tu proyecto por el archivo de esta entrega. Conserva los demás archivos y assets/Gatex.glb. Haz una copia de seguridad del archivo anterior.

La carpeta original de OneDrive no se modificó: esta sesión no tiene permiso de escritura allí.

Cambios:
- Se elimina la rotación aplicada a toda la escena GLB para corregir la pantalla. El soporte conserva ahora su orientación vertical original de Blender.
- La pantalla mantiene la orientación anterior, el ancho de 1.15 m, alto de 0.8625 m y distancia de 1.35 m.
- Como confirmaste, su BORDE INFERIOR queda a 0.75 m del suelo. Por su inclinación, el centro queda aproximadamente a 1.1758 m.
- La pantalla sigue siendo hija de AnclajeTablet. Su transformación local compensa la pose inicial del anclaje para conservar su orientación sin girar la base.
- Se ajusta uniformemente el tamaño del soporte para apoyar el pie en el suelo y conectar su anclaje con la pantalla a la nueva altura; la pantalla no se escala con ese ajuste inicial.
- Se mantiene una separación inicial aproximada de 15 mm entre el anclaje y el plano de pantalla para evitar superficies coincidentes.
- Tarjeta1 se conserva en su ubicación relativa dentro del GLB. No se modifica el archivo binario original.

Verificación:
La sintaxis pasó node --check. Se calcularon los límites del soporte a partir de sus vértices reales del GLB: la escala de presentación resultante es aproximadamente 0.298009; su punto más bajo queda en y=0. Se comprobó que el borde inferior queda a 0.75 m. No se ha realizado prueba visual de WebGL ni en Quest 3: falta confirmar la apariencia del apoyo y la dirección de sus partes con el visor.

Prueba después de copiar el archivo: recarga completamente la página servida por HTTP/HTTPS y entra a VR. Comprueba que la base se ve vertical como en tu dibujo y que el borde inferior está a altura de escritorio. Los desplegables no se modificaron.
