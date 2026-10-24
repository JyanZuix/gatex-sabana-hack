# Vista inicial a 1,50 m y ajustes confirmados

## Aplicar
Guarda copia de seguridad del main.js y modelo-tablet.js actuales. Copia los tres archivos de js/ de esta entrega dentro del js/ de tu proyecto:
- main.js: sustituye el actual.
- modelo-tablet.js: sustituye el actual.
- altura-vr.mjs: nuevo, necesario para la calibración.
Conserva catalogos.js, desplegables.mjs, inicio.js, index.html y assets/Gatex.glb. Esta entrega no modifica el proyecto original de OneDrive. Recarga completamente la página después de copiar los archivos.

## Altura
En PC la cámara inicia en y=1,50 m.
En VR, al recibir la primera pose válida del visor, se calcula el desplazamiento del espacio de referencia necesario para iniciar en 1,50 m, aunque el operador esté sentado. Se aplica una vez por sesión a través de renderer.xr.setReferenceSpace y getOffsetReferenceSpace. El desplazamiento afecta tanto al visor como a los mandos. No se bloquea la cabeza ni se impone una altura en cada fotograma: agacharse, inclinarse o levantarse después modifica la vista normalmente. Al salir se limpia la calibración y la siguiente sesión vuelve a calcularla. No se modifica el suelo/Guardian configurado en el sistema; es una transformación dentro de la experiencia.

## Base y anclaje
Se aplica +90 grados sobre Z al conjunto del GLB, de forma que giran tanto SoporteTablet como AnclajeTablet. Tarjeta1 también acompaña al conjunto. Se mantiene la escala uniforme de presentación del soporte de la corrección anterior, aproximadamente 0,298. Después del giro se centra horizontalmente el soporte y se apoya su punto más bajo en y=0.

## Pantalla
Su marco de rotación se obtiene del anclaje después del giro, compensando la escala negativa original para que esta no introduzca giros adicionales. Sigue siendo hija de AnclajeTablet, mediante PantallaInteractivaGatex.

Para medir la parte superior se usa la malla de SoporteTablet cuyo centro está más cerca de AnclajeTablet. En el archivo proporcionado es la segunda primitiva (índice 1). El ancho se mide en los ejes sin escala del anclaje; el ancho de pantalla se fija en 120 % de esa medida y el alto mantiene 4:3. Esto produce aproximadamente 0,84928 m de ancho y 0,63696 m de alto. El 20 % se aplica al ANCHO de la superficie superior; la altura deriva de la proporción del formulario y no se estira el contenido. La pantalla puede ser menor que la pantalla provisional anterior, porque la referencia solicitada es la base, no el tamaño anterior.

El borde inferior geométrico queda a 0,75 m del suelo incluso si el anclaje gira el rectángulo en diagonal. Se conserva la distancia del centro de pantalla de 1,35 m delante del usuario. Se separa el soporte hacia el fondo lo necesario para que todos sus vértices queden como mínimo 15 mm detrás del plano de pantalla. No es un motor físico ni una garantía de ausencia de colisiones ante modificaciones posteriores del modelo.

El anclaje original orienta la normal del plano hacia el fondo. Se invierte la cara de la geometría plana para verla desde el usuario, manteniendo la rotación del objeto igual a la del anclaje. Este detalle debe revisarse visualmente con el texto real y las gafas. El GLB original no se altera.

## Comprobaciones realizadas
- Sintaxis JavaScript de los tres archivos.
- Calibración simulada a partir de alturas reales de 0,85; 1,10; 1,50 y 1,80 m.
- Espera de pose válida; calibración una vez por sesión; conservación de 10 cm de movimiento posterior.
- Cálculo independiente a partir de los vértices del GLB real: giro de 90 grados, pie en y=0, borde inferior en y=0,75, pantalla un 20 % más ancha y separación de 15 mm con el soporte.
- No se cambió la lógica de desplegables ni se agregó envío al backend.

No se completó una prueba de WebGL ni en Meta Quest 3. Falta confirmar visualmente orientación, legibilidad y encaje del conjunto, y probar la calibración sentado con ambos mandos. Inicia cada sesión sentado en tu posición habitual, sin inclinarte durante la entrada.

Prueba PC con http://localhost:8000/?preview=1. Para el visor usa la URL HTTPS sin preview=1. No abras index.html con doble clic.

Referencias técnicas de la calibración:
https://developer.mozilla.org/en-US/docs/Web/API/XRReferenceSpace/getOffsetReferenceSpace
https://threejs.org/docs/pages/WebXRManager.html
